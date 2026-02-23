# My Skilled Self — AI Trading & Investing Agent

A production-ready AI agent system powered by **Google ADK** (Gemini 2.0) with pluggable
skills, a streaming **FastAPI** backend, and a **React TypeScript** frontend with interactive charts.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  React + TypeScript Frontend (port 3000)                │
│  • Streaming chat UI  • Plotly.js interactive charts    │
│  • Live market ticker • CopilotKit-ready API contract   │
└────────────────────┬────────────────────────────────────┘
                     │  SSE streaming / REST
┌────────────────────▼────────────────────────────────────┐
│  FastAPI Agent Backend (port 8000)                      │
│  • Google ADK + Gemini 2.0 Flash                        │
│  • Skill registry (HuggingFace-inspired pattern)        │
└────────────────────┬────────────────────────────────────┘
                     │  Tool calls
         ┌───────────┴──────────────┐
         ▼                          ▼
┌────────────────┐       ┌─────────────────────┐
│ Trading Advisor│       │  Chart Generator    │
│ Skill  📈      │       │  Skill  📊          │
│                │       │                     │
│ • Live quotes  │       │ • Candlestick charts│
│ • Tech analysis│       │ • Technical panels  │
│ • Fundamentals │       │ • Comparisons       │
│ • Market views │       │ • Sector heatmaps   │
│ • News         │       │ • Volume profiles   │
│ • Stock compare│       │ • Plotly JSON specs │
└───────┬────────┘       └─────────────────────┘
        │
        ▼
   Yahoo Finance
   (same data as Investopedia)
```

## Skills

### 📈 Trading Advisor
Expert trading and investing analysis powered by live Yahoo Finance data — the same
data source that Investopedia.com uses. Embedded domain knowledge from Investopedia covers:
- Fundamental analysis (P/E, EPS, ROE, FCF, Debt/Equity)
- Technical indicators (RSI, MACD, Bollinger Bands, SMA/EMA)
- Risk management (1% rule, position sizing, stop-losses)
- Market structure (bull/bear/correction, VIX, yield curve)
- Investment strategies, options basics, behavioral finance

**Tools:** `get_stock_quote`, `get_technical_analysis`, `get_fundamental_analysis`,
`get_market_overview`, `get_sector_performance`, `get_stock_news`, `compare_stocks`

### 📊 Chart Generator
Interactive Plotly.js chart specifications generated on-demand. The backend returns
JSON specs; the frontend renders them client-side for full interactivity.

**Tools:** `candlestick_chart`, `technical_analysis_chart`, `price_line_chart`,
`comparison_chart`, `sector_performance_chart`, `volume_profile_chart`

## Quick Start

### Prerequisites
- Docker & Docker Compose
- A Google AI Studio API key — get one free at https://aistudio.google.com/app/apikey

### 1. Configure
```bash
cp .env.example .env
# Edit .env and set your GOOGLE_API_KEY
```

### 2. Start
```bash
docker compose up --build
```

- Frontend: http://localhost:3000
- Agent API: http://localhost:8000
- API docs: http://localhost:8000/docs

### 3. Run Tests
```bash
# Python backend tests (52 tests)
PYTHONPATH=agent python -m pytest tests/ -v

# Frontend TypeScript tests (9 tests)
cd frontend && npm test
```

## Adding a New Skill

1. Create `agent/skills/your_skill/` with `skill.py`, `__init__.py`
2. Implement `YourSkill(BaseSkill)` with `metadata` and `get_tools()`
3. Add it to `agent/skills/registry.py` — the agent picks it up automatically

```python
# agent/skills/my_new_skill/skill.py
from skills.base import BaseSkill, SkillMetadata

def tool_my_function(param: str) -> dict:
    """Tool description used by the LLM."""
    return {"result": ...}

class MyNewSkill(BaseSkill):
    metadata = SkillMetadata(name="my_new_skill", description="...", tags=["..."])
    def get_tools(self): return [tool_my_function]
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness probe |
| GET | `/skills` | List all registered skills |
| POST | `/chat` | Single-turn chat (non-streaming) |
| POST | `/chat/stream` | Streaming chat (SSE) |
| GET | `/market/overview` | Live market indices snapshot |
| GET | `/market/sectors` | S&P 500 sector performance |

## SSE Event Types

The streaming endpoint yields newline-delimited JSON events:

```json
{"type": "text_chunk",  "content": "AAPL is trading at..."}
{"type": "tool_call",   "name": "tool_get_stock_quote", "args": {"ticker": "AAPL"}}
{"type": "tool_result", "name": "tool_get_stock_quote", "result": {...}}
{"type": "chart",       "chart_type": "candlestick", "ticker": "AAPL", "spec": {...}}
{"type": "done"}
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| AI Agent | Google ADK + Gemini 2.0 Flash |
| Backend | FastAPI + uvicorn + SSE streaming |
| Financial Data | yfinance (Yahoo Finance / Investopedia data) |
| Frontend | React 18 + TypeScript + Vite |
| Charts | Plotly.js (react-plotly.js) |
| Markdown | react-markdown + remark-gfm |
| Containers | Docker + Docker Compose |
| Backend Tests | pytest + pytest-asyncio (52 tests) |
| Frontend Tests | Vitest + Testing Library (9 tests) |
