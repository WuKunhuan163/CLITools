"""Centralized rate limit queue manager.

Manages a per-provider queue with ETA estimation, aggressive bypass,
and feedback-driven pushback. Each (provider, model) pair maintains:

- next_safe_t: Timestamp after which calls are expected to succeed
- rpm_window: Sliding window of recent request timestamps
- tpm_window: Sliding window of (timestamp, token_count) pairs
- in_flight_tickets: Tracked tickets with TTL for orphan detection
- state: idle / throttled / cooldown / blocked

Usage:
    from tool.LLM.logic.rate_queue import get_queue_manager

    qm = get_queue_manager()

    # Check before committing
    eta = qm.estimate_wait("zhipu-glm-4.7-flash")
    if eta.wait_s > 30:
        print(f"Queue backed up, ~{eta.wait_s}s wait")
        return

    # Context-manager style (auto-cleanup on crash/exception):
    ticket = qm.enqueue("zhipu-glm-4.7-flash", context_tokens=4000, timeout=60)
    with ticket:
        result = provider._send_request(...)
        ticket.complete(result)

    # Aggressive call (bypass queue, may risk 429)
    ticket = qm.enqueue("zhipu-glm-4.7-flash", aggressive=True)
    with ticket:
        result = provider._send_request(...)
        ticket.complete(result)
"""
import json
import time
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
from enum import Enum


_IN_FLIGHT_TTL_S = 300.0


class ProviderState(Enum):
    IDLE = "idle"
    ACTIVE = "active"
    THROTTLED = "throttled"
    COOLDOWN = "cooldown"
    BLOCKED = "blocked"


@dataclass
class RateLimits:
    """Rate limit configuration for a provider."""
    rpm: int = 30
    tpm: int = 0
    rpd: int = 0
    max_concurrency: int = 0
    min_interval_s: float = 2.0
    jitter_s: float = 1.0
    context_threshold_tokens: int = 0
    large_context_delay_s: float = 5.0

    @classmethod
    def from_model_json(cls, model_json: dict, tier: str = "free") -> "RateLimits":
        limits = model_json.get("rate_limits", {}).get(tier, {})
        settings = model_json.get("recommended_settings", {})
        return cls(
            rpm=limits.get("rpm", 30),
            tpm=limits.get("tpm", 0),
            rpd=limits.get("rpd", 0),
            max_concurrency=limits.get("max_concurrency", 0),
            min_interval_s=settings.get("min_interval_s", 2.0),
            jitter_s=settings.get("jitter_s", 1.0),
            context_threshold_tokens=limits.get("context_threshold_tokens") or 0,
            large_context_delay_s=settings.get("large_context_delay_s", 5.0),
        )


@dataclass
class WaitEstimate:
    """Estimated wait time for a queued request."""
    wait_s: float = 0.0
    queue_position: int = 0
    queue_length: int = 0
    state: ProviderState = ProviderState.IDLE
    next_safe_t: float = 0.0
    reason: str = ""

    @property
    def available_now(self) -> bool:
        return self.wait_s <= 0.0


class QueueTimeout(Exception):
    """Raised when enqueue() exceeds the caller's timeout."""
    pass


class Ticket:
    """A queued request handle with wait/cancel semantics.

    Use as a context manager for automatic cleanup:
        with qm.enqueue("provider") as ticket:
            result = do_api_call()
            ticket.complete(result)
    If an exception occurs, the ticket is automatically cancelled
    and in_flight is decremented.
    """

    def __init__(self, provider_name: str, context_tokens: int = 0,
                 aggressive: bool = False):
        self.provider_name = provider_name
        self.context_tokens = context_tokens
        self.aggressive = aggressive
        self.created_at = time.time()
        self.granted_at: float = 0.0
        self._event = threading.Event()
        self._result: Optional[Dict[str, Any]] = None
        self._cancelled = False
        self._completed = False
        self._manager: Optional["RateQueueManager"] = None

    def _bind(self, manager: "RateQueueManager"):
        self._manager = manager

    def wait(self, timeout: Optional[float] = None) -> bool:
        """Block until this ticket's turn. Returns True if granted."""
        if self.aggressive:
            return True
        return self._event.wait(timeout=timeout)

    def grant(self):
        """Signal that this ticket may proceed."""
        self.granted_at = time.time()
        self._event.set()

    def cancel(self):
        """Cancel this ticket."""
        self._cancelled = True
        self._event.set()

    @property
    def cancelled(self) -> bool:
        return self._cancelled

    @property
    def completed(self) -> bool:
        return self._completed

    def complete(self, result: Dict[str, Any]):
        """Report the API call result for feedback."""
        if self._completed:
            return
        self._completed = True
        self._result = result
        if self._manager:
            self._manager.complete(self, result)

    @property
    def result(self) -> Optional[Dict[str, Any]]:
        return self._result

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self._completed and not self._cancelled:
            if exc_type is not None:
                self._cancelled = True
            if self._manager:
                self._manager._release_ticket(self)
        return False


@dataclass
class ProviderQueue:
    """Per-provider queue state."""
    name: str
    limits: RateLimits
    state: ProviderState = ProviderState.IDLE
    next_safe_t: float = 0.0
    rpm_window: List[float] = field(default_factory=list)
    tpm_window: List[tuple] = field(default_factory=list)
    rpd_count: int = 0
    rpd_date: str = ""
    in_flight: int = 0
    in_flight_tickets: Dict[int, float] = field(default_factory=dict)
    consecutive_429s: int = 0
    last_429_t: float = 0.0
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def _prune_windows(self, now: float):
        cutoff_60 = now - 60.0
        self.rpm_window = [t for t in self.rpm_window if t > cutoff_60]
        self.tpm_window = [(t, n) for t, n in self.tpm_window if t > cutoff_60]
        today = time.strftime("%Y-%m-%d")
        if self.rpd_date != today:
            self.rpd_count = 0
            self.rpd_date = today

    def _reap_orphans(self, now: float) -> int:
        """Remove tickets that have been in-flight past the TTL.
        Returns number of reaped orphans."""
        reaped = 0
        expired = [tid for tid, t in self.in_flight_tickets.items()
                    if now - t > _IN_FLIGHT_TTL_S]
        for tid in expired:
            del self.in_flight_tickets[tid]
            self.in_flight = max(0, self.in_flight - 1)
            reaped += 1
        return reaped

    def compute_next_safe_t(self, now: float = 0) -> float:
        """Compute the earliest timestamp at which a new request is safe."""
        if now <= 0:
            now = time.time()
        self._prune_windows(now)
        self._reap_orphans(now)
        earliest = now

        if self.rpm_window and self.limits.rpm > 0:
            if len(self.rpm_window) >= self.limits.rpm:
                window_start = self.rpm_window[0]
                rpm_earliest = window_start + 60.0 + 0.1
                earliest = max(earliest, rpm_earliest)

        if self.limits.tpm > 0:
            recent_tokens = sum(n for _, n in self.tpm_window)
            if recent_tokens >= self.limits.tpm:
                if self.tpm_window:
                    tpm_earliest = self.tpm_window[0][0] + 60.0 + 0.1
                    earliest = max(earliest, tpm_earliest)

        if self.limits.rpd > 0 and self.rpd_count >= self.limits.rpd:
            tomorrow = time.mktime(time.strptime(
                time.strftime("%Y-%m-%d", time.localtime(now + 86400)),
                "%Y-%m-%d"))
            earliest = max(earliest, tomorrow)

        if self.limits.max_concurrency > 0 and self.in_flight >= self.limits.max_concurrency:
            earliest = max(earliest, now + self.limits.min_interval_s)

        if self.consecutive_429s > 0:
            backoff = min(2 ** self.consecutive_429s, 120)
            earliest = max(earliest, self.last_429_t + backoff)

        if self.rpm_window:
            last = self.rpm_window[-1]
            min_gap = last + self.limits.min_interval_s
            earliest = max(earliest, min_gap)

        self.next_safe_t = earliest
        return earliest

    def estimate_wait(self, position: int = 0) -> WaitEstimate:
        """Estimate wait time for a request at the given queue position."""
        now = time.time()
        safe_t = self.compute_next_safe_t(now)

        base_wait = max(0, safe_t - now)
        if self.limits.rpm > 0 and position > 0:
            per_slot = 60.0 / self.limits.rpm
            base_wait += position * per_slot

        state = self.state
        if self.consecutive_429s >= 3:
            state = ProviderState.COOLDOWN
        elif base_wait > 0:
            state = ProviderState.THROTTLED

        reason = ""
        if self.consecutive_429s > 0:
            reason = f"429 backoff (x{self.consecutive_429s})"
        elif self.limits.rpm > 0 and len(self.rpm_window) >= self.limits.rpm:
            reason = "RPM limit reached"
        elif self.limits.rpd > 0 and self.rpd_count >= self.limits.rpd:
            reason = "Daily request limit reached"
        elif self.limits.max_concurrency > 0 and self.in_flight >= self.limits.max_concurrency:
            reason = "Max concurrency reached"

        return WaitEstimate(
            wait_s=round(base_wait, 2),
            queue_position=position,
            queue_length=0,
            state=state,
            next_safe_t=safe_t,
            reason=reason,
        )

    def record_request(self, ticket_id: int, context_tokens: int = 0):
        """Record that a request was dispatched now."""
        now = time.time()
        self.rpm_window.append(now)
        if context_tokens > 0:
            self.tpm_window.append((now, context_tokens))
        self.rpd_count += 1
        self.in_flight += 1
        self.in_flight_tickets[ticket_id] = now

    def record_complete(self, ticket_id: int, result: Dict[str, Any]):
        """Record that a request completed. Adjusts state based on result."""
        self.in_flight_tickets.pop(ticket_id, None)
        self.in_flight = max(0, self.in_flight - 1)
        error_code = result.get("error_code", 0)

        if result.get("ok"):
            self.consecutive_429s = 0
            self.state = ProviderState.IDLE
        elif error_code == 429:
            self.consecutive_429s += 1
            self.last_429_t = time.time()
            self.state = ProviderState.COOLDOWN
            retry_after = result.get("retry_after_s")
            if retry_after and retry_after > 0:
                self.next_safe_t = max(self.next_safe_t, time.time() + retry_after)
            self._pushback_all()
        elif 500 <= error_code < 600:
            self.state = ProviderState.THROTTLED

    def record_release(self, ticket_id: int):
        """Release an in-flight slot without a result (crash/cancel cleanup)."""
        self.in_flight_tickets.pop(ticket_id, None)
        self.in_flight = max(0, self.in_flight - 1)

    def _pushback_all(self):
        """Push back next_safe_t after a 429."""
        backoff = min(2 ** self.consecutive_429s, 120)
        self.next_safe_t = max(self.next_safe_t, time.time() + backoff)

    def reset(self):
        """Reset all transient state. Safe to call after recovery."""
        self.state = ProviderState.IDLE
        self.next_safe_t = 0.0
        self.rpm_window.clear()
        self.tpm_window.clear()
        self.in_flight = 0
        self.in_flight_tickets.clear()
        self.consecutive_429s = 0
        self.last_429_t = 0.0


class RateQueueManager:
    """Singleton managing rate queues for all providers.

    Thread-safe. All providers share one manager that coordinates
    request scheduling across the entire system.
    """

    def __init__(self):
        self._queues: Dict[str, ProviderQueue] = {}
        self._lock = threading.Lock()

    def register_provider(self, name: str, limits: RateLimits):
        """Register a provider with its rate limits."""
        with self._lock:
            if name not in self._queues:
                self._queues[name] = ProviderQueue(name=name, limits=limits)
            else:
                self._queues[name].limits = limits

    def _ensure_provider(self, name: str) -> ProviderQueue:
        """Get or create a provider queue with default limits."""
        with self._lock:
            if name not in self._queues:
                limits = self._load_limits(name)
                self._queues[name] = ProviderQueue(name=name, limits=limits)
            return self._queues[name]

    @staticmethod
    def _load_limits(provider_name: str) -> RateLimits:
        """Load rate limits from model.json for a provider."""
        models_dir = Path(__file__).parent / "models"
        if not models_dir.is_dir():
            return RateLimits()

        for model_dir in models_dir.iterdir():
            if not model_dir.is_dir():
                continue
            mj = model_dir / "model.json"
            if not mj.exists():
                continue
            try:
                meta = json.loads(mj.read_text())
            except Exception:
                continue
            providers_dir = model_dir / "providers"
            if providers_dir.is_dir():
                for pd in providers_dir.iterdir():
                    if pd.is_dir() and pd.name in provider_name:
                        return RateLimits.from_model_json(meta)
        return RateLimits()

    def estimate_wait(self, provider_name: str) -> WaitEstimate:
        """Estimate how long a new request would wait."""
        pq = self._ensure_provider(provider_name)
        with pq._lock:
            return pq.estimate_wait()

    def enqueue(self, provider_name: str, context_tokens: int = 0,
                aggressive: bool = False, timeout: Optional[float] = None) -> Ticket:
        """Enqueue a request and return a Ticket.

        Args:
            provider_name: Registered provider name.
            context_tokens: Estimated input tokens for TPM tracking.
            aggressive: If True, bypass queue and return immediately.
            timeout: Max seconds to wait for a slot. None = no limit.
                Raises QueueTimeout if exceeded.

        Returns:
            A Ticket. Use as context manager for automatic cleanup:
                with qm.enqueue("provider", timeout=60) as ticket:
                    result = api_call()
                    ticket.complete(result)
        """
        pq = self._ensure_provider(provider_name)
        ticket = Ticket(provider_name, context_tokens, aggressive)
        ticket._bind(self)
        tid = id(ticket)

        if aggressive:
            with pq._lock:
                pq.record_request(tid, context_tokens)
            return ticket

        deadline = time.time() + timeout if timeout else None

        while True:
            with pq._lock:
                now = time.time()
                if deadline and now >= deadline:
                    raise QueueTimeout(
                        f"Timed out after {timeout}s waiting for {provider_name}")
                safe_t = pq.compute_next_safe_t(now)
                max_conc = max(pq.limits.max_concurrency, 1)

                if safe_t <= now and pq.in_flight < max_conc:
                    pq.record_request(tid, context_tokens)
                    ticket.grant()
                    return ticket
                else:
                    wait_s = max(0.1, safe_t - now)
                    if deadline:
                        wait_s = min(wait_s, deadline - now)

            time.sleep(min(wait_s, 2.0))

    def complete(self, ticket: Ticket, result: Dict[str, Any]):
        """Report that a request completed. Updates queue state."""
        if not isinstance(result, dict):
            result = {"ok": True}
        pq = self._ensure_provider(ticket.provider_name)
        with pq._lock:
            pq.record_complete(id(ticket), result)

    def _release_ticket(self, ticket: Ticket):
        """Release an in-flight ticket without a result (crash/cancel)."""
        pq = self._ensure_provider(ticket.provider_name)
        with pq._lock:
            pq.record_release(id(ticket))

    def cancel(self, ticket: Ticket):
        """Cancel a ticket and release its in-flight slot."""
        ticket.cancel()
        self._release_ticket(ticket)

    def reset_provider(self, provider_name: str):
        """Reset all transient state for a provider. Use after recovery."""
        pq = self._ensure_provider(provider_name)
        with pq._lock:
            pq.reset()

    def get_status(self, provider_name: str = None) -> Dict[str, Any]:
        """Get queue status for one or all providers."""
        if provider_name:
            pq = self._ensure_provider(provider_name)
            with pq._lock:
                return self._format_status(pq)
        with self._lock:
            result = {}
            for name, pq in self._queues.items():
                with pq._lock:
                    result[name] = self._format_status(pq)
            return result

    @staticmethod
    def _format_status(pq: ProviderQueue) -> Dict[str, Any]:
        now = time.time()
        safe_t = pq.compute_next_safe_t(now)
        return {
            "name": pq.name,
            "state": pq.state.value,
            "in_flight": pq.in_flight,
            "orphan_candidates": sum(
                1 for t in pq.in_flight_tickets.values()
                if now - t > _IN_FLIGHT_TTL_S * 0.5),
            "next_safe_t": safe_t,
            "wait_s": round(max(0, safe_t - now), 2),
            "consecutive_429s": pq.consecutive_429s,
            "rpm_used": len(pq.rpm_window),
            "rpm_limit": pq.limits.rpm,
            "rpd_used": pq.rpd_count,
            "rpd_limit": pq.limits.rpd,
        }


_instance: Optional[RateQueueManager] = None
_instance_lock = threading.Lock()


def get_queue_manager() -> RateQueueManager:
    """Get the singleton RateQueueManager."""
    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:
                _instance = RateQueueManager()
    return _instance
