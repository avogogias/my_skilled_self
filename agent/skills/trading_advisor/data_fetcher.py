"""Live financial data fetcher using Yahoo Finance (yfinance).

Yahoo Finance is the same data source that Investopedia's stock pages use,
making this functionally equivalent to the 'Investopedia trading API'.
"""

import json
from datetime import datetime, timezone
from typing import Any

import pandas as pd
import yfinance as yf


def _safe_float(val: Any, default: float = 0.0) -> float:
    """Convert a value to float safely."""
    try:
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return default
        return float(val)
    except (TypeError, ValueError):
        return default


def get_stock_quote(ticker: str) -> dict:
    """Get real-time stock quote and key metrics.

    Args:
        ticker: Stock ticker symbol (e.g. AAPL, MSFT, GOOGL, SPY).

    Returns:
        Dictionary with current price, change, volume, market cap, and key ratios.
    """
    try:
        stock = yf.Ticker(ticker.upper())
        info = stock.info

        # Current price — fast_info is more reliable for live quotes
        fast = stock.fast_info
        current_price = _safe_float(getattr(fast, "last_price", None) or info.get("currentPrice"))
        prev_close = _safe_float(getattr(fast, "previous_close", None) or info.get("previousClose"))
        change = current_price - prev_close if current_price and prev_close else 0
        change_pct = (change / prev_close * 100) if prev_close else 0

        return {
            "ticker": ticker.upper(),
            "name": info.get("longName", ticker),
            "current_price": round(current_price, 2),
            "previous_close": round(prev_close, 2),
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "open": round(_safe_float(info.get("open")), 2),
            "day_high": round(_safe_float(info.get("dayHigh")), 2),
            "day_low": round(_safe_float(info.get("dayLow")), 2),
            "52w_high": round(_safe_float(info.get("fiftyTwoWeekHigh")), 2),
            "52w_low": round(_safe_float(info.get("fiftyTwoWeekLow")), 2),
            "volume": int(info.get("volume", 0)),
            "avg_volume": int(info.get("averageVolume", 0)),
            "market_cap": int(info.get("marketCap", 0)),
            "pe_ratio": round(_safe_float(info.get("trailingPE")), 2),
            "forward_pe": round(_safe_float(info.get("forwardPE")), 2),
            "eps": round(_safe_float(info.get("trailingEps")), 2),
            "dividend_yield": round(_safe_float(info.get("dividendYield")) * 100, 2),
            "beta": round(_safe_float(info.get("beta")), 2),
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
            "exchange": info.get("exchange", "N/A"),
            "currency": info.get("currency", "USD"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        return {"error": str(exc), "ticker": ticker.upper()}


def get_historical_data(ticker: str, period: str = "6mo", interval: str = "1d") -> dict:
    """Fetch OHLCV historical data for charting and analysis.

    Args:
        ticker: Stock ticker symbol.
        period: Data period: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max.
        interval: Bar interval: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo.

    Returns:
        Dictionary with dates, open, high, low, close, volume arrays.
    """
    try:
        stock = yf.Ticker(ticker.upper())
        hist = stock.history(period=period, interval=interval)

        if hist.empty:
            return {"error": f"No data found for {ticker}", "ticker": ticker.upper()}

        # Reset index to get date as column
        hist = hist.reset_index()
        date_col = "Datetime" if "Datetime" in hist.columns else "Date"

        return {
            "ticker": ticker.upper(),
            "period": period,
            "interval": interval,
            "dates": hist[date_col].dt.strftime("%Y-%m-%d %H:%M").tolist(),
            "open": [round(float(v), 2) for v in hist["Open"]],
            "high": [round(float(v), 2) for v in hist["High"]],
            "low": [round(float(v), 2) for v in hist["Low"]],
            "close": [round(float(v), 2) for v in hist["Close"]],
            "volume": [int(v) for v in hist["Volume"]],
            "count": len(hist),
        }
    except Exception as exc:
        return {"error": str(exc), "ticker": ticker.upper()}


def get_financials(ticker: str) -> dict:
    """Get key financial statements: income, balance sheet, cash flow.

    Args:
        ticker: Stock ticker symbol.

    Returns:
        Key financial metrics from the latest annual filing.
    """
    try:
        stock = yf.Ticker(ticker.upper())
        info = stock.info

        return {
            "ticker": ticker.upper(),
            "revenue": int(info.get("totalRevenue", 0)),
            "gross_profit": int(info.get("grossProfits", 0)),
            "operating_income": int(info.get("operatingIncome", 0) or 0),
            "net_income": int(info.get("netIncomeToCommon", 0) or 0),
            "ebitda": int(info.get("ebitda", 0) or 0),
            "total_cash": int(info.get("totalCash", 0) or 0),
            "total_debt": int(info.get("totalDebt", 0) or 0),
            "free_cash_flow": int(info.get("freeCashflow", 0) or 0),
            "operating_cash_flow": int(info.get("operatingCashflow", 0) or 0),
            "profit_margin": round(_safe_float(info.get("profitMargins")) * 100, 2),
            "operating_margin": round(_safe_float(info.get("operatingMargins")) * 100, 2),
            "return_on_equity": round(_safe_float(info.get("returnOnEquity")) * 100, 2),
            "return_on_assets": round(_safe_float(info.get("returnOnAssets")) * 100, 2),
            "revenue_growth": round(_safe_float(info.get("revenueGrowth")) * 100, 2),
            "earnings_growth": round(_safe_float(info.get("earningsGrowth")) * 100, 2),
            "debt_to_equity": round(_safe_float(info.get("debtToEquity")), 2),
            "current_ratio": round(_safe_float(info.get("currentRatio")), 2),
            "quick_ratio": round(_safe_float(info.get("quickRatio")), 2),
            "shares_outstanding": int(info.get("sharesOutstanding", 0) or 0),
            "book_value": round(_safe_float(info.get("bookValue")), 2),
            "price_to_book": round(_safe_float(info.get("priceToBook")), 2),
        }
    except Exception as exc:
        return {"error": str(exc), "ticker": ticker.upper()}


def get_market_overview() -> dict:
    """Get a snapshot of major market indices and key economic indicators.

    Returns:
        Current prices and changes for major indices (S&P500, Nasdaq, Dow, VIX, etc.).
    """
    indices = {
        "S&P 500": "^GSPC",
        "Nasdaq 100": "^NDX",
        "Dow Jones": "^DJI",
        "Russell 2000": "^RUT",
        "VIX": "^VIX",
        "10Y Treasury": "^TNX",
        "Gold": "GC=F",
        "Crude Oil": "CL=F",
        "Bitcoin": "BTC-USD",
    }

    results = {}
    for name, sym in indices.items():
        try:
            t = yf.Ticker(sym)
            fast = t.fast_info
            price = _safe_float(getattr(fast, "last_price", None))
            prev = _safe_float(getattr(fast, "previous_close", None))
            chg = price - prev if price and prev else 0
            chg_pct = (chg / prev * 100) if prev else 0
            results[name] = {
                "symbol": sym,
                "price": round(price, 2),
                "change": round(chg, 2),
                "change_pct": round(chg_pct, 2),
            }
        except Exception:
            results[name] = {"symbol": sym, "price": 0, "change": 0, "change_pct": 0}

    return {"indices": results, "timestamp": datetime.now(timezone.utc).isoformat()}


def get_sector_performance() -> dict:
    """Get performance of all S&P 500 sectors via SPDR ETFs.

    Returns:
        YTD and 1-day performance for each GICS sector.
    """
    sectors = {
        "Technology": "XLK",
        "Healthcare": "XLV",
        "Financials": "XLF",
        "Consumer Discretionary": "XLY",
        "Communication Services": "XLC",
        "Industrials": "XLI",
        "Consumer Staples": "XLP",
        "Energy": "XLE",
        "Utilities": "XLU",
        "Real Estate": "XLRE",
        "Materials": "XLB",
    }

    results = {}
    for sector, etf in sectors.items():
        try:
            t = yf.Ticker(etf)
            fast = t.fast_info
            price = _safe_float(getattr(fast, "last_price", None))
            prev = _safe_float(getattr(fast, "previous_close", None))
            ytd_high = _safe_float(getattr(fast, "year_high", None))
            ytd_low = _safe_float(getattr(fast, "year_low", None))
            chg_pct = ((price - prev) / prev * 100) if prev else 0
            results[sector] = {
                "etf": etf,
                "price": round(price, 2),
                "change_pct_1d": round(chg_pct, 2),
                "52w_high": round(ytd_high, 2),
                "52w_low": round(ytd_low, 2),
            }
        except Exception:
            results[sector] = {"etf": etf, "price": 0, "change_pct_1d": 0}

    return {"sectors": results, "timestamp": datetime.now(timezone.utc).isoformat()}


def get_stock_news(ticker: str, limit: int = 5) -> dict:
    """Get recent news headlines for a stock.

    Args:
        ticker: Stock ticker symbol.
        limit: Maximum number of news items to return (1-10).

    Returns:
        List of recent news articles with title, publisher, and link.
    """
    try:
        limit = max(1, min(10, limit))
        stock = yf.Ticker(ticker.upper())
        news = stock.news or []

        articles = []
        for item in news[:limit]:
            articles.append({
                "title": item.get("title", ""),
                "publisher": item.get("publisher", ""),
                "link": item.get("link", ""),
                "published_at": datetime.fromtimestamp(
                    item.get("providerPublishTime", 0), tz=timezone.utc
                ).strftime("%Y-%m-%d %H:%M UTC") if item.get("providerPublishTime") else "",
                "summary": item.get("summary", ""),
            })

        return {"ticker": ticker.upper(), "articles": articles, "count": len(articles)}
    except Exception as exc:
        return {"error": str(exc), "ticker": ticker.upper(), "articles": []}
