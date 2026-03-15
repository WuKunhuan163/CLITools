"""Token-bucket rate limiter with configurable jitter.

Enforces a hard RPM cap and adds random delays between requests
to mimic human-paced interactions and avoid triggering anti-bot
detection on upstream services.
"""
import time
import random
import threading


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

            if waited > 0:
                time.sleep(waited)

            self._last_request_time = time.time()
            self._request_times.append(self._last_request_time)

        return waited

    def reset(self):
        """Clear request history."""
        with self._lock:
            self._request_times.clear()
            self._last_request_time = 0.0
