"""Pytest configuration and shared fixtures."""

import os
import sys

import pytest

# Add the agent directory to the Python path so we can import skills directly
AGENT_DIR = os.path.join(os.path.dirname(__file__), "..", "agent")
sys.path.insert(0, AGENT_DIR)


@pytest.fixture
def sample_ohlcv():
    """Realistic synthetic OHLCV data for 60 days."""
    import math
    import random

    random.seed(42)
    base = 150.0
    closes, opens, highs, lows, volumes = [], [], [], [], []
    dates = []

    from datetime import date, timedelta

    start = date(2025, 1, 2)
    for i in range(60):
        day = start + timedelta(days=i)
        if day.weekday() >= 5:  # Skip weekends
            continue
        delta = random.gauss(0.001, 0.018)
        base *= 1 + delta
        o = round(base * random.uniform(0.995, 1.005), 2)
        c = round(base, 2)
        h = round(max(o, c) * random.uniform(1.002, 1.015), 2)
        l = round(min(o, c) * random.uniform(0.985, 0.998), 2)
        v = int(random.uniform(5_000_000, 80_000_000))
        dates.append(day.strftime("%Y-%m-%d 00:00"))
        opens.append(o)
        highs.append(h)
        lows.append(l)
        closes.append(c)
        volumes.append(v)

    return {
        "dates": dates,
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volumes,
    }
