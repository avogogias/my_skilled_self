"""Technical analysis computations (RSI, MACD, Bollinger Bands, etc.).

All indicators are computed from raw OHLCV data without external TA libraries
to keep the dependency tree slim. Results are compatible with both the
trading advisor text responses and the chart generator visualisations.
"""

import math
from typing import Optional


def _ema(prices: list[float], period: int) -> list[float]:
    """Exponential Moving Average."""
    if len(prices) < period:
        return []
    k = 2 / (period + 1)
    ema = [sum(prices[:period]) / period]
    for p in prices[period:]:
        ema.append(p * k + ema[-1] * (1 - k))
    return ema


def _sma(prices: list[float], period: int) -> list[Optional[float]]:
    """Simple Moving Average (with leading None values)."""
    result: list[Optional[float]] = [None] * (period - 1)
    for i in range(period - 1, len(prices)):
        result.append(sum(prices[i - period + 1 : i + 1]) / period)
    return result


def compute_rsi(close: list[float], period: int = 14) -> list[Optional[float]]:
    """Compute RSI (Relative Strength Index).

    Args:
        close: List of closing prices.
        period: Look-back period (default 14).

    Returns:
        List of RSI values (None where insufficient data).
    """
    if len(close) < period + 1:
        return [None] * len(close)

    gains, losses = [], []
    for i in range(1, len(close)):
        delta = close[i] - close[i - 1]
        gains.append(max(delta, 0))
        losses.append(max(-delta, 0))

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    rsi_values: list[Optional[float]] = [None] * period

    def _rsi(ag, al):
        # Both zero means no price movement → neutral midpoint
        if ag == 0 and al == 0:
            return 50.0
        # Only losses, no gains → fully overbought guard against div-by-zero
        if al == 0:
            return 100.0
        rs = ag / al
        return round(100 - (100 / (1 + rs)), 2)

    rsi_values.append(_rsi(avg_gain, avg_loss))

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        rsi_values.append(_rsi(avg_gain, avg_loss))

    return rsi_values


def compute_macd(
    close: list[float],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> dict:
    """Compute MACD line, signal line, and histogram.

    Args:
        close: Closing prices.
        fast: Fast EMA period (default 12).
        slow: Slow EMA period (default 26).
        signal: Signal EMA period (default 9).

    Returns:
        Dict with macd, signal, histogram lists.
    """
    if len(close) < slow + signal:
        return {"macd": [], "signal": [], "histogram": []}

    ema_fast = _ema(close, fast)
    ema_slow = _ema(close, slow)

    # Align: ema_fast starts at index (fast-1), ema_slow at (slow-1)
    offset = slow - fast
    macd_line = [
        round(f - s, 4) for f, s in zip(ema_fast[offset:], ema_slow)
    ]

    signal_line = _ema(macd_line, signal)
    offset_sig = signal - 1
    aligned_macd = macd_line[offset_sig:]
    histogram = [round(m - s, 4) for m, s in zip(aligned_macd, signal_line)]

    return {
        "macd": [round(v, 4) for v in aligned_macd],
        "signal": [round(v, 4) for v in signal_line],
        "histogram": histogram,
    }


def compute_bollinger_bands(
    close: list[float], period: int = 20, std_dev: float = 2.0
) -> dict:
    """Compute Bollinger Bands (upper, middle, lower).

    Args:
        close: Closing prices.
        period: Moving average period (default 20).
        std_dev: Number of standard deviations (default 2.0).

    Returns:
        Dict with upper, middle, lower band lists.
    """
    if len(close) < period:
        return {"upper": [], "middle": [], "lower": []}

    middle, upper, lower = [], [], []
    for i in range(period - 1, len(close)):
        window = close[i - period + 1 : i + 1]
        sma = sum(window) / period
        variance = sum((p - sma) ** 2 for p in window) / period
        std = math.sqrt(variance)
        middle.append(round(sma, 2))
        upper.append(round(sma + std_dev * std, 2))
        lower.append(round(sma - std_dev * std, 2))

    return {"upper": upper, "middle": middle, "lower": lower}


def compute_indicators(
    dates: list[str],
    close: list[float],
    high: list[float],
    low: list[float],
    volume: list[int],
) -> dict:
    """Compute a full set of technical indicators and return a summary.

    Args:
        dates: Date strings.
        close: Closing prices.
        high: High prices.
        low: Low prices.
        volume: Volume data.

    Returns:
        Dict with all indicator arrays and a human-readable summary.
    """
    sma_20 = _sma(close, 20)
    sma_50 = _sma(close, 50)
    sma_200 = _sma(close, 200)
    rsi_14 = compute_rsi(close, 14)
    macd_data = compute_macd(close)
    bb_data = compute_bollinger_bands(close, 20)

    # Latest valid values
    last_close = close[-1] if close else 0
    last_rsi = next((v for v in reversed(rsi_14) if v is not None), None)
    last_sma20 = next((v for v in reversed(sma_20) if v is not None), None)
    last_sma50 = next((v for v in reversed(sma_50) if v is not None), None)
    last_sma200 = next((v for v in reversed(sma_200) if v is not None), None)
    last_macd = macd_data["macd"][-1] if macd_data["macd"] else None
    last_signal = macd_data["signal"][-1] if macd_data["signal"] else None
    last_hist = macd_data["histogram"][-1] if macd_data["histogram"] else None
    last_bb_upper = bb_data["upper"][-1] if bb_data["upper"] else None
    last_bb_lower = bb_data["lower"][-1] if bb_data["lower"] else None

    # Signal interpretations
    signals = []
    if last_rsi is not None:
        if last_rsi > 70:
            signals.append(f"RSI {last_rsi:.1f}: Overbought — potential pullback.")
        elif last_rsi < 30:
            signals.append(f"RSI {last_rsi:.1f}: Oversold — potential bounce.")
        else:
            signals.append(f"RSI {last_rsi:.1f}: Neutral zone.")

    if last_macd is not None and last_signal is not None:
        if last_macd > last_signal:
            signals.append("MACD above signal line: Bullish momentum.")
        else:
            signals.append("MACD below signal line: Bearish momentum.")

    if last_sma50 and last_sma200:
        if last_sma50 > last_sma200:
            signals.append("Golden Cross active (50MA > 200MA): Long-term bullish.")
        else:
            signals.append("Death Cross active (50MA < 200MA): Long-term bearish.")

    if last_close and last_bb_upper and last_bb_lower:
        if last_close > last_bb_upper:
            signals.append("Price above upper Bollinger Band: Overbought / strong momentum.")
        elif last_close < last_bb_lower:
            signals.append("Price below lower Bollinger Band: Oversold / weakness.")

    # Trend direction
    price_30d_ago = close[-30] if len(close) >= 30 else close[0]
    trend_pct = ((last_close - price_30d_ago) / price_30d_ago * 100) if price_30d_ago else 0
    trend = "Uptrend" if trend_pct > 2 else "Downtrend" if trend_pct < -2 else "Sideways"

    return {
        "rsi": rsi_14,
        "macd": macd_data,
        "bollinger_bands": bb_data,
        "sma_20": sma_20,
        "sma_50": sma_50,
        "sma_200": sma_200,
        "latest": {
            "close": last_close,
            "rsi": round(last_rsi, 2) if last_rsi else None,
            "macd": last_macd,
            "macd_signal": last_signal,
            "macd_histogram": last_hist,
            "sma_20": round(last_sma20, 2) if last_sma20 else None,
            "sma_50": round(last_sma50, 2) if last_sma50 else None,
            "sma_200": round(last_sma200, 2) if last_sma200 else None,
            "bb_upper": last_bb_upper,
            "bb_lower": last_bb_lower,
            "trend": trend,
            "trend_30d_pct": round(trend_pct, 2),
        },
        "signals": signals,
        "data_points": len(close),
    }
