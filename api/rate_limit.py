import time
from collections import defaultdict
from fastapi import HTTPException, Request

# project_id → list of timestamps
_buckets: dict[str, list[float]] = defaultdict(list)
WINDOW_SEC = 60
MAX_REQUESTS = int(__import__("os").getenv("RATE_LIMIT_RPM", "20"))


def check(project_id: str):
    now = time.time()
    bucket = _buckets[project_id]
    # Purge old
    _buckets[project_id] = [t for t in bucket if now - t < WINDOW_SEC]
    if len(_buckets[project_id]) >= MAX_REQUESTS:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit: {MAX_REQUESTS} requests/min per project",
        )
    _buckets[project_id].append(now)
