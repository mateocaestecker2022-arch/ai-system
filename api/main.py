from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import asyncio
import json

from core.config import Config
from core.orchestrator import Orchestrator
from core.llm import stream_llm_async
from tools.indexer import build_and_save, is_index_stale

app = FastAPI(title="AI System", version="1.0.0")
config = Config()
orchestrator = Orchestrator(config)


class RunRequest(BaseModel):
    project: str
    query: str


class IndexRequest(BaseModel):
    project: str


@app.get("/health")
def health():
    return {"status": "ok"}


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


@app.post("/stream")
async def stream(req: RunRequest):
    """Stream la réponse du Coder token par token."""
    async def generate():
        # Planner + Memory
        tasks = await asyncio.to_thread(orchestrator.planner.plan, req.query)
        context = await asyncio.to_thread(
            orchestrator.memory.get_context, req.project, tasks
        )

        tasks_str = "\n".join(
            f"[{t['type'].upper()}] {t['description']} → {t['target']}"
            for t in tasks
        )
        context_str = "\n---\n".join(context) if context else "No context."

        from agents.coder import CODER_PROMPT
        prompt = CODER_PROMPT.format(tasks=tasks_str, context=context_str)

        async for chunk in stream_llm_async(prompt, config):
            yield f"data: {json.dumps({'text': chunk})}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/status")
async def status(project: str):
    stale = await asyncio.to_thread(is_index_stale, project)
    return {"project": project, "index_stale": stale}
