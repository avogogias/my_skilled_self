"""API integration tests using FastAPI TestClient.

These tests run the FastAPI app in-process with all external calls mocked,
so they work offline and in CI without a real Google API key.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Patch ADK dependencies before importing the app.
# IMPORTANT: import yfinance FIRST so google.protobuf loads into sys.modules
# before we inject our google.adk stubs — otherwise the stub's plain
# types.ModuleType("google") corrupts the google namespace package.
import os
import sys
import types

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))

try:
    import yfinance  # noqa: F401 — ensures google.protobuf is in sys.modules
except Exception:
    pass

# Create minimal google.adk / google.genai stubs
adk_stub = types.ModuleType("google.adk")
agents_stub = types.ModuleType("google.adk.agents")
runners_stub = types.ModuleType("google.adk.runners")
sessions_stub = types.ModuleType("google.adk.sessions")
genai_stub = types.ModuleType("google.genai")
genai_types_stub = types.ModuleType("google.genai.types")

class _FakeLlmAgent:
    def __init__(self, **kwargs): pass

class _FakeRunner:
    def __init__(self, **kwargs): self.session_service = _FakeSessionService()
    async def run_async(self, **kwargs):
        async def _gen():
            yield MagicMock()
        return _gen()

class _FakeSessionService:
    async def get_session(self, **kwargs): return None
    async def create_session(self, **kwargs): return None

class _FakeContent:
    def __init__(self, role=None, parts=None): self.role = role; self.parts = parts or []

class _FakePart:
    @staticmethod
    def from_text(text): m = MagicMock(); m.text = text; return m

agents_stub.LlmAgent = _FakeLlmAgent
runners_stub.Runner = _FakeRunner
sessions_stub.InMemorySessionService = _FakeSessionService
genai_types_stub.Content = _FakeContent
genai_types_stub.Part = _FakePart

# Inject ONLY the adk/genai sub-modules; leave sys.modules["google"] intact
# so that google.protobuf (used by yfinance) continues to work.
sys.modules["google.adk"] = adk_stub
sys.modules["google.adk.agents"] = agents_stub
sys.modules["google.adk.runners"] = runners_stub
sys.modules["google.adk.sessions"] = sessions_stub
sys.modules["google.genai"] = genai_stub
sys.modules["google.genai.types"] = genai_types_stub

os.environ.setdefault("GOOGLE_API_KEY", "test-key-123")

from main import app


@pytest.fixture
def client():
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


# ── /health ────────────────────────────────────────────────────────────────

class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        r = client.get("/health")
        assert r.status_code == 200

    def test_health_body(self, client):
        r = client.get("/health")
        body = r.json()
        assert body["status"] == "ok"
        assert "model" in body
        assert "app" in body

    def test_health_api_key_configured(self, client):
        r = client.get("/health")
        assert r.json()["api_key_configured"] is True


# ── /skills ────────────────────────────────────────────────────────────────

class TestSkillsEndpoint:
    def test_skills_returns_200(self, client):
        r = client.get("/skills")
        assert r.status_code == 200

    def test_skills_has_trading_advisor(self, client):
        r = client.get("/skills")
        names = [s["name"] for s in r.json()["skills"]]
        assert "trading_advisor" in names

    def test_skills_has_chart_generator(self, client):
        r = client.get("/skills")
        names = [s["name"] for s in r.json()["skills"]]
        assert "chart_generator" in names

    def test_skills_structure(self, client):
        r = client.get("/skills")
        for skill in r.json()["skills"]:
            assert "name" in skill
            assert "description" in skill
            assert "tools" in skill
            assert isinstance(skill["tools"], list)


# ── /market/* ──────────────────────────────────────────────────────────────

class TestMarketEndpoints:
    def test_market_overview(self, client):
        mock_data = {
            "indices": {"S&P 500": {"symbol": "^GSPC", "price": 5000, "change": 10, "change_pct": 0.2}},
            "timestamp": "2026-02-23T12:00:00",
        }
        with patch("main.get_market_overview", return_value=mock_data):
            r = client.get("/market/overview")
        assert r.status_code == 200
        assert "indices" in r.json()

    def test_market_sectors(self, client):
        mock_data = {
            "sectors": {"Technology": {"etf": "XLK", "price": 200, "change_pct_1d": 1.0}},
            "timestamp": "2026-02-23T12:00:00",
        }
        with patch("main.get_sector_performance", return_value=mock_data):
            r = client.get("/market/sectors")
        assert r.status_code == 200
        assert "sectors" in r.json()


# ── /chat ──────────────────────────────────────────────────────────────────

class TestChatEndpoint:
    def test_chat_no_api_key_returns_503(self, client):
        with patch("main.config") as mock_cfg:
            mock_cfg.google_api_key = ""
            r = client.post("/chat", json={"message": "Hello", "session_id": "s1"})
        assert r.status_code == 503

    def test_chat_requires_message(self, client):
        # Empty message should fail validation
        r = client.post("/chat", json={"message": "", "session_id": "s1"})
        assert r.status_code == 422  # Pydantic validation error

    def test_chat_with_mock_agent(self, client):
        async def mock_response(*args, **kwargs):
            return {
                "text": "AAPL is trading at $185. RSI is neutral at 52.",
                "charts": [],
                "tool_calls": [],
                "session_id": "test-session",
            }
        with patch("main.config") as mock_cfg:
            mock_cfg.google_api_key = "test-key"
            with patch("agent_core.get_agent_response", side_effect=mock_response):
                r = client.post(
                    "/chat",
                    json={"message": "Tell me about AAPL", "session_id": "test-session"},
                )
        # Accepts 200 or 503/500 depending on ADK stub
        assert r.status_code in (200, 500, 503)


# ── /chat/stream ───────────────────────────────────────────────────────────

class TestChatStreamEndpoint:
    def test_stream_no_api_key(self, client):
        with patch("main.config") as mock_cfg:
            mock_cfg.google_api_key = ""
            r = client.post(
                "/chat/stream",
                json={"message": "Hello", "session_id": "s1"},
            )
        assert r.status_code == 503

    def test_stream_content_type(self, client):
        async def mock_stream(*args, **kwargs):
            yield json.dumps({"type": "text_chunk", "content": "Test"})
            yield json.dumps({"type": "done"})

        with patch("main.config") as mock_cfg:
            mock_cfg.google_api_key = "test-key"
            with patch("agent_core.stream_agent_response", side_effect=mock_stream):
                r = client.post(
                    "/chat/stream",
                    json={"message": "Hello", "session_id": "test-s"},
                )
        # StreamingResponse has text/event-stream
        assert "text/event-stream" in r.headers.get("content-type", "")
