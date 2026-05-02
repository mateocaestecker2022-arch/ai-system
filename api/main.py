from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
import json

from core.config import Config
from core.orchestrator import Orchestrator
from core.llm import stream_llm_async
from core.tokens import compress
from core.logger import Logger
from tools.indexer import build_and_save, is_index_stale
from api.auth import create_token, get_current_project
from api.rate_limit import check as rate_check

app = FastAPI(title="AI System", version="3.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

config = Config()
orchestrator = Orchestrator(config)
logger = Logger()


# ------------------------------------------------------------------ #
# Models                                                               #
# ------------------------------------------------------------------ #

class RunRequest(BaseModel):
    project: str
    query: str

class ScanRequest(BaseModel):
    project: str
    auto_fix: bool = False

class IndexRequest(BaseModel):
    project: str

class TokenRequest(BaseModel):
    project_id: str


# ------------------------------------------------------------------ #
# Auth                                                                 #
# ------------------------------------------------------------------ #

@app.post("/auth/token")
def get_token(req: TokenRequest):
    """Génère un JWT pour un project_id donné."""
    return {"token": create_token(req.project_id), "project_id": req.project_id}


# ------------------------------------------------------------------ #
# Core endpoints (protégés JWT + rate limit)                          #
# ------------------------------------------------------------------ #

@app.get("/health")
def health():
    return {"status": "ok", "version": "3.0.0"}


@app.post("/run")
async def run(req: RunRequest, project_id: str = Depends(get_current_project)):
    rate_check(project_id)
    # Isolation : le project dans le token doit matcher la requête
    if req.project.split("/")[-1].split("\\")[-1] != project_id and project_id != "admin":
        raise HTTPException(403, "Project mismatch with token")
    try:
        return await orchestrator.run_async(req.query, req.project)
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/scan")
async def scan(req: ScanRequest, project_id: str = Depends(get_current_project)):
    rate_check(project_id)
    try:
        return await orchestrator.scan_async(req.project, auto_fix=req.auto_fix)
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/index")
async def index_project(req: IndexRequest, project_id: str = Depends(get_current_project)):
    rate_check(project_id)
    try:
        chunks = await asyncio.to_thread(build_and_save, req.project)
        return {"status": "ok", "chunks": len(chunks)}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/stream")
async def stream(req: RunRequest, project_id: str = Depends(get_current_project)):
    rate_check(project_id)

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
async def status(project: str, project_id: str = Depends(get_current_project)):
    stale = await asyncio.to_thread(is_index_stale, project)
    return {"project": project, "index_stale": stale}


@app.get("/events")
def events(tail: int = 50, project_id: str = Depends(get_current_project)):
    all_events = logger.tail(tail)
    # Isolation par project_id
    if project_id != "admin":
        all_events = [
            e for e in all_events
            if e.get("project_id") == project_id or "project_id" not in e
        ]
    return all_events
