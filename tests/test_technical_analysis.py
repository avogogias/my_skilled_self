"""Unit tests for technical analysis computations.

Tests run entirely offline — no network calls.
"""

import pytest
from skills.trading_advisor.technical_analysis import (
    _ema,
    _sma,
    compute_bollinger_bands,
    compute_indicators,
    compute_macd,
    compute_rsi,
)


class TestEMA:
    def test_basic_ema(self):
        prices = [10.0, 11.0, 12.0, 13.0, 14.0]
        result = _ema(prices, 3)
        assert len(result) == 3
        # First EMA = SMA of first 3 = (10+11+12)/3 = 11
        assert result[0] == pytest.approx(11.0, rel=1e-3)

    def test_insufficient_data_returns_empty(self):
        assert _ema([1.0, 2.0], 5) == []


class TestSMA:
    def test_basic_sma(self, sample_ohlcv):
        closes = sample_ohlcv["close"]
        result = _sma(closes, 20)
        assert len(result) == len(closes)
        # First 19 should be None
        assert all(v is None for v in result[:19])
        # 20th should be a valid float
        assert result[19] is not None
        assert result[19] == pytest.approx(sum(closes[:20]) / 20, rel=1e-3)

    def test_sma_period_larger_than_data(self):
        prices = [1.0, 2.0, 3.0]
        result = _sma(prices, 10)
        assert all(v is None for v in result)


class TestRSI:
    def test_rsi_in_range(self, sample_ohlcv):
        closes = sample_ohlcv["close"]
        result = compute_rsi(closes, 14)
        valid = [v for v in result if v is not None]
        assert all(0 <= v <= 100 for v in valid), "RSI must be between 0 and 100"

    def test_rsi_length_matches_input(self, sample_ohlcv):
        closes = sample_ohlcv["close"]
        result = compute_rsi(closes, 14)
        assert len(result) == len(closes)

    def test_rsi_insufficient_data(self):
        result = compute_rsi([1.0, 2.0, 3.0], 14)
        assert all(v is None for v in result)

    def test_rsi_constant_prices_returns_neutral(self):
        # No change at all (avg_gain=0, avg_loss=0) → neutral RSI of 50
        prices = [100.0] * 20
        result = compute_rsi(prices, 14)
        valid = [v for v in result if v is not None]
        # Bug fix: both gain and loss = 0 should return 50.0 (neutral), not 100.0
        assert all(v == 50.0 for v in valid)

    def test_rsi_only_gains_returns_100(self):
        # Strictly increasing prices → only gains, no losses → RSI = 100
        prices = [float(i) for i in range(1, 22)]
        result = compute_rsi(prices, 14)
        valid = [v for v in result if v is not None]
        assert all(v == 100.0 for v in valid)

    def test_rsi_only_losses_returns_0(self):
        # Strictly decreasing prices → only losses, no gains → RSI near 0
        prices = [float(20 - i) for i in range(21)]
        result = compute_rsi(prices, 14)
        valid = [v for v in result if v is not None]
        assert all(v == 0.0 for v in valid)


class TestMACD:
    def test_macd_structure(self, sample_ohlcv):
        closes = sample_ohlcv["close"]
        result = compute_macd(closes)
        assert "macd" in result
        assert "signal" in result
        assert "histogram" in result

    def test_histogram_equals_macd_minus_signal(self, sample_ohlcv):
        closes = sample_ohlcv["close"]
        result = compute_macd(closes)
        for m, s, h in zip(result["macd"], result["signal"], result["histogram"]):
            assert abs((m - s) - h) < 1e-6

    def test_macd_empty_on_insufficient_data(self):
        result = compute_macd([1.0] * 10, fast=12, slow=26, signal=9)
        assert result["macd"] == []


class TestBollingerBands:
    def test_bollinger_structure(self, sample_ohlcv):
        closes = sample_ohlcv["close"]
        result = compute_bollinger_bands(closes, 20)
        assert "upper" in result
        assert "middle" in result
        assert "lower" in result

    def test_upper_above_middle_above_lower(self, sample_ohlcv):
        closes = sample_ohlcv["close"]
        result = compute_bollinger_bands(closes, 20)
        for u, m, l in zip(result["upper"], result["middle"], result["lower"]):
            assert u >= m >= l, "upper >= middle >= lower must hold"

    def test_band_length(self, sample_ohlcv):
        closes = sample_ohlcv["close"]
        n = len(closes)
        result = compute_bollinger_bands(closes, 20)
        assert len(result["upper"]) == n - 19
        assert len(result["middle"]) == n - 19
        assert len(result["lower"]) == n - 19


class TestComputeIndicators:
    def test_returns_all_keys(self, sample_ohlcv):
        d = sample_ohlcv
        result = compute_indicators(d["dates"], d["close"], d["high"], d["low"], d["volume"])
        assert "rsi" in result
        assert "macd" in result
        assert "bollinger_bands" in result
        assert "sma_20" in result
        assert "sma_50" in result
        assert "latest" in result
        assert "signals" in result

    def test_latest_values_present(self, sample_ohlcv):
        d = sample_ohlcv
        result = compute_indicators(d["dates"], d["close"], d["high"], d["low"], d["volume"])
        latest = result["latest"]
        assert "close" in latest
        assert "trend" in latest
        assert latest["trend"] in ("Uptrend", "Downtrend", "Sideways")

    def test_signals_is_list_of_strings(self, sample_ohlcv):
        d = sample_ohlcv
        result = compute_indicators(d["dates"], d["close"], d["high"], d["low"], d["volume"])
        assert isinstance(result["signals"], list)
        for s in result["signals"]:
            assert isinstance(s, str)
