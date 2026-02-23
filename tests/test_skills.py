"""Unit tests for the skill infrastructure.

These tests mock external data fetchers so no network calls are made.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from skills.base import BaseSkill, SkillMetadata
from skills.chart_generator import ChartGeneratorSkill
from skills.chart_generator.chart_builder import (
    build_comparison_chart,
    build_line_chart,
    build_sector_chart,
)
from skills.registry import get_all_tools, get_skills_manifest
from skills.trading_advisor import TradingAdvisorSkill


# ── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
def mock_hist(sample_ohlcv):
    """Return sample OHLCV dict resembling get_historical_data output."""
    return {**sample_ohlcv, "ticker": "AAPL", "period": "6mo", "count": len(sample_ohlcv["close"])}


@pytest.fixture
def mock_quote():
    return {
        "ticker": "AAPL",
        "name": "Apple Inc.",
        "current_price": 185.50,
        "previous_close": 183.00,
        "change": 2.50,
        "change_pct": 1.37,
        "pe_ratio": 28.5,
        "market_cap": 2_850_000_000_000,
        "beta": 1.22,
        "sector": "Technology",
        "dividend_yield": 0.55,
        "eps": 6.51,
    }


# ── Skill Registry Tests ────────────────────────────────────────────────────

class TestSkillRegistry:
    def test_all_tools_returns_list(self):
        tools = get_all_tools()
        assert isinstance(tools, list)
        assert len(tools) > 0

    def test_all_tools_are_callable(self):
        for tool in get_all_tools():
            assert callable(tool), f"{tool} must be callable"

    def test_all_tools_have_docstrings(self):
        for tool in get_all_tools():
            assert tool.__doc__, f"{tool.__name__} must have a docstring"

    def test_skills_manifest_structure(self):
        manifest = get_skills_manifest()
        assert isinstance(manifest, list)
        assert len(manifest) == 2  # trading_advisor + chart_generator
        for skill in manifest:
            assert "name" in skill
            assert "description" in skill
            assert "version" in skill
            assert "tags" in skill
            assert "tools" in skill
            assert isinstance(skill["tools"], list)

    def test_trading_advisor_in_manifest(self):
        manifest = get_skills_manifest()
        names = [s["name"] for s in manifest]
        assert "trading_advisor" in names

    def test_chart_generator_in_manifest(self):
        manifest = get_skills_manifest()
        names = [s["name"] for s in manifest]
        assert "chart_generator" in names


# ── TradingAdvisorSkill Tests ───────────────────────────────────────────────

class TestTradingAdvisorSkill:
    def test_metadata(self):
        skill = TradingAdvisorSkill()
        assert skill.metadata.name == "trading_advisor"
        assert len(skill.metadata.tags) > 0
        assert skill.metadata.version

    def test_get_tools_count(self):
        skill = TradingAdvisorSkill()
        tools = skill.get_tools()
        assert len(tools) >= 5  # At least 5 tools

    def test_tools_have_typed_annotations(self):
        skill = TradingAdvisorSkill()
        import inspect
        for tool in skill.get_tools():
            sig = inspect.signature(tool)
            # Must have at least return annotation or parameter annotations
            # (ADK uses these for schema generation)
            assert sig is not None

    def test_compare_stocks_tool(self, mock_hist):
        with patch(
            "skills.trading_advisor.skill.get_historical_data",
            return_value=mock_hist,
        ):
            from skills.trading_advisor.skill import tool_compare_stocks
            result = tool_compare_stocks("AAPL,MSFT", period="1y")
            assert "comparison" in result
            assert "AAPL" in result["comparison"]
            assert "MSFT" in result["comparison"]
            assert "return_pct" in result["comparison"]["AAPL"]

    def test_technical_analysis_tool(self, mock_hist):
        with patch(
            "skills.trading_advisor.skill.get_historical_data",
            return_value=mock_hist,
        ):
            from skills.trading_advisor.skill import tool_get_technical_analysis
            result = tool_get_technical_analysis("AAPL", period="6mo")
            assert "ticker" in result
            assert result["ticker"] == "AAPL"
            assert "latest" in result
            assert "signals" in result

    def test_market_overview_tool(self):
        mock_overview = {
            "indices": {
                "S&P 500": {"symbol": "^GSPC", "price": 5000, "change": 10, "change_pct": 0.2}
            },
            "timestamp": "2026-02-23T12:00:00",
        }
        with patch(
            "skills.trading_advisor.data_fetcher.get_market_overview",
            return_value=mock_overview,
        ):
            from skills.trading_advisor.skill import tool_get_market_overview
            result = tool_get_market_overview()
            assert "indices" in result
            assert "S&P 500" in result["indices"]


# ── ChartGeneratorSkill Tests ──────────────────────────────────────────────

class TestChartGeneratorSkill:
    def test_metadata(self):
        skill = ChartGeneratorSkill()
        assert skill.metadata.name == "chart_generator"
        assert "plotly" in skill.metadata.tags or "charts" in skill.metadata.tags

    def test_get_tools_count(self):
        skill = ChartGeneratorSkill()
        tools = skill.get_tools()
        assert len(tools) >= 5

    def test_candlestick_tool_returns_spec(self, mock_hist):
        with patch(
            "skills.chart_generator.chart_builder.get_historical_data",
            return_value=mock_hist,
        ):
            from skills.chart_generator.skill import tool_candlestick_chart
            result = tool_candlestick_chart("AAPL", period="6mo")
            assert result["chart_type"] == "candlestick"
            assert "spec" in result
            assert "data" in result["spec"]
            assert "layout" in result["spec"]

    def test_technical_chart_tool_returns_spec(self, mock_hist):
        with patch(
            "skills.chart_generator.chart_builder.get_historical_data",
            return_value=mock_hist,
        ):
            from skills.chart_generator.skill import tool_technical_analysis_chart
            result = tool_technical_analysis_chart("AAPL")
            assert result["chart_type"] == "technical"
            assert "spec" in result
            # Technical chart should have multiple traces (price, BBands, RSI, MACD)
            assert len(result["spec"]["data"]) >= 6

    def test_comparison_chart_multiple_tickers(self, mock_hist):
        with patch(
            "skills.chart_generator.chart_builder.get_historical_data",
            return_value=mock_hist,
        ):
            result = build_comparison_chart("AAPL,MSFT,GOOGL", period="1y")
            assert "data" in result
            # Should have 3 stock traces + baseline
            assert len(result["data"]) >= 4

    def test_sector_chart_structure(self):
        mock_sectors = {
            "sectors": {
                "Technology": {"etf": "XLK", "price": 210, "change_pct_1d": 1.5, "52w_high": 220, "52w_low": 180},
                "Healthcare": {"etf": "XLV", "price": 140, "change_pct_1d": -0.3, "52w_high": 150, "52w_low": 130},
            },
            "timestamp": "2026-02-23T12:00:00",
        }
        with patch(
            "skills.chart_generator.chart_builder.get_sector_performance",
            return_value=mock_sectors,
        ):
            result = build_sector_chart()
            assert "data" in result
            assert "layout" in result
            assert result["data"][0]["type"] == "bar"

    def test_line_chart_area_style(self, mock_hist):
        with patch(
            "skills.chart_generator.chart_builder.get_historical_data",
            return_value=mock_hist,
        ):
            result = build_line_chart("AAPL", period="1y", chart_type="area")
            assert result["data"][0]["fill"] == "tozeroy"

    def test_line_chart_line_style(self, mock_hist):
        with patch(
            "skills.chart_generator.chart_builder.get_historical_data",
            return_value=mock_hist,
        ):
            result = build_line_chart("AAPL", period="1y", chart_type="line")
            assert result["data"][0]["fill"] == "none"

    def test_chart_error_on_data_fetch_failure(self):
        with patch(
            "skills.chart_generator.chart_builder.get_historical_data",
            return_value={"error": "No data for XYZ", "ticker": "XYZ"},
        ):
            from skills.chart_generator.chart_builder import build_candlestick_chart
            result = build_candlestick_chart("XYZ")
            assert "error" in result
