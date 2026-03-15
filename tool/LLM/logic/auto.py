"""Auto model selection with fallback chain.

Provides an AutoProvider that tries models in stability order, falling back
to the next available model on errors. The stability list is maintained
dynamically based on model.json metadata and runtime error tracking.

Usage:
    from tool.LLM.logic.auto import AutoProvider
    provider = AutoProvider()
    result = provider.send(messages)
"""
import json
import time
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from tool.LLM.logic.base import LLMProvider, CostModel, ModelCapabilities

_MODELS_DIR = Path(__file__).parent / "models"


class ProviderHealth:
    """Tracks per-provider error rates and availability."""

    def __init__(self):
        self._errors: Dict[str, List[float]] = {}
        self._successes: Dict[str, int] = {}
        self._lock = threading.Lock()

    def record_error(self, provider_name: str):
        with self._lock:
            self._errors.setdefault(provider_name, []).append(time.time())
            self._errors[provider_name] = [
                t for t in self._errors[provider_name]
                if time.time() - t < 600  # 10-minute window
            ]

    def record_success(self, provider_name: str):
        with self._lock:
            self._successes[provider_name] = self._successes.get(provider_name, 0) + 1

    def recent_error_count(self, provider_name: str, window_s: int = 300) -> int:
        with self._lock:
            cutoff = time.time() - window_s
            return sum(1 for t in self._errors.get(provider_name, []) if t > cutoff)

    def is_healthy(self, provider_name: str) -> bool:
        return self.recent_error_count(provider_name) < 3


_health = ProviderHealth()


def _load_model_stability() -> List[Dict[str, Any]]:
    """Load model metadata and sort by stability heuristic.

    Stability factors (higher = more stable):
    - free_tier models are preferred (no billing failures)
    - higher RPM = more headroom
    - lower error count in recent window
    - non-reasoning models are more predictable for simple tasks
    """
    from tool.LLM.logic.registry import _REGISTRY, _ensure_builtins
    _ensure_builtins()

    # Build a map of provider_name -> model.json metadata by scanning model dirs
    provider_meta: Dict[str, Dict] = {}
    if _MODELS_DIR.is_dir():
        for d in _MODELS_DIR.iterdir():
            if not d.is_dir():
                continue
            mj = d / "model.json"
            if not mj.exists():
                continue
            try:
                meta = json.loads(mj.read_text())
            except Exception:
                continue
            prov_dir = d / "providers"
            if prov_dir.is_dir():
                for pd in prov_dir.iterdir():
                    if pd.is_dir() and (pd / "interface").is_dir():
                        # Match provider by checking the registry for providers
                        # with this vendor prefix
                        for reg_name in _REGISTRY:
                            vendor = pd.name
                            if vendor in reg_name:
                                provider_meta[reg_name] = meta

    ranked = []
    for name, cls in _REGISTRY.items():
        if name == "auto":
            continue
        try:
            inst = cls()
            available = inst.is_available()
        except Exception:
            available = False
        if not available:
            continue

        meta = provider_meta.get(name, {})
        caps = meta.get("capabilities", {})
        rate = meta.get("rate_limits", {}).get("free", {})
        cost = meta.get("cost", {})

        score = 0
        if cost.get("free_tier", False):
            score += 100
        score += rate.get("rpm", 10)
        if not caps.get("reasoning", False):
            score += 20
        if caps.get("tool_calling", True):
            score += 50
        score -= _health.recent_error_count(name) * 30

        ranked.append({
            "name": name,
            "score": score,
            "capabilities": caps,
            "meta": meta,
        })

    ranked.sort(key=lambda x: -x["score"])
    return ranked


class AutoProvider(LLMProvider):
    """Automatically selects the best available model with fallback.

    On each call, tries providers in stability order. If one fails with
    a retryable error (429, 500, timeout), falls back to the next.
    """

    name = "auto"
    cost_model = CostModel(free_tier=True)
    capabilities = ModelCapabilities(
        supports_tool_calling=True,
        supports_streaming=True,
    )

    def __init__(self, preferred: Optional[str] = None, **kwargs):
        self._preferred = preferred
        self._kwargs = kwargs
        self._last_used: Optional[str] = None

    def _get_fallback_chain(self) -> List[str]:
        """Build ordered list of provider names to try."""
        ranked = _load_model_stability()
        chain = []
        if self._preferred:
            chain.append(self._preferred)
        for r in ranked:
            name = r["name"]
            if name not in chain and _health.is_healthy(name):
                chain.append(name)
        for r in ranked:
            name = r["name"]
            if name not in chain:
                chain.append(name)
        return chain

    def _send_request(self, messages, temperature=1.0, max_tokens=16384,
                      tools=None) -> Dict[str, Any]:
        from tool.LLM.logic.registry import get_provider

        chain = self._get_fallback_chain()
        last_error = None

        for provider_name in chain:
            try:
                provider = get_provider(provider_name)
                result = provider._send_request(
                    messages, temperature, max_tokens, tools=tools)

                if result.get("ok"):
                    _health.record_success(provider_name)
                    self._last_used = provider_name
                    result["_auto_provider"] = provider_name
                    return result

                error_code = result.get("error_code", 0)
                if error_code in (429, 500, 502, 503):
                    _health.record_error(provider_name)
                    last_error = result
                    continue
                else:
                    self._last_used = provider_name
                    result["_auto_provider"] = provider_name
                    return result

            except Exception as e:
                _health.record_error(provider_name)
                last_error = {"ok": False, "error": str(e)}
                continue

        if last_error:
            return last_error
        return {"ok": False, "error": "No available providers"}

    def send_streaming(self, messages, temperature=1.0, max_tokens=16384,
                       tools=None):
        from tool.LLM.logic.registry import get_provider

        chain = self._get_fallback_chain()

        for provider_name in chain:
            try:
                provider = get_provider(provider_name)
                error_seen = False

                for chunk in provider.send_streaming(
                        messages, temperature, max_tokens, tools=tools):
                    if not chunk.get("ok"):
                        _health.record_error(provider_name)
                        error_seen = True
                        break
                    yield chunk

                if not error_seen:
                    _health.record_success(provider_name)
                    self._last_used = provider_name
                    return

            except Exception:
                _health.record_error(provider_name)
                continue

        yield {"ok": False, "error": "All providers failed"}

    def is_available(self) -> bool:
        return bool(self._get_fallback_chain())

    def get_info(self) -> Dict[str, Any]:
        info = super().get_info()
        info["chain"] = self._get_fallback_chain()
        info["last_used"] = self._last_used
        return info
