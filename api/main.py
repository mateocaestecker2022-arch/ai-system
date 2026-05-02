from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import asyncio
import json

from core.config import Config
from core.orchestrator import Orchestrator
from core.llm import stream_llm_async
from core.tokens import compress
from tools.indexer import build_and_save, is_index_stale

app = FastAPI(title="AI System V2", version="2.0.0")
config = Config()
orchestrator = Orchestrator(config)


class RunRequest(BaseModel):
    project: str
    query: str


class ScanRequest(BaseModel):
    project: str
    auto_fix: bool = False


class IndexRequest(BaseModel):
    project: str


@app.get("/health")
def health():
    return {"status": "ok", "version": "2.0.0"}


@app.post("/index")
def index_project(req: IndexRequest):
    try:
        chunks = build_and_save(req.project)
        return {"status": "ok", "chunks": len(chunks), "project": req.project}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/run")
async def run(req: RunRequest):
    try:
        result = await orchestrator.run_async(req.query, req.project)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/scan")
async def scan(req: ScanRequest):
    try:
        result = await orchestrator.scan_async(req.project, auto_fix=req.auto_fix)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/stream")
async def stream(req: RunRequest):
    """Stream le diff du premier coder token par token (SSE)."""
    async def generate():
        tasks = await asyncio.to_thread(orchestrator.planner.plan, req.query)
        if not tasks:
            yield "data: [DONE]\n\n"
            return

        task = tasks[0]
        context = await asyncio.to_thread(
            orchestrator.memory.get_context_for_task, req.project, task
        )
        context_str = compress("\n---\n".join(context), config.MAX_CONTEXT_TOKENS)

        from agents.coder import CODER_PROMPT
        prompt = CODER_PROMPT.format(
            type=task.get("type", "modify"),
            description=task["description"],
            target=task.get("target", "unknown"),
            context=context_str,
        )

        async for chunk in stream_llm_async(prompt, config):
            yield f"data: {json.dumps({'text': chunk})}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/status")
async def status(project: str):
    stale = await asyncio.to_thread(is_index_stale, project)
    return {"project": project, "index_stale": stale}
