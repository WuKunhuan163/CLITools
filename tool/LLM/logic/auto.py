"""Auto model selection with LLM-based decision and provider health tracking.

Two preference lists drive the selection:

- **primary_list** (A): All models ranked by quality, free models first.
- **fallback_list** (B): Fast free models used to make the model-selection decision.

Decision flow:
1. User sends prompt → system calls first available model M from B with a
   decision prompt describing all *available* models from A.
2. M returns the chosen model C.
3. If M fails, try next in B. If all B fail, fall back to first available in A.

Provider recovery:
- Each provider can define recovery conditions (timed cooldown, user selection).
- Once a recovery condition fires the provider re-enters the available pool.

The decision interface is callable standalone:

    from tool.LLM.logic.auto import auto_decide
    model_c, response = auto_decide(
        primary_list=PRIMARY_LIST,
        fallback_list=FALLBACK_LIST,
        task_description="...",
        user_prompt="...",
    )
"""
import json
import time
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from tool.LLM.logic.base import LLMProvider, CostModel, ModelCapabilities

_MODELS_DIR = Path(__file__).parent / "models"

# ── Preference Lists ─────────────────────────────────────────────────

PRIMARY_LIST = [
    # FAST free models (non-thinking, instant response)
    "google-gemini-3.1-flash-lite",
    "zhipu-glm-4-flash",
    "baidu-ernie-speed-8k",
    "siliconflow-qwen2.5-7b",
    "baidu-ernie-4.5-turbo-128k",
    "tencent-hunyuan-lite",
    # THINKING free models (15-40s initial delay, for deep reasoning)
    "google-gemini-2.5-flash",
    "google-gemini-3-flash",
    "zhipu-glm-4.7-flash",
    # FAST paid models
    "deepseek-chat",
    "anthropic-claude-haiku-4.5",
    "openai-gpt-4o-mini",
    "baidu-ernie-4.0-turbo-8k",
    # THINKING paid models
    "google-gemini-3.1-pro",
    "google-gemini-2.5-pro",
    "anthropic-claude-sonnet-4.6",
    "openai-gpt-4o",
    "deepseek-reasoner",
    "zhipu-glm-4.7",
    "baidu-ernie-5.0",
    "baidu-ernie-x1.1",
    "baidu-ernie-x1-turbo-32k",
]

FALLBACK_LIST = [
    # Non-thinking free models, sorted by RPM (speed/quota) for fast routing decisions.
    # Thinking models are excluded — they waste reasoning tokens on simple routing.
    "baidu-ernie-speed-8k",          # 10000 RPM, most stable
    "siliconflow-qwen2.5-7b",        # 100 RPM
    "tencent-hunyuan-lite",           # 60 RPM
    "zhipu-glm-4-flash",             # 30 RPM
    "google-gemini-3.1-flash-lite",   # 30 RPM
    "baidu-ernie-4.5-turbo-128k",    # free, non-thinking
]

TITLE_LIST = [
    # Non-thinking free models for generating short session titles.
    # max_tokens kept very low (16) — thinking models are excluded.
    "baidu-ernie-speed-8k",
    "siliconflow-qwen2.5-7b",
    "tencent-hunyuan-lite",
    "zhipu-glm-4-flash",
    "google-gemini-3.1-flash-lite",
    "baidu-ernie-4.5-turbo-128k",
]


# ── Recovery Conditions ──────────────────────────────────────────────

class RecoveryCondition:
    """Base recovery condition — provider re-enters pool when met."""

    def is_met(self, provider_name: str, context: dict) -> bool:
        return False


class TimedRecovery(RecoveryCondition):
    """Re-enable after *wait_seconds* since the last error."""

    def __init__(self, wait_seconds: float):
        self.wait_seconds = wait_seconds

    def is_met(self, provider_name: str, context: dict) -> bool:
        last_error_time = context.get("last_error_time", 0)
        return (time.time() - last_error_time) >= self.wait_seconds


class UserSelectRecovery(RecoveryCondition):
    """Re-enable when the user explicitly selects this provider."""

    def is_met(self, provider_name: str, context: dict) -> bool:
        return context.get("user_selected", False)


def _compute_timed_recovery(provider_name: str) -> float:
    """Compute recovery wait from the provider's rate limit policy.

    Uses RPM from model.json: wait = 60/RPM * 3 (3 RPM windows).
    Falls back to 120s if no data available.

    Reads model.json directly (no registry import) to avoid circular import
    at module-level evaluation time.
    """
    try:
        vendor = provider_name.split("-")[0] if "-" in provider_name else provider_name
        for d in _MODELS_DIR.iterdir():
            if not d.is_dir():
                continue
            mj = d / "model.json"
            if not mj.exists():
                continue
            prov_dir = d / "providers"
            if prov_dir.is_dir():
                for pd in prov_dir.iterdir():
                    if pd.is_dir() and pd.name == vendor:
                        meta = json.loads(mj.read_text())
                        rpm = meta.get("rate_limits", {}).get("free", {}).get("rpm", 0)
                        if rpm > 0:
                            return max(60.0 / rpm * 3, 30.0)
    except Exception:
        pass
    return 120.0


def _build_recovery_rules() -> Dict[str, List[RecoveryCondition]]:
    """Build recovery rules for all known providers."""
    known = [
        "zhipu-glm-4.7-flash", "zhipu-glm-4-flash", "zhipu-glm-4.7",
        "google-gemini-2.5-flash", "google-gemini-2.5-flash-lite",
        "google-gemini-2.5-pro", "google-gemini-3-flash",
        "google-gemini-3.1-flash-lite", "google-gemini-3.1-pro",
        "baidu-ernie-speed-8k", "baidu-ernie-4.5-turbo-128k",
        "baidu-ernie-5.0", "baidu-ernie-4.5-8k",
        "baidu-ernie-x1-turbo-32k", "baidu-ernie-x1.1",
        "baidu-ernie-4.0-turbo-8k", "baidu-ernie-4.5-turbo-32k",
        "tencent-hunyuan-lite", "siliconflow-qwen2.5-7b",
        "nvidia-glm-4-7b",
        "anthropic-claude-sonnet-4.6", "anthropic-claude-haiku-4.5",
        "openai-gpt-4o", "openai-gpt-4o-mini",
        "deepseek-chat", "deepseek-reasoner",
    ]
    rules: Dict[str, List[RecoveryCondition]] = {}
    for name in known:
        wait = _compute_timed_recovery(name)
        rules[name] = [TimedRecovery(wait), UserSelectRecovery()]
    rules["__default__"] = [TimedRecovery(120), UserSelectRecovery()]
    return rules


PROVIDER_RECOVERY_RULES: Dict[str, List[RecoveryCondition]] = _build_recovery_rules()


# ── Provider Health ──────────────────────────────────────────────────

class ProviderHealth:
    """Tracks per-provider errors, cooldowns, and recovery state."""

    def __init__(self):
        self._errors: Dict[str, List[float]] = {}
        self._successes: Dict[str, int] = {}
        self._disabled: Dict[str, Dict] = {}
        self._lock = threading.Lock()

    def record_error(self, provider_name: str, error_code: int = 0):
        with self._lock:
            now = time.time()
            self._errors.setdefault(provider_name, []).append(now)
            self._errors[provider_name] = [
                t for t in self._errors[provider_name]
                if now - t < 600
            ]
            if self._should_disable(provider_name):
                self._disabled[provider_name] = {
                    "last_error_time": now,
                    "error_code": error_code,
                    "user_selected": False,
                }

    def _should_disable(self, provider_name: str) -> bool:
        return len([
            t for t in self._errors.get(provider_name, [])
            if time.time() - t < 300
        ]) >= 3

    def record_success(self, provider_name: str):
        with self._lock:
            self._successes[provider_name] = self._successes.get(provider_name, 0) + 1
            self._disabled.pop(provider_name, None)

    def mark_user_selected(self, provider_name: str):
        with self._lock:
            if provider_name in self._disabled:
                self._disabled[provider_name]["user_selected"] = True
            self._disabled.pop(provider_name, None)
            self._errors.pop(provider_name, None)

    def is_available(self, provider_name: str) -> bool:
        with self._lock:
            if provider_name not in self._disabled:
                return True
            ctx = self._disabled[provider_name]
            rules = PROVIDER_RECOVERY_RULES.get(
                provider_name,
                PROVIDER_RECOVERY_RULES["__default__"],
            )
            for rule in rules:
                if rule.is_met(provider_name, ctx):
                    del self._disabled[provider_name]
                    self._errors.pop(provider_name, None)
                    return True
            return False

    def recent_error_count(self, provider_name: str, window_s: int = 300) -> int:
        with self._lock:
            cutoff = time.time() - window_s
            return sum(1 for t in self._errors.get(provider_name, []) if t > cutoff)

    def get_disabled(self) -> Dict[str, Dict]:
        with self._lock:
            return dict(self._disabled)


_health = ProviderHealth()


def get_health() -> ProviderHealth:
    """Return the global provider health tracker."""
    return _health


# ── Model Metadata Helpers ───────────────────────────────────────────

def _load_model_meta(provider_name: str) -> Dict:
    """Load model.json for a provider using the registry's model mapping."""
    from tool.LLM.logic.registry import _MODEL_PROVIDERS, _ensure_builtins, _MODELS_DIR as reg_models_dir
    _ensure_builtins()

    for model_id, providers in _MODEL_PROVIDERS.items():
        if provider_name in providers:
            dir_name = model_id.replace("-", "_").replace(".", "_")
            mj = reg_models_dir / dir_name / "model.json"
            if mj.exists():
                try:
                    return json.loads(mj.read_text())
                except Exception:
                    return {}
            break
    return {}


def _get_available_models(model_list: List[str]) -> List[str]:
    """Filter list to providers that are registered, configured, and healthy.

    Delegates to ProviderManager for unified availability that factors in
    per-key state, rate-limiter backoff, and provider-level health.
    """
    from tool.LLM.logic.provider_manager import get_manager
    return get_manager().get_available_from_list(model_list)


def get_next_available(exclude: Optional[List[str]] = None) -> Optional[str]:
    """Return the first healthy, available model from PRIMARY_LIST, skipping *exclude*."""
    skip = set(exclude or [])
    for name in _get_available_models(PRIMARY_LIST):
        if name not in skip:
            return name
    return None


def _build_model_descriptions(available: List[str]) -> str:
    """Build a concise model catalog for the decision prompt.

    Includes real-time health state so the decision model can factor in
    which providers are rate-limited or degraded.
    """
    from tool.LLM.logic.provider_manager import get_manager
    mgr = get_manager()

    lines = []
    for name in available:
        meta = _load_model_meta(name)
        display = meta.get("display_name", name)
        caps = meta.get("capabilities", {})
        cost = meta.get("cost", {})
        bench = meta.get("benchmarks", {})
        rate = meta.get("rate_limits", {}).get("free", {})

        parts = [f"- **{name}** ({display})"]
        cap_tags = []
        if caps.get("tool_calling"):
            cap_tags.append("tools")
        if caps.get("vision"):
            cap_tags.append("vision")
        is_reasoning = caps.get("reasoning", False)
        if is_reasoning:
            cap_tags.append("reasoning/thinking (SLOW: 15-40s initial delay)")
        if cap_tags:
            parts.append(f"  Capabilities: {', '.join(cap_tags)}")
        parts.append(f"  Speed: {'SLOW (thinking model)' if is_reasoning else 'FAST'}")
        if cost.get("free_tier"):
            parts.append("  Cost: FREE")
        else:
            inp = cost.get("input_per_1m", cost.get("input_per_1k", "?"))
            out = cost.get("output_per_1m", cost.get("output_per_1k", "?"))
            cur = cost.get("currency", "USD")
            parts.append(f"  Cost: {inp}/{out} per 1M tokens ({cur})")
        ctx_k = caps.get("max_context_tokens", 0)
        if ctx_k:
            parts.append(f"  Context: {ctx_k // 1000}K tokens")
        if bench.get("arena_elo"):
            parts.append(f"  ELO: {bench['arena_elo']} (rank #{bench.get('arena_rank', '?')})")
        if rate.get("rpm"):
            parts.append(f"  Rate: {rate['rpm']} RPM")

        status = mgr.get_provider_status(name)
        health_tag = status["status"].upper()
        if health_tag != "AVAILABLE":
            parts.append(f"  ⚠ Health: {health_tag}")
            if status["estimated_wait_s"] > 0:
                parts.append(f"  Est. wait: {status['estimated_wait_s']}s")

        lines.append("\n".join(parts))
    return "\n\n".join(lines)


# ── Decision Interface ───────────────────────────────────────────────

_DECISION_PROMPT = """\
You are a model router. Pick the BEST model for the user's task. \
Reply with ONLY the model identifier, nothing else.

Rules (in priority order):
1. AVOID models with Health RATE_LIMITED or DEGRADED.
2. If the task involves images, pick a vision-capable model.
3. Prefer free models unless the task clearly needs paid capabilities.
4. STRONGLY prefer FAST (non-thinking) models. Thinking/reasoning models have 15-40s initial delay — only use them for tasks that EXPLICITLY require deep multi-step reasoning (e.g. math proofs, complex algorithms).
5. For simple questions, translations, summaries, basic code, or chat — ALWAYS pick a FAST model.
6. Among fast models, prefer higher quality (higher ELO, larger context).
7. The models are listed in quality order — earlier models are generally better.

Available models:
{model_catalog}

{health_summary}

User task:
{user_prompt}

Reply with ONLY the model identifier."""

_TITLE_PROMPT = """\
Generate a short title (max 6 words) for this task. Reply with ONLY the title, \
no quotes, no explanation.

Task: {user_prompt}"""


def auto_decide(
    primary_list: Optional[List[str]] = None,
    fallback_list: Optional[List[str]] = None,
    task_description: str = "",
    user_prompt: str = "",
) -> Tuple[Optional[str], str]:
    """Use an LLM to decide which model to use for a task.

    Args:
        primary_list: Model names to choose from (defaults to PRIMARY_LIST).
        fallback_list: Models used to *make* the decision (defaults to FALLBACK_LIST).
        task_description: Optional extra context.
        user_prompt: The user's actual prompt/question.

    Returns:
        (chosen_model, decision_response) — the provider name to use and the
        raw LLM response.  If all decision models fail, returns the first
        available model from primary_list with an empty response.
    """
    from tool.LLM.logic.registry import get_provider

    a_list = primary_list or PRIMARY_LIST
    b_list = fallback_list or FALLBACK_LIST

    available_a = _get_available_models(a_list)
    available_b = _get_available_models(b_list)

    if not available_a:
        return None, ""

    catalog = _build_model_descriptions(available_a)
    full_prompt = task_description + "\n" + user_prompt if task_description else user_prompt

    from tool.LLM.logic.provider_manager import get_manager
    health_summary = get_manager().get_status_summary_for_prompt(available_a)

    decision_prompt = _DECISION_PROMPT.format(
        model_catalog=catalog,
        health_summary=("Current health:\n" + health_summary) if health_summary else "",
        user_prompt=full_prompt[:2000],
    )

    _DECISION_TIMEOUT = 10

    for decider_name in available_b:
        try:
            provider = get_provider(decider_name)
            result = {"ok": False, "error": "timeout"}
            call_done = threading.Event()
            call_result = [None]

            def _call():
                try:
                    call_result[0] = provider._send_request(
                        [{"role": "user", "content": decision_prompt}],
                        temperature=0.1,
                        max_tokens=512,
                    )
                except Exception as e:
                    call_result[0] = {"ok": False, "error": str(e)}
                finally:
                    call_done.set()

            t = threading.Thread(target=_call, daemon=True)
            t.start()
            if call_done.wait(timeout=_DECISION_TIMEOUT):
                result = call_result[0] or result
            else:
                _health.record_error(decider_name, 408)
                continue

            if result.get("ok"):
                chosen = result.get("text", "").strip()
                chosen = chosen.strip('"').strip("'").strip("`").strip()
                if chosen in available_a:
                    _health.record_success(decider_name)
                    return chosen, chosen
                for name in available_a:
                    if name in chosen or chosen in name:
                        _health.record_success(decider_name)
                        return name, chosen
                _health.record_success(decider_name)
                return available_a[0], chosen
            else:
                error_code = result.get("error_code", 0)
                _health.record_error(decider_name, error_code)
        except Exception:
            _health.record_error(decider_name)
            continue

    return available_a[0], ""


def auto_generate_title(user_prompt: str) -> str:
    """Generate a short session title using a fast non-thinking model.

    Uses TITLE_LIST (non-thinking models only, sorted by RPM) and
    max_tokens=16 to get the fastest possible title generation.
    """
    from tool.LLM.logic.registry import get_provider

    fast_list = _get_available_models(TITLE_LIST)
    if not fast_list:
        fast_list = _get_available_models(FALLBACK_LIST)
    prompt = _TITLE_PROMPT.format(user_prompt=user_prompt[:500])

    _TITLE_TIMEOUT = 6

    for model_name in fast_list:
        try:
            provider = get_provider(model_name)
            result = {"ok": False, "error": "timeout"}
            call_done = threading.Event()
            call_result = [None]

            def _call():
                try:
                    call_result[0] = provider._send_request(
                        [{"role": "user", "content": prompt}],
                        temperature=0.3,
                        max_tokens=16,
                    )
                except Exception as e:
                    call_result[0] = {"ok": False, "error": str(e)}
                finally:
                    call_done.set()

            t = threading.Thread(target=_call, daemon=True)
            t.start()
            if call_done.wait(timeout=_TITLE_TIMEOUT):
                result = call_result[0] or result
            else:
                _health.record_error(model_name, 408)
                continue

            if result.get("ok"):
                title = result.get("text", "").strip().strip('"').strip("'")
                if title and len(title) < 80:
                    _health.record_success(model_name)
                    return title
            _health.record_error(model_name, result.get("error_code", 0))
        except Exception:
            _health.record_error(model_name)
            continue

    words = user_prompt.split()
    return " ".join(words[:6]) + ("..." if len(words) > 6 else "")


# ── AutoProvider (used by the conversation system) ───────────────────

class AutoProvider(LLMProvider):
    """Wraps the auto-decision system as an LLMProvider.

    On the first streaming call, uses auto_decide() to pick a model,
    then delegates all actual work to the chosen provider.
    """

    name = "auto"
    cost_model = CostModel(free_tier=True)
    capabilities = ModelCapabilities(
        supports_tool_calling=True,
        supports_streaming=True,
    )

    def __init__(self, **kwargs):
        self._chosen: Optional[str] = None
        self._kwargs = kwargs

    def _send_request(self, messages, temperature=1.0, max_tokens=16384,
                      tools=None) -> Dict[str, Any]:
        from tool.LLM.logic.registry import get_provider

        if not self._chosen:
            user_text = ""
            for m in reversed(messages):
                if m.get("role") == "user":
                    user_text = m.get("content", "")
                    break
            chosen, _ = auto_decide(user_prompt=user_text)
            if not chosen:
                return {"ok": False, "error": "No available providers"}
            self._chosen = chosen

        provider = get_provider(self._chosen)
        result = provider._send_request(messages, temperature, max_tokens,
                                        tools=tools)
        if result.get("ok"):
            _health.record_success(self._chosen)
            result["_auto_provider"] = self._chosen
        else:
            error_code = result.get("error_code", 0)
            if error_code in (429, 500, 502, 503):
                _health.record_error(self._chosen, error_code)
        return result

    def send_streaming(self, messages, temperature=1.0, max_tokens=16384,
                       tools=None):
        from tool.LLM.logic.registry import get_provider

        if not self._chosen:
            user_text = ""
            for m in reversed(messages):
                if m.get("role") == "user":
                    user_text = m.get("content", "")
                    break
            chosen, _ = auto_decide(user_prompt=user_text)
            if not chosen:
                yield {"ok": False, "error": "No available providers"}
                return
            self._chosen = chosen

        provider = get_provider(self._chosen)
        error_seen = False
        for chunk in provider.send_streaming(messages, temperature, max_tokens,
                                             tools=tools):
            if not chunk.get("ok"):
                _health.record_error(self._chosen, chunk.get("error_code", 0))
                error_seen = True
            yield chunk

        if not error_seen:
            _health.record_success(self._chosen)

    def is_available(self) -> bool:
        return bool(_get_available_models(PRIMARY_LIST))

    def get_info(self) -> Dict[str, Any]:
        info = super().get_info()
        info["primary_list"] = PRIMARY_LIST
        info["fallback_list"] = FALLBACK_LIST
        info["chosen"] = self._chosen
        info["disabled"] = _health.get_disabled()
        return info
