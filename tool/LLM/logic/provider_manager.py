"""Unified LLM Provider Management Interface.

Single facade that aggregates per-key health (AdaptiveKeySelector),
request rate limiting (RateLimiter), and provider-level health
(ProviderHealth) into one queryable API.

The assistant application layer queries this interface for:
- Unified per-model, per-provider, per-key state
- Expected request processing wait time
- Availability assessment (is the provider currently 429?)

When a 429 or other error occurs, this module updates internal state
immediately. The next call to ``get_status()`` or ``get_full_snapshot()``
returns the refreshed state, allowing Auto mode to naturally avoid
failed models without manually removing them from the candidate list.

Usage::

    from tool.LLM.logic.provider_manager import get_manager
    mgr = get_manager()

    # Query full state snapshot (for Auto decision prompt)
    snapshot = mgr.get_full_snapshot()

    # Check single provider
    status = mgr.get_provider_status("zhipu-glm-4.7-flash")
    if status["available"]:
        wait_s = status["estimated_wait_s"]

    # Report a result (usually called by OpenAICompatProvider)
    mgr.report_result("zhipu-glm-4.7-flash", key_id, result, headers)
"""
import time
import threading
from typing import Any, Dict, List, Optional

from tool.LLM.logic.key_state import (
    AdaptiveKeySelector, KeyStatus, KeyState, get_selector,
)
from tool.LLM.logic.auto import (
    ProviderHealth, get_health, PROVIDER_RECOVERY_RULES,
    PRIMARY_LIST, FALLBACK_LIST,
)


class ProviderStatus:
    """Computed availability status for a single provider."""

    AVAILABLE = "available"
    RATE_LIMITED = "rate_limited"
    DEGRADED = "degraded"
    STALE = "stale"
    DISABLED = "disabled"
    UNCONFIGURED = "unconfigured"


class ProviderManager:
    """Unified provider state manager.

    Aggregates:
    - AdaptiveKeySelector (per-key scores, stale/rate-limited states)
    - ProviderHealth (provider-level error tracking, recovery conditions)
    - RateLimiter state (consecutive 429s, in-flight count)

    Thread-safe. One global instance via get_manager().
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._rate_limiters: Dict[str, Any] = {}
        self._health: ProviderHealth = get_health()

    def _get_vendor(self, provider_name: str) -> str:
        """Extract vendor from provider name (e.g. 'zhipu-glm-4-flash' -> 'zhipu')."""
        return provider_name.split("-")[0] if "-" in provider_name else provider_name

    def _get_rate_limiter(self, provider_name: str):
        """Get the RateLimiter instance for a provider, if one has been registered."""
        return self._rate_limiters.get(provider_name)

    def register_rate_limiter(self, provider_name: str, limiter):
        """Register a provider's RateLimiter for unified monitoring."""
        with self._lock:
            self._rate_limiters[provider_name] = limiter

    def get_provider_status(self, provider_name: str) -> Dict[str, Any]:
        """Return unified status for a single provider.

        Returns a dict with:
        - status: one of ProviderStatus constants
        - available: bool
        - estimated_wait_s: float (expected delay before request can proceed)
        - key_summary: {total, active, rate_limited, stale, degraded}
        - health_errors_5m: int (error count in last 5 minutes)
        - rate_limiter: {consecutive_429s, in_flight} or None
        - recovery_eta_s: float or None (seconds until next recovery window)
        """
        vendor = self._get_vendor(provider_name)
        now = time.time()

        key_summary = self._get_key_summary(vendor)
        health_available = self._health.is_available(provider_name)
        error_count = self._health.recent_error_count(provider_name)

        limiter = self._get_rate_limiter(provider_name)
        limiter_info = None
        if limiter:
            limiter_info = {
                "consecutive_429s": limiter.consecutive_429s,
                "in_flight": limiter.in_flight,
            }

        status = self._compute_status(
            key_summary, health_available, error_count, limiter
        )
        wait_s = self._estimate_wait(provider_name, key_summary, limiter)
        recovery_eta = self._estimate_recovery(provider_name, now)

        is_configured = self._is_configured(provider_name)
        if not is_configured:
            status = ProviderStatus.UNCONFIGURED

        return {
            "provider": provider_name,
            "vendor": vendor,
            "status": status,
            "available": status in (ProviderStatus.AVAILABLE, ProviderStatus.DEGRADED),
            "estimated_wait_s": round(wait_s, 1),
            "key_summary": key_summary,
            "health_errors_5m": error_count,
            "rate_limiter": limiter_info,
            "recovery_eta_s": round(recovery_eta, 1) if recovery_eta else None,
            "timestamp": now,
        }

    def get_full_snapshot(self) -> Dict[str, Dict]:
        """Return status for all known providers.

        Designed to feed Auto's decision prompt with per-model health data.
        """
        from tool.LLM.logic.registry import _REGISTRY, _ensure_builtins
        _ensure_builtins()

        snapshot = {}
        for name in _REGISTRY:
            if name == "auto":
                continue
            snapshot[name] = self.get_provider_status(name)
        return snapshot

    def get_available_from_list(self, model_list: List[str]) -> List[str]:
        """Filter a preference list to providers that are truly available.

        Combines registry check, config check, key health, and provider health.
        """
        from tool.LLM.logic.registry import _REGISTRY, _ensure_builtins
        _ensure_builtins()

        available = []
        for name in model_list:
            if name not in _REGISTRY:
                continue
            status = self.get_provider_status(name)
            if status["available"]:
                available.append(name)
        return available

    def report_result(self, provider_name: str, key_id: Optional[str],
                      result: Dict[str, Any], headers: Dict[str, str] = None):
        """Unified result reporting — updates all tracking systems.

        Called by providers after each request. Propagates to:
        - AdaptiveKeySelector (per-key score update)
        - ProviderHealth (provider-level error/success)
        - RateLimiter (429 backoff counter)
        """
        vendor = self._get_vendor(provider_name)
        ok = result.get("ok", False)
        error_code = result.get("error_code", 0)

        if key_id:
            try:
                selector = get_selector(vendor)
                selector.report(key_id, result, headers=headers)
            except Exception:
                pass

        if ok:
            self._health.record_success(provider_name)
            limiter = self._get_rate_limiter(provider_name)
            if limiter:
                limiter.report_success()
        else:
            self._health.record_error(provider_name, error_code)
            if error_code == 429:
                limiter = self._get_rate_limiter(provider_name)
                if limiter:
                    limiter.report_429()

    def mark_user_selected(self, provider_name: str):
        """Signal that the user manually selected this provider.

        Triggers recovery if the provider was disabled.
        """
        self._health.mark_user_selected(provider_name)

    def get_status_summary_for_prompt(self, model_list: List[str]) -> str:
        """Build a concise state summary for the Auto decision prompt.

        Returns markdown-formatted lines describing each provider's current
        health, so the decision model can factor in real-time availability.
        """
        lines = []
        for name in model_list:
            status = self.get_provider_status(name)
            if status["status"] == ProviderStatus.UNCONFIGURED:
                continue

            state_tag = status["status"].upper()
            wait = status["estimated_wait_s"]
            ks = status["key_summary"]
            errs = status["health_errors_5m"]

            parts = [f"  State: {state_tag}"]
            if wait > 0:
                parts.append(f"Est. wait: {wait}s")
            if ks["rate_limited"] > 0:
                parts.append(f"Keys: {ks['active']}/{ks['total']} active, "
                             f"{ks['rate_limited']} rate-limited")
            if errs > 0:
                parts.append(f"Recent errors: {errs}")
            eta = status["recovery_eta_s"]
            if eta and eta > 0:
                parts.append(f"Recovery in: ~{int(eta)}s")

            lines.append(f"- **{name}**: " + " | ".join(parts))
        return "\n".join(lines) if lines else "All providers healthy."

    # ── Internal helpers ──────────────────────────────────────────────

    def _is_configured(self, provider_name: str) -> bool:
        """Check whether the provider has at least one API key configured."""
        from tool.LLM.logic.registry import _REGISTRY, _ensure_builtins
        _ensure_builtins()
        if provider_name not in _REGISTRY:
            return False
        try:
            inst = _REGISTRY[provider_name]()
            return inst.is_available()
        except Exception:
            return False

    def _get_key_summary(self, vendor: str) -> Dict[str, int]:
        """Aggregate key states for a vendor."""
        try:
            selector = get_selector(vendor)
            states = selector.get_all_states()
        except Exception:
            return {"total": 0, "active": 0, "rate_limited": 0,
                    "stale": 0, "degraded": 0}

        summary = {"total": 0, "active": 0, "rate_limited": 0,
                    "stale": 0, "degraded": 0}
        for _kid, st in states.items():
            summary["total"] += 1
            s = st.get("status", KeyStatus.ACTIVE)
            if s == KeyStatus.ACTIVE:
                summary["active"] += 1
            elif s == KeyStatus.RATE_LIMITED:
                summary["rate_limited"] += 1
            elif s == KeyStatus.STALE:
                summary["stale"] += 1
            elif s == KeyStatus.DEGRADED:
                summary["degraded"] += 1
        return summary

    def _compute_status(self, key_summary: Dict, health_available: bool,
                        error_count: int, limiter) -> str:
        """Derive a single status label from all signals."""
        if key_summary["total"] == 0:
            return ProviderStatus.UNCONFIGURED

        if not health_available:
            return ProviderStatus.DISABLED

        if key_summary["active"] == 0 and key_summary["total"] > 0:
            if key_summary["rate_limited"] > 0:
                return ProviderStatus.RATE_LIMITED
            return ProviderStatus.STALE

        if key_summary["rate_limited"] > 0 and key_summary["active"] > 0:
            return ProviderStatus.DEGRADED

        if limiter and limiter.consecutive_429s > 0:
            return ProviderStatus.RATE_LIMITED

        if error_count >= 3:
            return ProviderStatus.DEGRADED

        return ProviderStatus.AVAILABLE

    def _estimate_wait(self, provider_name: str,
                       key_summary: Dict, limiter) -> float:
        """Estimate seconds until a request could reasonably be sent."""
        wait = 0.0

        if limiter and limiter.consecutive_429s > 0:
            wait += min(2 ** limiter.consecutive_429s, 60)

        if key_summary["active"] == 0 and key_summary["rate_limited"] > 0:
            vendor = self._get_vendor(provider_name)
            try:
                selector = get_selector(vendor)
                now = time.time()
                min_reset = float("inf")
                for _kid, st in selector.get_all_states().items():
                    if st.get("status") == KeyStatus.RATE_LIMITED:
                        reset_t = st.get("rate_limit_reset_t", 0)
                        if reset_t and reset_t > now:
                            min_reset = min(min_reset, reset_t - now)
                if min_reset < float("inf"):
                    wait = max(wait, min_reset)
            except Exception:
                wait = max(wait, 30.0)

        return wait

    def _estimate_recovery(self, provider_name: str, now: float) -> Optional[float]:
        """Estimate seconds until the provider might recover from disabled state."""
        disabled = self._health.get_disabled()
        if provider_name not in disabled:
            return None

        ctx = disabled[provider_name]
        rules = PROVIDER_RECOVERY_RULES.get(
            provider_name,
            PROVIDER_RECOVERY_RULES.get("__default__", []),
        )

        min_eta = None
        for rule in rules:
            if hasattr(rule, "wait_seconds"):
                last_err = ctx.get("last_error_time", 0)
                eta = rule.wait_seconds - (now - last_err)
                if eta > 0:
                    if min_eta is None or eta < min_eta:
                        min_eta = eta
        return min_eta


_manager: Optional[ProviderManager] = None
_manager_lock = threading.Lock()


def get_manager() -> ProviderManager:
    """Get or create the global ProviderManager singleton."""
    global _manager
    if _manager is None:
        with _manager_lock:
            if _manager is None:
                _manager = ProviderManager()
    return _manager
