import time
from collections import defaultdict, deque

# key -> deque[timestamps]
_BUCKETS: dict[str, deque[float]] = defaultdict(deque)

def hit(key: str, limit: int, window_sec: int) -> bool:
    """
    Returns True if allowed, False if rate-limited.
    """
    now = time.time()
    q = _BUCKETS[key]

    # drop old
    cutoff = now - window_sec
    while q and q[0] < cutoff:
        q.popleft()

    if len(q) >= limit:
        return False

    q.append(now)
    return True
