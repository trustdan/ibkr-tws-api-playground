"""
Tests for pandas-ta indicator functionality.
Used to verify proper pandas-ta installation and catch regressions.
"""

import numpy as np
import pandas as pd
import pytest

try:
    import pandas_ta as ta

    PANDAS_TA_AVAILABLE = True
except ImportError:
    PANDAS_TA_AVAILABLE = False

# Skip all tests if pandas-ta is not available
pytestmark = pytest.mark.skipif(not PANDAS_TA_AVAILABLE, reason="pandas-ta not installed")


# Create test data fixtures
@pytest.fixture
def price_data():
    # Generate random but realistic looking price data
    np.random.seed(42)  # For reproducibility
    close = 100 + np.cumsum(np.random.normal(0, 1, 100))  # Random walk
    high = close + np.random.uniform(0, 3, 100)
    low = close - np.random.uniform(0, 3, 100)
    volume = np.random.randint(1000, 10000, 100)
    df = pd.DataFrame({"close": close, "high": high, "low": low, "volume": volume})
    return df


def test_pandas_ta_import():
    """Verify pandas-ta imports correctly"""
    assert PANDAS_TA_AVAILABLE, "pandas-ta should be importable"
    assert hasattr(ta, "sma"), "sma function should be available"
    assert len(ta.Category) > 5, "pandas-ta should have multiple categories of indicators"


def test_moving_averages(price_data):
    """Test various moving average indicators"""
    df = price_data

    # Test Simple Moving Average
    sma = df.ta.sma(length=14)
    assert not sma.isna().all(), "SMA should produce valid output"
    assert sma.shape[0] == df.shape[0], "SMA output should have same length as input"

    # Test Exponential Moving Average
    ema = df.ta.ema(length=14)
    assert not ema.isna().all(), "EMA should produce valid output"

    # Test Weighted Moving Average
    wma = df.ta.wma(length=14)
    assert not wma.isna().all(), "WMA should produce valid output"


def test_momentum_indicators(price_data):
    """Test momentum indicators"""
    df = price_data

    # Test Relative Strength Index
    rsi = df.ta.rsi(length=14)
    assert not rsi.isna().all(), "RSI should produce valid output"
    assert (rsi.dropna() >= 0).all() and (
        rsi.dropna() <= 100
    ).all(), "RSI values should be between 0 and 100"

    # Test Stochastic
    stoch = df.ta.stoch(k=5, d=3, smooth_k=3)
    assert not stoch["STOCHk_5_3_3"].isna().all(), "STOCH should produce valid output"

    # Test MACD
    macd = df.ta.macd(fast=12, slow=26, signal=9)
    assert not macd["MACD_12_26_9"].isna().all(), "MACD should produce valid output"


def test_volatility_indicators(price_data):
    """Test volatility indicators"""
    df = price_data

    # Test Average True Range
    atr = df.ta.atr(length=14)
    assert not atr.isna().all(), "ATR should produce valid output"

    # Test Bollinger Bands
    bbands = df.ta.bbands(length=20, std=2)
    assert not bbands["BBU_20_2.0"].isna().all(), "BBANDS should produce valid output"
    assert (
        bbands["BBU_20_2.0"].dropna() >= bbands["BBM_20_2.0"].dropna()
    ).all(), "Upper band should be above middle band"
    assert (
        bbands["BBM_20_2.0"].dropna() >= bbands["BBL_20_2.0"].dropna()
    ).all(), "Middle band should be above lower band"


def test_volume_indicators(price_data):
    """Test volume indicators"""
    df = price_data

    # Test On Balance Volume
    obv = df.ta.obv()
    assert not obv.isna().all(), "OBV should produce valid output"

    # Test Chaikin A/D Line
    ad = df.ta.ad()
    assert not ad.isna().all(), "A/D Line should produce valid output"


def test_pattern_recognition(price_data):
    """Test candlestick pattern recognition functions"""
    df = price_data

    # Test if candlestick patterns are available in pandas-ta
    # Note: pandas-ta has cdl_pattern which is more general
    if hasattr(ta, "cdl_pattern"):
        cdl_patterns = df.ta.cdl_pattern()
        assert isinstance(cdl_patterns, pd.DataFrame), "Pattern recognition should return DataFrame"


def test_additional_functions(price_data):
    """Test additional functions in pandas-ta"""
    df = price_data

    # Test Donchian Channels
    donchian = df.ta.donchian(lower_length=20, upper_length=20)
    assert not donchian.isna().all().all(), "Donchian Channels should produce valid output"

    # Test Keltner Channels
    keltner = df.ta.kc(length=20, scalar=2)
    assert not keltner.isna().all().all(), "Keltner Channels should produce valid output"
