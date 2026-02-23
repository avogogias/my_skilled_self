"""Chart Generator skill — produces interactive Plotly.js chart specifications.

The agent calls these tools to generate charts. Each tool returns a JSON dict
that is a valid Plotly.js figure specification. The React frontend renders it
using react-plotly.js — no charting code runs in the backend.

Skill pattern (HuggingFace-inspired):
  - SKILL_METADATA : describes the skill
  - get_tools()    : returns list of Python functions for the ADK agent
"""

import json
from skills.base import BaseSkill, SkillMetadata
from skills.chart_generator.chart_builder import (
    build_candlestick_chart,
    build_comparison_chart,
    build_line_chart,
    build_sector_chart,
    build_technical_chart,
    build_volume_profile_chart,
)


# ──────────────────────────────────────────────────────────────────────────────
# ADK Tool Functions
# ──────────────────────────────────────────────────────────────────────────────

def tool_candlestick_chart(ticker: str, period: str = "6mo") -> dict:
    """Generate an interactive candlestick OHLCV chart with volume subplot.

    Best for: visualising price action, identifying patterns (doji, hammer, etc.),
    and understanding intraday / day-to-day price movements.

    Args:
        ticker: Stock ticker symbol (e.g. AAPL, TSLA, SPY).
        period: Data period — 1mo, 3mo, 6mo, 1y, 2y (default: 6mo).

    Returns:
        Plotly figure spec (data + layout + config) for the frontend to render.
    """
    spec = build_candlestick_chart(ticker, period=period)
    return {"chart_type": "candlestick", "ticker": ticker.upper(), "spec": spec}


def tool_technical_analysis_chart(ticker: str, period: str = "6mo") -> dict:
    """Generate a multi-panel technical analysis chart.

    Includes: Price + Bollinger Bands + SMA 20/50 (top panel),
    RSI 14 with overbought/oversold levels (middle panel),
    MACD line + signal + histogram (bottom panel).

    Args:
        ticker: Stock ticker symbol.
        period: Data period — 1mo, 3mo, 6mo, 1y, 2y (default: 6mo).

    Returns:
        Plotly figure spec for the frontend to render.
    """
    spec = build_technical_chart(ticker, period=period)
    return {"chart_type": "technical", "ticker": ticker.upper(), "spec": spec}


def tool_price_line_chart(ticker: str, period: str = "1y", style: str = "area") -> dict:
    """Generate a clean price line or area chart.

    Best for: long-term trend visualisation and portfolio performance views.

    Args:
        ticker: Stock ticker symbol.
        period: Data period — 1mo, 3mo, 6mo, 1y, 2y, 5y (default: 1y).
        style: Chart style — 'line' or 'area' (default: area).

    Returns:
        Plotly figure spec for the frontend to render.
    """
    spec = build_line_chart(ticker, period=period, chart_type=style)
    return {"chart_type": "line", "ticker": ticker.upper(), "spec": spec}


def tool_comparison_chart(tickers: str, period: str = "1y") -> dict:
    """Generate a normalised performance comparison chart for multiple stocks.

    Shows % return from the start of the period, allowing apples-to-apples
    comparison regardless of absolute price differences.

    Args:
        tickers: Comma-separated ticker symbols — e.g. "AAPL,MSFT,GOOGL,AMZN".
                 Maximum 5 tickers.
        period: Comparison period — 1mo, 3mo, 6mo, 1y, 2y (default: 1y).

    Returns:
        Plotly figure spec for the frontend to render.
    """
    spec = build_comparison_chart(tickers, period=period)
    ticker_list = [t.strip().upper() for t in tickers.split(",")][:5]
    return {"chart_type": "comparison", "tickers": ticker_list, "spec": spec}


def tool_sector_performance_chart() -> dict:
    """Generate a horizontal bar chart of today's S&P 500 sector performance.

    Shows daily % change for all 11 GICS sectors via SPDR ETFs.
    Green bars = sectors outperforming, red bars = underperforming.

    Returns:
        Plotly figure spec for the frontend to render.
    """
    spec = build_sector_chart()
    return {"chart_type": "sector", "spec": spec}


def tool_volume_profile_chart(ticker: str, period: str = "3mo") -> dict:
    """Generate a volume profile chart showing trading activity by price level.

    Helps identify key support/resistance levels based on where most volume
    has traded historically.

    Args:
        ticker: Stock ticker symbol.
        period: Data period — 1mo, 3mo, 6mo (default: 3mo).

    Returns:
        Plotly figure spec for the frontend to render.
    """
    spec = build_volume_profile_chart(ticker, period=period)
    return {"chart_type": "volume_profile", "ticker": ticker.upper(), "spec": spec}


# ──────────────────────────────────────────────────────────────────────────────
# Skill Class
# ──────────────────────────────────────────────────────────────────────────────

class ChartGeneratorSkill(BaseSkill):
    metadata = SkillMetadata(
        name="chart_generator",
        description=(
            "Generates interactive, publication-quality financial charts using "
            "Plotly.js. Creates candlestick charts, technical analysis panels, "
            "line/area charts, multi-stock comparisons, sector heat maps, and "
            "volume profiles — all rendered client-side for maximum interactivity."
        ),
        version="1.0.0",
        tags=["charts", "visualisation", "plotly", "technical-analysis", "finance"],
        icon="📊",
    )

    def get_tools(self):
        return [
            tool_candlestick_chart,
            tool_technical_analysis_chart,
            tool_price_line_chart,
            tool_comparison_chart,
            tool_sector_performance_chart,
            tool_volume_profile_chart,
        ]
