"""Per-key state tracking with adaptive selection.

Each API key has its own health state, success/failure history,
and selection weight. The AdaptiveKeySelector chooses keys
probabilistically based on their track record.

State persistence: key states are stored per-provider in
providers/<vendor>/data/keys.json under key_states.<key_id>.

Key lifecycle:
    active   — normal operation
    degraded — intermittent failures but still usable
    stale    — auth failure (401/403) or account-level problem;
               excluded from selection until re-verified
    rate_limited — temporarily throttled; auto-recovers after cooldown

Usage:
    selector = AdaptiveKeySelector("zhipu")
    key_id, api_key = selector.select()
    result = provider._send_request(...)
    selector.report(key_id, result, headers=resp_headers)
"""
import json
import math
import random
import time
import threading
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class KeyStatus:
    ACTIVE = "active"
    DEGRADED = "degraded"
    RATE_LIMITED = "rate_limited"
    STALE = "stale"


_SCORE_DECAY_HALF_LIFE_S = 3600.0
_STALE_ERROR_CODES = {401, 403}
_TRANSIENT_ERROR_CODES = {429, 500, 502, 503, 504}
_DEGRADED_THRESHOLD = 3
_STALE_CONSECUTIVE_FAILURES = 5


@dataclass
class KeyState:
    """Per-key runtime and persistent state."""
    key_id: str
    provider: str
    status: str = KeyStatus.ACTIVE
    total_requests: int = 0
    total_successes: int = 0
    total_failures: int = 0
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    last_success_t: float = 0.0
    last_failure_t: float = 0.0
    last_request_t: float = 0.0
    last_error: str = ""
    last_error_code: int = 0
    avg_latency_s: float = 0.0
    stale_reason: str = ""
    stale_since: float = 0.0

    rate_limit_remaining: int = -1
    rate_limit_reset_t: float = 0.0
    rate_limit_pool_id: str = ""

    _score_cache: float = field(default=1.0, repr=False)
    _score_t: float = field(default=0.0, repr=False)

    def compute_score(self, now: float = 0) -> float:
        """Compute adaptive selection weight.

        Higher = more preferred. Factors:
        - Success rate (exponentially weighted recent)
        - Latency (lower is better)
        - Recency of last success
        - Penalty for consecutive failures
        """
        if not now:
            now = time.time()

        if self.status == KeyStatus.STALE:
            return 0.0

        if now - self._score_t < 5.0:
            return self._score_cache

        base = 1.0

        if self.total_requests > 0:
            success_rate = self.total_successes / self.total_requests
            base *= (0.3 + 0.7 * success_rate)

        if self.avg_latency_s > 0:
            latency_factor = 1.0 / (1.0 + self.avg_latency_s / 5.0)
            base *= latency_factor

        if self.consecutive_failures > 0:
            penalty = 0.5 ** min(self.consecutive_failures, 5)
            base *= penalty

        if self.last_success_t > 0:
            age = now - self.last_success_t
            recency = math.exp(-age / _SCORE_DECAY_HALF_LIFE_S * math.log(2))
            base *= (0.5 + 0.5 * recency)
        elif self.total_requests == 0:
            base *= 0.9

        if self.status == KeyStatus.RATE_LIMITED:
            if self.rate_limit_reset_t > now:
                base *= 0.1
            else:
                self.status = KeyStatus.ACTIVE

        self._score_cache = max(base, 0.01)
        self._score_t = now
        return self._score_cache

    def record_success(self, latency_s: float = 0, headers: Dict[str, str] = None):
        now = time.time()
        self.total_requests += 1
        self.total_successes += 1
        self.consecutive_successes += 1
        self.consecutive_failures = 0
        self.last_success_t = now
        self.last_request_t = now
        self.last_error = ""
        self.last_error_code = 0

        if latency_s > 0:
            alpha = 0.3
            if self.avg_latency_s > 0:
                self.avg_latency_s = alpha * latency_s + (1 - alpha) * self.avg_latency_s
            else:
                self.avg_latency_s = latency_s

        if self.status in (KeyStatus.DEGRADED, KeyStatus.RATE_LIMITED):
            self.status = KeyStatus.ACTIVE
            self.stale_reason = ""

        if headers:
            self._parse_rate_headers(headers)

        self._score_t = 0

    def record_failure(self, error: str = "", error_code: int = 0,
                       headers: Dict[str, str] = None):
        now = time.time()
        self.total_requests += 1
        self.total_failures += 1
        self.consecutive_failures += 1
        self.consecutive_successes = 0
        self.last_failure_t = now
        self.last_request_t = now
        self.last_error = error[:200]
        self.last_error_code = error_code

        if error_code in _STALE_ERROR_CODES:
            self.status = KeyStatus.STALE
            self.stale_since = now
            self.stale_reason = f"Auth failure ({error_code})"
        elif error_code == 429:
            self.status = KeyStatus.RATE_LIMITED
            if headers:
                self._parse_rate_headers(headers)
            retry_after = self._parse_retry_delay(headers, error)
            if retry_after and retry_after > 0:
                self.rate_limit_reset_t = now + retry_after
            elif self.rate_limit_reset_t <= now:
                self.rate_limit_reset_t = now + min(2 ** self.consecutive_failures, 120)
        elif self.consecutive_failures >= _STALE_CONSECUTIVE_FAILURES:
            self.status = KeyStatus.STALE
            self.stale_since = now
            self.stale_reason = f"Consecutive failures ({self.consecutive_failures})"
        elif self.consecutive_failures >= _DEGRADED_THRESHOLD:
            self.status = KeyStatus.DEGRADED

        if headers:
            self._parse_rate_headers(headers)

        self._score_t = 0

    @staticmethod
    def _parse_retry_delay(headers: Dict[str, str] = None,
                           error: str = "") -> Optional[float]:
        """Extract retry delay from headers or error body.

        Checks Retry-After header first, then retryDelay in error text.
        Returns seconds to wait, or None if not found.
        """
        if headers:
            retry = headers.get("retry-after")
            if retry:
                try:
                    return float(retry)
                except ValueError:
                    pass

        if error and "retryDelay" in error:
            import re
            m = re.search(r'"retryDelay"\s*:\s*"(\d+(?:\.\d+)?)s?"', error)
            if m:
                return float(m.group(1))
        return None

    def _parse_rate_headers(self, headers: Dict[str, str]):
        """Extract rate limit info from response headers."""
        remaining = headers.get("x-ratelimit-remaining-requests")
        if remaining is not None:
            try:
                self.rate_limit_remaining = int(remaining)
            except (ValueError, TypeError):
                pass

        reset = headers.get("x-ratelimit-reset-requests")
        if reset is not None:
            try:
                self.rate_limit_reset_t = time.time() + float(reset.rstrip("s"))
            except (ValueError, TypeError):
                pass

        pool_id = headers.get("x-ratelimit-limit-requests")
        if pool_id is not None:
            self.rate_limit_pool_id = str(pool_id)

    def reactivate(self):
        """Reactivate a stale key after successful re-verification."""
        self.status = KeyStatus.ACTIVE
        self.stale_reason = ""
        self.stale_since = 0.0
        self.consecutive_failures = 0
        self.last_error = ""
        self.last_error_code = 0
        self._score_t = 0

    def to_dict(self) -> dict:
        d = {
            "status": self.status,
            "total_requests": self.total_requests,
            "total_successes": self.total_successes,
            "total_failures": self.total_failures,
            "consecutive_failures": self.consecutive_failures,
            "last_success_t": self.last_success_t,
            "last_failure_t": self.last_failure_t,
            "avg_latency_s": round(self.avg_latency_s, 3),
            "stale_reason": self.stale_reason,
            "stale_since": self.stale_since,
            "rate_limit_pool_id": self.rate_limit_pool_id,
        }
        return {k: v for k, v in d.items() if v}

    @classmethod
    def from_dict(cls, key_id: str, provider: str, data: dict) -> "KeyState":
        return cls(
            key_id=key_id,
            provider=provider,
            status=data.get("status", KeyStatus.ACTIVE),
            total_requests=data.get("total_requests", 0),
            total_successes=data.get("total_successes", 0),
            total_failures=data.get("total_failures", 0),
            consecutive_failures=data.get("consecutive_failures", 0),
            last_success_t=data.get("last_success_t", 0.0),
            last_failure_t=data.get("last_failure_t", 0.0),
            avg_latency_s=data.get("avg_latency_s", 0.0),
            stale_reason=data.get("stale_reason", ""),
            stale_since=data.get("stale_since", 0.0),
            rate_limit_pool_id=data.get("rate_limit_pool_id", ""),
        )


class AdaptiveKeySelector:
    """Selects API keys based on adaptive scoring.

    Instead of round-robin, keys are selected probabilistically
    weighted by their health score. Keys with higher success rates,
    lower latency, and recent successes are preferred.

    Stale keys are excluded entirely until re-verified.
    """

    def __init__(self, provider: str):
        self._provider = provider
        self._states: Dict[str, KeyState] = {}
        self._lock = threading.Lock()
        self._load()

    def _load(self):
        """Load key states from per-provider data."""
        from tool.LLM.logic.config import get_provider_config, get_api_keys
        keys = get_api_keys(self._provider)
        pcfg = get_provider_config(self._provider)
        saved_states = pcfg.get("key_states", {})

        for k in keys:
            kid = k["id"]
            if kid in saved_states:
                self._states[kid] = KeyState.from_dict(kid, self._provider, saved_states[kid])
            else:
                self._states[kid] = KeyState(key_id=kid, provider=self._provider)

    def _save(self):
        """Persist key states to per-provider data."""
        from tool.LLM.logic.config import _load_provider_keys, _save_provider_keys
        pcfg = _load_provider_keys(self._provider)
        pcfg["key_states"] = {kid: st.to_dict() for kid, st in self._states.items()}
        _save_provider_keys(self._provider, pcfg)

    def select(self) -> Tuple[Optional[str], Optional[str]]:
        """Select the best available key.

        Returns (key_id, api_key) or (None, None) if no keys available.
        Uses weighted random selection: keys with higher scores have
        higher probability of being selected, but lower-scored keys
        still get occasional tries for re-evaluation.
        """
        from tool.LLM.logic.config import get_api_keys

        with self._lock:
            keys = get_api_keys(self._provider)
            if not keys:
                return None, None

            key_map = {k["id"]: k["key"] for k in keys}
            now = time.time()

            for k in keys:
                if k["id"] not in self._states:
                    self._states[k["id"]] = KeyState(key_id=k["id"], provider=self._provider)

            candidates = []
            for kid, state in self._states.items():
                if kid not in key_map:
                    continue
                score = state.compute_score(now)
                if score > 0:
                    candidates.append((kid, score))

            if not candidates:
                first_key = keys[0]
                return first_key["id"], first_key["key"]

            total_weight = sum(s for _, s in candidates)
            r = random.uniform(0, total_weight)
            cumulative = 0
            for kid, score in candidates:
                cumulative += score
                if r <= cumulative:
                    return kid, key_map[kid]

            kid = candidates[-1][0]
            return kid, key_map[kid]

    def report(self, key_id: str, result: Dict[str, Any],
               headers: Dict[str, str] = None):
        """Report the result of an API call for adaptive feedback.

        Args:
            key_id: The key that was used.
            result: Provider result dict with ok, error_code, latency_s, etc.
            headers: Response headers (for rate limit info).
        """
        with self._lock:
            state = self._states.get(key_id)
            if not state:
                state = KeyState(key_id=key_id, provider=self._provider)
                self._states[key_id] = state

            if result.get("ok"):
                state.record_success(
                    latency_s=result.get("latency_s", 0),
                    headers=headers,
                )
            else:
                state.record_failure(
                    error=result.get("error", ""),
                    error_code=result.get("error_code", 0),
                    headers=headers,
                )

            if result.get("error_code") == 429:
                self._check_shared_pool(key_id)

            self._save()

    def _check_shared_pool(self, triggered_key_id: str):
        """Detect keys sharing the same rate-limit pool.

        If two keys have the same rate_limit_pool_id (from headers),
        they likely belong to the same account. When one key hits 429,
        mark the other(s) as rate_limited too.
        """
        triggered = self._states.get(triggered_key_id)
        if not triggered or not triggered.rate_limit_pool_id:
            return

        pool_id = triggered.rate_limit_pool_id
        for kid, state in self._states.items():
            if kid == triggered_key_id:
                continue
            if state.rate_limit_pool_id == pool_id and state.status == KeyStatus.ACTIVE:
                state.status = KeyStatus.RATE_LIMITED
                state.rate_limit_reset_t = triggered.rate_limit_reset_t

    def reverify(self, key_id: str) -> Dict[str, Any]:
        """Re-verify a stale key by making a health check.

        Returns {"ok": True} if key is now active, {"ok": False, "error": ...} otherwise.
        """
        from tool.LLM.logic.config import get_api_keys

        with self._lock:
            keys = get_api_keys(self._provider)
            key_map = {k["id"]: k["key"] for k in keys}
            api_key = key_map.get(key_id)
            if not api_key:
                return {"ok": False, "error": "Key not found"}
            state = self._states.get(key_id)

        try:
            from tool.LLM.logic.registry import get_provider
            provider = get_provider(f"{self._provider}-*", api_key=api_key)
            result = provider.health_check()

            with self._lock:
                if result.get("healthy"):
                    if state:
                        state.reactivate()
                    self._save()
                    return {"ok": True}
                else:
                    if state:
                        state.record_failure(
                            error=result.get("error", "Health check failed"),
                            error_code=0,
                        )
                    self._save()
                    return {"ok": False, "error": result.get("error", "Health check failed")}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def get_active_count(self) -> int:
        """Count of non-stale keys."""
        return sum(1 for s in self._states.values()
                   if s.status != KeyStatus.STALE)

    def has_usable_keys(self) -> bool:
        """Whether any key is available for API calls."""
        if not self._states:
            return False
        return any(s.status != KeyStatus.STALE for s in self._states.values())

    def get_all_states(self) -> Dict[str, Dict]:
        """Return all key states for status display."""
        with self._lock:
            now = time.time()
            return {
                kid: {
                    **state.to_dict(),
                    "score": round(state.compute_score(now), 3),
                    "key_id": kid,
                }
                for kid, state in self._states.items()
            }


_selectors: Dict[str, AdaptiveKeySelector] = {}
_sel_lock = threading.Lock()


def get_selector(provider: str) -> AdaptiveKeySelector:
    """Get or create an AdaptiveKeySelector for a provider."""
    with _sel_lock:
        if provider not in _selectors:
            _selectors[provider] = AdaptiveKeySelector(provider)
        return _selectors[provider]
