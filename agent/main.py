"""FastAPI application — the HTTP interface to the My Skilled Self agent.

Endpoints:
  GET  /health            — liveness probe
  GET  /skills            — list registered skills and their tools
  POST /chat              — single-turn non-streaming chat
  POST /chat/stream       — streaming chat (Server-Sent Events)
  GET  /market/overview   — live market snapshot (no agent, direct data)
  GET  /market/sectors    — live sector performance (no agent, direct data)
"""

import json
import logging
import os
import sys
import uuid
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

# Ensure the agent package root is on the path when running inside Docker
sys.path.insert(0, os.path.dirname(__file__))

from config import config
from skills.registry import get_skills_manifest
from skills.trading_advisor.data_fetcher import get_market_overview, get_sector_performance

logging.basicConfig(
    level=logging.DEBUG if config.debug else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Lifespan — warm up the ADK runner on startup
# ──────────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    if config.google_api_key:
        try:
            from agent_core import get_runner
            get_runner()
            logger.info("ADK agent runner ready.")
        except Exception as exc:
            logger.warning("ADK runner could not initialise: %s", exc)
    else:
        logger.warning("GOOGLE_API_KEY not set — agent will not function.")
    yield


# ──────────────────────────────────────────────────────────────────────────────
# App
# ──────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="My Skilled Self — AI Trading Agent",
    description=(
        "Google ADK-powered AI agent with pluggable skills: trading advisor "
        "with live market data and interactive chart generation."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────────────────────────────────────────────────────────────────
# Schemas
# ──────────────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = Field(default="default_user")


# ──────────────────────────────────────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "model": config.gemini_model,
        "app": config.app_name,
        "api_key_configured": bool(config.google_api_key),
    }


@app.get("/skills")
async def skills():
    return {"skills": get_skills_manifest()}


@app.post("/chat")
async def chat(req: ChatRequest):
    if not config.google_api_key:
        raise HTTPException(status_code=503, detail="GOOGLE_API_KEY not configured.")
    try:
        from agent_core import get_agent_response
        result = await get_agent_response(
            user_message=req.message,
            session_id=req.session_id,
            user_id=req.user_id,
        )
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Chat error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    if not config.google_api_key:
        raise HTTPException(status_code=503, detail="GOOGLE_API_KEY not configured.")

    from agent_core import stream_agent_response

    async def event_generator():
        try:
            async for chunk in stream_agent_response(
                user_message=req.message,
                session_id=req.session_id,
                user_id=req.user_id,
            ):
                yield f"data: {chunk}\n\n"
        except Exception as exc:
            logger.exception("Stream error: %s", exc)
            error_event = json.dumps({"type": "error", "message": str(exc)})
            yield f"data: {error_event}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/market/overview")
async def market_overview():
    """Direct market snapshot — no agent call needed."""
    return get_market_overview()


@app.get("/market/sectors")
async def market_sectors():
    """Direct sector performance — no agent call needed."""
    return get_sector_performance()


# ──────────────────────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=config.host,
        port=config.port,
        reload=config.debug,
        log_level="debug" if config.debug else "info",
    )
