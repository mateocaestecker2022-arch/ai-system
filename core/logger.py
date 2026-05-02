import json
import time
from pathlib import Path


class Logger:
    """
    Logger JSONL local — complément au Tracer HTTP.
    Toujours disponible même sans dashboard déployé.
    """

    def __init__(self, path: str = "events.jsonl"):
        self._path = Path(path)

    def log(self, event: dict):
        event.setdefault("timestamp", time.time())
        with self._path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")

    def read_all(self) -> list[dict]:
        if not self._path.exists():
            return []
        events = []
        for line in self._path.read_text(encoding="utf-8").splitlines():
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return events

    def tail(self, n: int = 50) -> list[dict]:
        return self.read_all()[-n:]
