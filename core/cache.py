import hashlib
import json
import time
from pathlib import Path

CACHE_DIR = Path(__file__).parent.parent / ".cache"
CACHE_TTL = 3600  # 1 heure


def _key(query: str, context: list[str]) -> str:
    raw = query + "|".join(context)
    return hashlib.sha256(raw.encode()).hexdigest()


def get(query: str, context: list[str]) -> dict | None:
    CACHE_DIR.mkdir(exist_ok=True)
    path = CACHE_DIR / f"{_key(query, context)}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if time.time() - data["ts"] > CACHE_TTL:
        path.unlink(missing_ok=True)
        return None
    return data["result"]


def set(query: str, context: list[str], result: dict):
    CACHE_DIR.mkdir(exist_ok=True)
    path = CACHE_DIR / f"{_key(query, context)}.json"
    path.write_text(
        json.dumps({"ts": time.time(), "result": result}, indent=2),
        encoding="utf-8",
    )
