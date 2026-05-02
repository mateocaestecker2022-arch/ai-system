import time
import uuid
import httpx
import asyncio
from contextlib import asynccontextmanager

COLLECTOR_URL = None  # Chargé depuis config


def _url(config) -> str | None:
    return getattr(config, "COLLECTOR_URL", None)


def new_trace_id() -> str:
    return str(uuid.uuid4())


class Span:
    def __init__(self, trace_id: str, agent: str, project_id: str, config, task_id: int | None = None):
        self.trace_id = trace_id
        self.agent = agent
        self.project_id = project_id
        self.config = config
        self.task_id = task_id
        self._start = time.time()
        self.tokens_input = 0
        self.tokens_output = 0

    def set_tokens(self, inp: int, out: int):
        self.tokens_input = inp
        self.tokens_output = out

    async def finish(self, status: str = "success", error: str | None = None):
        duration_ms = int((time.time() - self._start) * 1000)
        event = {
            "trace_id": self.trace_id,
            "project_id": self.project_id,
            "agent": self.agent,
            "event": "llm_call",
            "tokens_input": self.tokens_input,
            "tokens_output": self.tokens_output,
            "duration_ms": duration_ms,
            "status": status,
            "timestamp": int(time.time()),
            "metadata": {"task_id": self.task_id, "error": error},
        }
        await _emit(event, self.config)


class Tracer:
    def __init__(self, config):
        self.config = config

    def new_trace(self, project_path: str) -> str:
        return new_trace_id()

    def span(self, trace_id: str, agent: str, project_id: str, task_id: int | None = None) -> Span:
        return Span(trace_id, agent, project_id, self.config, task_id)

    async def trace_start(self, trace_id: str, project_id: str, query: str):
        await _emit({
            "trace_id": trace_id,
            "project_id": project_id,
            "agent": "Leader",
            "event": "trace_start",
            "tokens_input": 0,
            "tokens_output": 0,
            "duration_ms": 0,
            "status": "running",
            "timestamp": int(time.time()),
            "metadata": {"query": query[:200]},
        }, self.config)

    async def trace_end(self, trace_id: str, project_id: str, total_tokens: int, duration_ms: int, status: str = "success"):
        await _emit({
            "trace_id": trace_id,
            "project_id": project_id,
            "agent": "Leader",
            "event": "trace_end",
            "tokens_input": total_tokens,
            "tokens_output": 0,
            "duration_ms": duration_ms,
            "status": status,
            "timestamp": int(time.time()),
            "metadata": {},
        }, self.config)


async def _emit(event: dict, config):
    url = _url(config)
    if not url:
        return
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            await client.post(f"{url}/collect", json=event)
    except Exception:
        pass  # Ne jamais bloquer le pipeline pour du monitoring
