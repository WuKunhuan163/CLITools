"""Token-bucket rate limiter with configurable jitter and retry support.

Enforces a hard RPM cap and adds random delays between requests
to mimic human-paced interactions and avoid triggering anti-bot
detection on upstream services.
"""
import time
import random
import threading
from typing import Callable, Any


class RateLimiter:
    """Thread-safe rate limiter with jitter.

    Parameters:
        rpm: Maximum requests per minute (0 = unlimited).
        min_interval_s: Minimum seconds between requests.
        jitter_s: Random additional delay range [0, jitter_s].
    """

    def __init__(self, rpm: int = 30, min_interval_s: float = 2.0,
                 jitter_s: float = 1.0):
        self.rpm = rpm
        self.min_interval_s = min_interval_s
        self.jitter_s = jitter_s
        self._lock = threading.Lock()
        self._last_request_time: float = 0.0
        self._request_times: list = []
        self._consecutive_429s: int = 0

    def wait(self) -> float:
        """Block until the next request is permitted.

        Returns the actual wait time in seconds.
        """
        with self._lock:
            now = time.time()
            waited = 0.0

            since_last = now - self._last_request_time
            if since_last < self.min_interval_s:
                gap = self.min_interval_s - since_last
                waited += gap

            if self.jitter_s > 0:
                jitter = random.uniform(0, self.jitter_s)
                waited += jitter

            if self.rpm > 0:
                cutoff = now - 60.0
                self._request_times = [
                    t for t in self._request_times if t > cutoff
                ]
                if len(self._request_times) >= self.rpm:
                    earliest = self._request_times[0]
                    rpm_wait = 60.0 - (now - earliest) + 0.1
                    if rpm_wait > waited:
                        waited = rpm_wait

            # Adaptive backoff: if recent 429s, add extra delay
            if self._consecutive_429s > 0:
                backoff = min(2 ** self._consecutive_429s, 60)
                waited += backoff

            if waited > 0:
                time.sleep(waited)

            self._last_request_time = time.time()
            self._request_times.append(self._last_request_time)

        return waited

    def report_429(self):
        """Signal that the last request was rate-limited (429).

        Increases adaptive backoff for subsequent requests.
        """
        with self._lock:
            self._consecutive_429s += 1

    def report_success(self):
        """Signal that the last request succeeded. Resets 429 counter."""
        with self._lock:
            self._consecutive_429s = 0

    def reset(self):
        """Clear request history."""
        with self._lock:
            self._request_times.clear()
            self._last_request_time = 0.0
            self._consecutive_429s = 0

    @property
    def consecutive_429s(self) -> int:
        return self._consecutive_429s


def retry_on_transient(fn: Callable[..., dict], max_retries: int = 3,
                       rate_limiter: 'RateLimiter' = None) -> dict:
    """Retry a send-like function on transient errors (429, 5xx, network).

    Args:
        fn: Callable that returns {"ok": bool, "error": str, ...}.
        max_retries: Maximum number of retry attempts.
        rate_limiter: If provided, reports 429s for adaptive backoff.

    Returns:
        The last result dict (success or final failure).
    """
    for attempt in range(max_retries + 1):
        result = fn()
        if result.get("ok"):
            if rate_limiter:
                rate_limiter.report_success()
            return result

        error = str(result.get("error", ""))
        error_code = result.get("error_code", 0)
        is_transient = (
            error_code == 429
            or 500 <= error_code < 600
            or "timeout" in error.lower()
            or "connection" in error.lower()
        )

        if not is_transient or attempt >= max_retries:
            return result

        if error_code == 429 and rate_limiter:
            rate_limiter.report_429()

        backoff = min(2 ** attempt + random.uniform(0, 1), 60)
        time.sleep(backoff)

    return result
