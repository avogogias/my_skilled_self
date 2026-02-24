"""Trading Advisor skill — ADK-compatible tool functions.

Skill pattern (HuggingFace-inspired):
  - SKILL_METADATA : describes the skill
  - get_tools()    : returns list of Python functions the ADK agent exposes
"""

import math

from skills.base import BaseSkill, SkillMetadata
from skills.trading_advisor.data_fetcher import (
    get_financials,
    get_historical_data,
    get_market_overview,
    get_sector_performance,
    get_stock_news,
    get_stock_quote,
)
from skills.trading_advisor.technical_analysis import compute_indicators


# ──────────────────────────────────────────────────────────────────────────────
# ADK Tool Functions — plain Python callables with typed signatures & docstrings
# ──────────────────────────────────────────────────────────────────────────────

def tool_get_stock_quote(ticker: str) -> dict:
    """Get the real-time price and key metrics for a stock, ETF, or index.

    Args:
        ticker: Ticker symbol, e.g. AAPL, TSLA, SPY, QQQ, BTC-USD.

    Returns:
        Current price, daily change, volume, P/E, dividend yield, sector, etc.
    """
    return get_stock_quote(ticker)


def tool_get_technical_analysis(ticker: str, period: str = "6mo") -> dict:
    """Perform full technical analysis on a stock: RSI, MACD, Bollinger Bands, MAs.

    Args:
        ticker: Ticker symbol.
        period: Historical data period — 1mo, 3mo, 6mo, 1y, 2y (default: 6mo).

    Returns:
        Technical indicators, signal interpretations, and trend summary.
    """
    hist = get_historical_data(ticker, period=period, interval="1d")
    if "error" in hist:
        return hist

    indicators = compute_indicators(
        dates=hist["dates"],
        close=hist["close"],
        high=hist["high"],
        low=hist["low"],
        volume=hist["volume"],
    )

    return {
        "ticker": ticker.upper(),
        "period": period,
        "latest": indicators["latest"],
        "signals": indicators["signals"],
        "data_points": indicators["data_points"],
    }


def tool_get_fundamental_analysis(ticker: str) -> dict:
    """Get fundamental financial metrics: revenue, earnings, margins, ratios.

    Args:
        ticker: Ticker symbol.

    Returns:
        Income statement metrics, balance sheet ratios, growth rates, etc.
    """
    quote = get_stock_quote(ticker)
    financials = get_financials(ticker)
    if "error" in financials:
        return financials

    # Combine for richer context
    return {
        "ticker": ticker.upper(),
        "name": quote.get("name", ticker),
        "price": quote.get("current_price"),
        "market_cap": quote.get("market_cap"),
        "pe_ratio": quote.get("pe_ratio"),
        "forward_pe": quote.get("forward_pe"),
        "eps": quote.get("eps"),
        "dividend_yield": quote.get("dividend_yield"),
        "beta": quote.get("beta"),
        "sector": quote.get("sector"),
        **financials,
    }


def tool_get_market_overview() -> dict:
    """Get a live snapshot of major market indices, volatility, and commodities.

    Returns:
        Current price and daily change for S&P 500, Nasdaq, Dow, VIX, Gold,
        Crude Oil, Bitcoin, and 10-year Treasury yield.
    """
    return get_market_overview()


def tool_get_sector_performance() -> dict:
    """Get today's performance across all 11 GICS S&P 500 sectors.

    Returns:
        Price and percentage change for Technology, Healthcare, Financials,
        Energy, Utilities, and all other SPDR sector ETFs.
    """
    return get_sector_performance()


def tool_get_stock_news(ticker: str, limit: int = 5) -> dict:
    """Retrieve recent news headlines and summaries for a stock.

    Args:
        ticker: Ticker symbol.
        limit: Number of articles to return (1–10, default 5).

    Returns:
        List of recent news items with title, publisher, link, and summary.
    """
    return get_stock_news(ticker, limit=limit)


def tool_compare_stocks(tickers: str, period: str = "1y") -> dict:
    """Compare performance of multiple stocks over a given period.

    Args:
        tickers: Comma-separated ticker symbols, e.g. "AAPL,MSFT,GOOGL".
        period: Comparison period: 1mo, 3mo, 6mo, 1y, 2y (default: 1y).

    Returns:
        Price performance, returns, volatility comparison for each ticker.
    """
    ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()][:5]
    if not ticker_list:
        return {"error": "No valid tickers provided.", "tickers": [], "comparison": {}}
    results = {}

    for ticker in ticker_list:
        hist = get_historical_data(ticker, period=period, interval="1d")
        if "error" in hist or not hist.get("close"):
            results[ticker] = {"error": "No data"}
            continue

        closes = hist["close"]
        start_price = closes[0]
        end_price = closes[-1]
        returns_pct = ((end_price - start_price) / start_price * 100) if start_price else 0

        # Volatility (annualised std dev of daily returns)
        daily_rets = [
            (closes[i] - closes[i - 1]) / closes[i - 1]
            for i in range(1, len(closes))
            if closes[i - 1] != 0
        ]
        avg_ret = sum(daily_rets) / len(daily_rets) if daily_rets else 0
        variance = sum((r - avg_ret) ** 2 for r in daily_rets) / len(daily_rets) if daily_rets else 0
        annualised_vol = math.sqrt(variance * 252) * 100

        results[ticker] = {
            "start_price": round(start_price, 2),
            "end_price": round(end_price, 2),
            "return_pct": round(returns_pct, 2),
            "annualised_volatility_pct": round(annualised_vol, 2),
            "data_points": len(closes),
        }

    return {"tickers": ticker_list, "period": period, "comparison": results}


# ──────────────────────────────────────────────────────────────────────────────
# Skill Class
# ──────────────────────────────────────────────────────────────────────────────

class TradingAdvisorSkill(BaseSkill):
    metadata = SkillMetadata(
        name="trading_advisor",
        description=(
            "Expert trading and investing advisor using live Yahoo Finance data "
            "(same data source as Investopedia). Provides real-time quotes, "
            "technical analysis, fundamental analysis, market overviews, and news."
        ),
        version="1.0.0",
        tags=["trading", "investing", "finance", "stocks", "technical-analysis"],
        icon="📈",
    )

    def get_tools(self):
        return [
            tool_get_stock_quote,
            tool_get_technical_analysis,
            tool_get_fundamental_analysis,
            tool_get_market_overview,
            tool_get_sector_performance,
            tool_get_stock_news,
            tool_compare_stocks,
        ]
