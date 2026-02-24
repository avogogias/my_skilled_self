"""Plotly JSON specification builder for interactive charts.

The agent backend never imports Plotly — it merely returns JSON dicts that
conform to the Plotly.js data/layout schema. The React frontend renders them
with react-plotly.js, keeping the backend dependency-free from charting libs.
"""

from typing import Any, Optional
from skills.trading_advisor.data_fetcher import get_historical_data, get_sector_performance
from skills.trading_advisor.technical_analysis import (
    compute_bollinger_bands,
    compute_indicators,
    compute_macd,
    compute_rsi,
    _sma,
)


PLOTLY_THEME = {
    "paper_bgcolor": "#0f1117",
    "plot_bgcolor": "#0f1117",
    "font": {"color": "#e0e0e0", "family": "Inter, sans-serif"},
    "gridcolor": "#1e2130",
}


def _dark_layout(title: str, extra: Optional[dict] = None) -> dict:
    layout = {
        "title": {"text": title, "font": {"size": 18, "color": "#ffffff"}},
        "paper_bgcolor": PLOTLY_THEME["paper_bgcolor"],
        "plot_bgcolor": PLOTLY_THEME["plot_bgcolor"],
        "font": PLOTLY_THEME["font"],
        "legend": {"bgcolor": "#1a1d2e", "bordercolor": "#2d3148"},
        "xaxis": {"gridcolor": "#1e2130", "linecolor": "#2d3148", "showgrid": True},
        "yaxis": {"gridcolor": "#1e2130", "linecolor": "#2d3148", "showgrid": True},
        "hovermode": "x unified",
        "margin": {"l": 50, "r": 20, "t": 60, "b": 40},
    }
    if extra:
        layout.update(extra)
    return layout


def build_candlestick_chart(ticker: str, period: str = "6mo") -> dict:
    """Build a candlestick OHLCV chart with volume subplot.

    Args:
        ticker: Stock ticker symbol.
        period: Data period (1mo, 3mo, 6mo, 1y, 2y).

    Returns:
        Plotly JSON spec dict: {data, layout, config}.
    """
    hist = get_historical_data(ticker, period=period, interval="1d")
    if "error" in hist:
        return {"error": hist["error"]}

    dates = hist["dates"]
    candlestick = {
        "type": "candlestick",
        "x": dates,
        "open": hist["open"],
        "high": hist["high"],
        "low": hist["low"],
        "close": hist["close"],
        "name": ticker.upper(),
        "increasing": {"line": {"color": "#26a69a"}},
        "decreasing": {"line": {"color": "#ef5350"}},
        "yaxis": "y",
    }

    volume_bar = {
        "type": "bar",
        "x": dates,
        "y": hist["volume"],
        "name": "Volume",
        "marker": {
            "color": [
                "#26a69a" if hist["close"][i] >= hist["open"][i] else "#ef5350"
                for i in range(len(dates))
            ],
            "opacity": 0.6,
        },
        "yaxis": "y2",
    }

    layout = _dark_layout(
        f"{ticker.upper()} — Candlestick Chart ({period})",
        {
            "xaxis": {
                "gridcolor": "#1e2130",
                "rangeslider": {"visible": False},
                "type": "date",
            },
            "yaxis": {"gridcolor": "#1e2130", "domain": [0.25, 1.0], "title": "Price (USD)"},
            "yaxis2": {"gridcolor": "#1e2130", "domain": [0, 0.2], "title": "Volume"},
        },
    )

    return {
        "data": [candlestick, volume_bar],
        "layout": layout,
        "config": {"responsive": True, "displayModeBar": True},
    }


def build_technical_chart(ticker: str, period: str = "6mo") -> dict:
    """Build a technical analysis chart with price, MAs, Bollinger Bands, RSI, MACD.

    Args:
        ticker: Stock ticker symbol.
        period: Data period.

    Returns:
        Plotly JSON spec dict with 3 subplots: price+indicators, RSI, MACD.
    """
    hist = get_historical_data(ticker, period=period, interval="1d")
    if "error" in hist:
        return {"error": hist["error"]}

    dates = hist["dates"]
    closes = hist["close"]
    indicators = compute_indicators(
        dates=dates,
        close=closes,
        high=hist["high"],
        low=hist["low"],
        volume=hist["volume"],
    )

    # Align date arrays
    n = len(dates)
    sma20 = indicators["sma_20"]
    sma50 = indicators["sma_50"]
    sma200 = indicators["sma_200"]
    rsi = indicators["rsi"]
    macd_data = indicators["macd"]
    bb = indicators["bollinger_bands"]

    bb_offset = n - len(bb["upper"])
    rsi_offset = n - len([v for v in rsi if v is not None])

    bb_dates = dates[bb_offset:]
    macd_offset = n - len(macd_data["macd"])
    macd_dates = dates[macd_offset:]

    traces = [
        # Price
        {
            "type": "scatter", "x": dates, "y": closes, "name": "Price",
            "line": {"color": "#4fc3f7", "width": 1.5}, "yaxis": "y",
        },
        # Bollinger Bands
        {
            "type": "scatter", "x": bb_dates, "y": bb["upper"],
            "name": "BB Upper", "line": {"color": "#7e57c2", "width": 1, "dash": "dot"},
            "yaxis": "y",
        },
        {
            "type": "scatter", "x": bb_dates, "y": bb["middle"],
            "name": "BB Middle", "line": {"color": "#7e57c2", "width": 1},
            "yaxis": "y",
        },
        {
            "type": "scatter", "x": bb_dates, "y": bb["lower"],
            "name": "BB Lower", "line": {"color": "#7e57c2", "width": 1, "dash": "dot"},
            "fill": "tonexty", "fillcolor": "rgba(126,87,194,0.05)", "yaxis": "y",
        },
        # SMAs
        {
            "type": "scatter", "x": dates,
            "y": [v for v in sma20], "name": "SMA 20",
            "line": {"color": "#ffb74d", "width": 1.2}, "yaxis": "y",
        },
        {
            "type": "scatter", "x": dates,
            "y": [v for v in sma50], "name": "SMA 50",
            "line": {"color": "#ef9a9a", "width": 1.2}, "yaxis": "y",
        },
        # RSI
        {
            "type": "scatter", "x": dates, "y": rsi,
            "name": "RSI (14)", "line": {"color": "#80cbc4", "width": 1.5}, "yaxis": "y2",
        },
        {
            "type": "scatter", "x": dates, "y": [70] * n,
            "name": "Overbought (70)", "line": {"color": "#ef5350", "width": 0.8, "dash": "dash"},
            "yaxis": "y2",
        },
        {
            "type": "scatter", "x": dates, "y": [30] * n,
            "name": "Oversold (30)", "line": {"color": "#26a69a", "width": 0.8, "dash": "dash"},
            "yaxis": "y2",
        },
        # MACD
        {
            "type": "scatter", "x": macd_dates, "y": macd_data["macd"],
            "name": "MACD", "line": {"color": "#29b6f6", "width": 1.5}, "yaxis": "y3",
        },
        {
            "type": "scatter", "x": macd_dates, "y": macd_data["signal"],
            "name": "Signal", "line": {"color": "#ff7043", "width": 1.2}, "yaxis": "y3",
        },
        {
            "type": "bar", "x": macd_dates, "y": macd_data["histogram"],
            "name": "Histogram",
            "marker": {"color": [
                "#26a69a" if (v or 0) >= 0 else "#ef5350"
                for v in macd_data["histogram"]
            ]},
            "yaxis": "y3",
        },
    ]

    layout = _dark_layout(
        f"{ticker.upper()} — Technical Analysis ({period})",
        {
            "xaxis": {"gridcolor": "#1e2130", "type": "date", "rangeslider": {"visible": False}},
            "yaxis": {"gridcolor": "#1e2130", "domain": [0.45, 1.0], "title": "Price"},
            "yaxis2": {"gridcolor": "#1e2130", "domain": [0.25, 0.42], "title": "RSI"},
            "yaxis3": {"gridcolor": "#1e2130", "domain": [0.0, 0.22], "title": "MACD"},
            "height": 700,
        },
    )

    return {
        "data": traces,
        "layout": layout,
        "config": {"responsive": True},
    }


def build_line_chart(ticker: str, period: str = "1y", chart_type: str = "line") -> dict:
    """Build a simple price line (or area) chart.

    Args:
        ticker: Ticker symbol.
        period: Data period.
        chart_type: 'line' or 'area'.

    Returns:
        Plotly JSON spec.
    """
    hist = get_historical_data(ticker, period=period, interval="1d")
    if "error" in hist:
        return {"error": hist["error"]}

    fill = "tozeroy" if chart_type == "area" else "none"
    start = hist["close"][0] if hist["close"] else 0
    end = hist["close"][-1] if hist["close"] else 0
    color = "#26a69a" if end >= start else "#ef5350"

    trace = {
        "type": "scatter",
        "x": hist["dates"],
        "y": hist["close"],
        "name": ticker.upper(),
        "mode": "lines",
        "line": {"color": color, "width": 2},
        "fill": fill,
        "fillcolor": f"rgba({'38,166,154' if end >= start else '239,83,80'},0.15)",
    }

    return {
        "data": [trace],
        "layout": _dark_layout(f"{ticker.upper()} — Price ({period})"),
        "config": {"responsive": True},
    }


def build_comparison_chart(tickers: str, period: str = "1y") -> dict:
    """Build a normalised performance comparison chart for multiple tickers.

    Args:
        tickers: Comma-separated ticker symbols (max 5).
        period: Comparison period.

    Returns:
        Plotly JSON spec with % returns from period start.
    """
    ticker_list = [t.strip().upper() for t in tickers.split(",")][:5]
    colors = ["#4fc3f7", "#26a69a", "#ffb74d", "#ef9a9a", "#ce93d8"]
    traces = []

    for idx, ticker in enumerate(ticker_list):
        hist = get_historical_data(ticker, period=period, interval="1d")
        if "error" in hist or not hist.get("close"):
            continue
        base = hist["close"][0]
        normalised = [round((c - base) / base * 100, 2) for c in hist["close"]]
        traces.append({
            "type": "scatter",
            "x": hist["dates"],
            "y": normalised,
            "name": ticker,
            "mode": "lines",
            "line": {"color": colors[idx % len(colors)], "width": 2},
        })

    if not traces:
        return {"error": "No data available for any of the requested tickers."}

    x_baseline = [traces[0]["x"][0], traces[0]["x"][-1]]
    traces.append({
        "type": "scatter",
        "x": x_baseline,
        "y": [0, 0],
        "name": "Baseline (0%)",
        "mode": "lines",
        "line": {"color": "#555", "width": 1, "dash": "dash"},
    })

    layout = _dark_layout(
        f"Performance Comparison: {', '.join(ticker_list)} ({period})",
        {"yaxis": {"title": "Return (%)", "gridcolor": "#1e2130"}},
    )

    return {
        "data": traces,
        "layout": layout,
        "config": {"responsive": True},
    }


def build_sector_chart() -> dict:
    """Build a horizontal bar chart of today's sector performance.

    Returns:
        Plotly JSON spec with sector ETF daily % change.
    """
    data = get_sector_performance()
    sectors = data.get("sectors", {})

    sorted_sectors = sorted(sectors.items(), key=lambda x: x[1].get("change_pct_1d", 0))
    names = [s for s, _ in sorted_sectors]
    values = [v.get("change_pct_1d", 0) for _, v in sorted_sectors]
    colors = ["#26a69a" if v >= 0 else "#ef5350" for v in values]

    trace = {
        "type": "bar",
        "orientation": "h",
        "x": values,
        "y": names,
        "marker": {"color": colors},
        "text": [f"{v:+.2f}%" for v in values],
        "textposition": "outside",
    }

    layout = _dark_layout(
        "S&P 500 Sector Performance (Today)",
        {
            "xaxis": {"title": "Daily Change (%)", "gridcolor": "#1e2130"},
            "yaxis": {"gridcolor": "#1e2130"},
            "height": 450,
            "margin": {"l": 160, "r": 60, "t": 60, "b": 40},
        },
    )

    return {
        "data": [trace],
        "layout": layout,
        "config": {"responsive": True},
    }


def build_volume_profile_chart(ticker: str, period: str = "3mo") -> dict:
    """Build a volume profile (price distribution) chart.

    Args:
        ticker: Ticker symbol.
        period: Data period.

    Returns:
        Plotly JSON spec with volume distribution by price level.
    """
    hist = get_historical_data(ticker, period=period, interval="1d")
    if "error" in hist:
        return {"error": hist["error"]}

    closes = hist["close"]
    volumes = hist["volume"]

    if not closes:
        return {"error": "No data"}

    price_min = min(closes)
    price_max = max(closes)
    num_bins = 20
    bin_size = (price_max - price_min) / num_bins if price_max != price_min else 1

    bins: dict[float, int] = {}
    for price, vol in zip(closes, volumes):
        bin_key = round(price_min + ((price - price_min) // bin_size) * bin_size, 2)
        bins[bin_key] = bins.get(bin_key, 0) + vol

    sorted_bins = sorted(bins.items())
    prices = [str(k) for k, _ in sorted_bins]
    vols = [v for _, v in sorted_bins]

    trace = {
        "type": "bar",
        "orientation": "h",
        "x": vols,
        "y": prices,
        "marker": {"color": "#4fc3f7", "opacity": 0.8},
        "name": "Volume",
    }

    layout = _dark_layout(
        f"{ticker.upper()} — Volume Profile ({period})",
        {
            "xaxis": {"title": "Volume", "gridcolor": "#1e2130"},
            "yaxis": {"title": "Price ($)", "gridcolor": "#1e2130"},
            "height": 500,
        },
    )

    return {
        "data": [trace],
        "layout": layout,
        "config": {"responsive": True},
    }
