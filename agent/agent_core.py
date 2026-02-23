"""Google ADK agent setup.

Assembles the LlmAgent with all registered skills, creates the Runner with
an in-memory session store, and exposes async helpers for FastAPI to call.
"""

import json
import logging
import uuid
from typing import AsyncIterator

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

from config import config
from skills.registry import get_all_tools
from skills.trading_advisor.knowledge import SYSTEM_INSTRUCTION

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Build the agent
# ──────────────────────────────────────────────────────────────────────────────

def _build_agent() -> LlmAgent:
    tools = get_all_tools()
    logger.info("Registering %d tools with the agent.", len(tools))
    return LlmAgent(
        name=config.app_name,
        model=config.gemini_model,
        description=(
            "Expert AI trading and investing advisor with live market data access, "
            "technical analysis, fundamental analysis, and interactive chart generation."
        ),
        instruction=SYSTEM_INSTRUCTION,
        tools=tools,
    )


_agent: LlmAgent | None = None
_runner: Runner | None = None
_session_service = InMemorySessionService()


def get_runner() -> Runner:
    global _agent, _runner
    if _runner is None:
        _agent = _build_agent()
        _runner = Runner(
            agent=_agent,
            app_name=config.app_name,
            session_service=_session_service,
        )
        logger.info("ADK Runner initialised with model: %s", config.gemini_model)
    return _runner


# ──────────────────────────────────────────────────────────────────────────────
# Session management
# ──────────────────────────────────────────────────────────────────────────────

async def ensure_session(user_id: str, session_id: str) -> None:
    """Create a session if it does not already exist."""
    runner = get_runner()
    existing = await runner.session_service.get_session(
        app_name=config.app_name,
        user_id=user_id,
        session_id=session_id,
    )
    if existing is None:
        await runner.session_service.create_session(
            app_name=config.app_name,
            user_id=user_id,
            session_id=session_id,
        )


# ──────────────────────────────────────────────────────────────────────────────
# Streaming response generator
# ──────────────────────────────────────────────────────────────────────────────

async def stream_agent_response(
    user_message: str,
    session_id: str,
    user_id: str = "default_user",
) -> AsyncIterator[str]:
    """Stream agent response chunks as Server-Sent Events data strings.

    Each yielded value is a JSON string containing one of:
      {"type": "text_chunk",  "content": "..."}
      {"type": "tool_call",   "name": "...", "args": {...}}
      {"type": "tool_result", "name": "...", "result": {...}}
      {"type": "chart",       "chart_type": "...", "spec": {...}}
      {"type": "done"}
      {"type": "error",       "message": "..."}
    """
    runner = get_runner()
    await ensure_session(user_id, session_id)

    user_content = genai_types.Content(
        role="user",
        parts=[genai_types.Part.from_text(user_message)],
    )

    try:
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=user_content,
        ):
            # Tool call events
            if event.content and event.content.parts:
                for part in event.content.parts:
                    # Function calls (tool invocations)
                    if hasattr(part, "function_call") and part.function_call:
                        fc = part.function_call
                        yield json.dumps({
                            "type": "tool_call",
                            "name": fc.name,
                            "args": dict(fc.args) if fc.args else {},
                        })

                    # Function responses (tool results)
                    elif hasattr(part, "function_response") and part.function_response:
                        fr = part.function_response
                        result = dict(fr.response) if fr.response else {}

                        # Check if this is a chart response
                        if "spec" in result and "chart_type" in result:
                            yield json.dumps({
                                "type": "chart",
                                "chart_type": result.get("chart_type"),
                                "ticker": result.get("ticker", ""),
                                "spec": result.get("spec", {}),
                            })
                        else:
                            yield json.dumps({
                                "type": "tool_result",
                                "name": fr.name,
                                "result": result,
                            })

                    # Text chunks
                    elif hasattr(part, "text") and part.text:
                        yield json.dumps({"type": "text_chunk", "content": part.text})

        yield json.dumps({"type": "done"})

    except Exception as exc:
        logger.exception("Agent error: %s", exc)
        yield json.dumps({"type": "error", "message": str(exc)})
        yield json.dumps({"type": "done"})


async def get_agent_response(
    user_message: str,
    session_id: str,
    user_id: str = "default_user",
) -> dict:
    """Non-streaming version: collect the full agent response and return it."""
    text_parts = []
    charts = []
    tool_calls = []

    async for raw in stream_agent_response(user_message, session_id, user_id):
        event = json.loads(raw)
        if event["type"] == "text_chunk":
            text_parts.append(event["content"])
        elif event["type"] == "chart":
            charts.append(event)
        elif event["type"] == "tool_call":
            tool_calls.append(event)
        elif event["type"] == "error":
            return {"error": event["message"]}

    return {
        "text": "".join(text_parts),
        "charts": charts,
        "tool_calls": tool_calls,
        "session_id": session_id,
    }
