"""Per-user rate limit for /ask: max `limit` requests per `window` seconds.
In-memory: fine for one Render instance; resets on restart."""
import threading
import time
from collections import defaultdict, deque


class RateLimiter:
    def __init__(self, limit=10, window=60.0, clock=time.monotonic):
        self.limit = limit
        self.window = window
        self.clock = clock
        self._hits = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key):
        """Return (allowed, retry_after_seconds)."""
        now = self.clock()
        with self._lock:
            q = self._hits[key]
            while q and now - q[0] >= self.window:
                q.popleft()
            if len(q) >= self.limit:
                retry = int(self.window - (now - q[0])) + 1
                return False, max(retry, 1)
            q.append(now)
            return True, 0
