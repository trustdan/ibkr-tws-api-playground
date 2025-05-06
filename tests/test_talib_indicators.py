"""
Tests for TA-Lib indicator functionality.
Used to verify proper TA-Lib installation and catch regressions.
"""
import numpy as np
import pytest

try:
    import talib
    TALIB_AVAILABLE = True
except ImportError:
    TALIB_AVAILABLE = False

# Skip all tests if TA-Lib is not available
pytestmark = pytest.mark.skipif(not TALIB_AVAILABLE, reason="TA-Lib not installed")

# Create test data fixtures
@pytest.fixture
def price_data():
    # Generate random but realistic looking price data
    np.random.seed(42)  # For reproducibility
    close = 100 + np.cumsum(np.random.normal(0, 1, 100))  # Random walk
    high = close + np.random.uniform(0, 3, 100)
    low = close - np.random.uniform(0, 3, 100)
    volume = np.random.randint(1000, 10000, 100)
    return {
        'close': close,
        'high': high,
        'low': low,
        'volume': volume
    }

def test_talib_import():
    """Verify TA-Lib imports correctly"""
    assert TALIB_AVAILABLE, "TA-Lib should be importable"
    assert hasattr(talib, 'SMA'), "SMA function should be available"
    assert len(talib.get_functions()) > 100, "TA-Lib should have many functions"

def test_moving_averages(price_data):
    """Test various moving average indicators"""
    close = price_data['close']
    
    # Test Simple Moving Average
    sma = talib.SMA(close, timeperiod=14)
    assert not np.isnan(sma).all(), "SMA should produce valid output"
    assert sma.shape == close.shape, "SMA output should have same shape as input"
    
    # Test Exponential Moving Average
    ema = talib.EMA(close, timeperiod=14)
    assert not np.isnan(ema).all(), "EMA should produce valid output"
    
    # Test Weighted Moving Average
    wma = talib.WMA(close, timeperiod=14)
    assert not np.isnan(wma).all(), "WMA should produce valid output"

def test_momentum_indicators(price_data):
    """Test momentum indicators"""
    close = price_data['close']
    
    # Test Relative Strength Index
    rsi = talib.RSI(close, timeperiod=14)
    assert not np.isnan(rsi).all(), "RSI should produce valid output"
    assert np.all((rsi >= 0) & (rsi <= 100)), "RSI values should be between 0 and 100"
    
    # Test Stochastic
    slowk, slowd = talib.STOCH(price_data['high'], price_data['low'], close, 
                              fastk_period=5, slowk_period=3, slowk_matype=0, 
                              slowd_period=3, slowd_matype=0)
    assert not np.isnan(slowk).all(), "STOCH should produce valid output"
    
    # Test MACD
    macd, macdsignal, macdhist = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
    assert not np.isnan(macd).all(), "MACD should produce valid output"

def test_volatility_indicators(price_data):
    """Test volatility indicators"""
    # Test Average True Range
    atr = talib.ATR(price_data['high'], price_data['low'], price_data['close'], timeperiod=14)
    assert not np.isnan(atr).all(), "ATR should produce valid output"
    
    # Test Bollinger Bands
    upper, middle, lower = talib.BBANDS(price_data['close'], timeperiod=20, 
                                      nbdevup=2, nbdevdn=2, matype=0)
    assert not np.isnan(upper).all(), "BBANDS should produce valid output"
    assert np.all(upper >= middle), "Upper band should be above middle band"
    assert np.all(middle >= lower), "Middle band should be above lower band"

def test_volume_indicators(price_data):
    """Test volume indicators"""
    # Test On Balance Volume
    obv = talib.OBV(price_data['close'], price_data['volume'].astype(int))
    assert not np.isnan(obv).all(), "OBV should produce valid output"
    
    # Test Chaikin A/D Line
    ad = talib.AD(price_data['high'], price_data['low'], 
                price_data['close'], price_data['volume'].astype(int))
    assert not np.isnan(ad).all(), "A/D Line should produce valid output"

def test_pattern_recognition(price_data):
    """Test candlestick pattern recognition functions"""
    if hasattr(talib, 'CDLDOJI'):
        doji = talib.CDLDOJI(price_data['high'], price_data['low'], 
                           price_data['close'], price_data['close'])
        assert isinstance(doji, np.ndarray), "Pattern recognition should return numpy array"

def test_problematic_functions(price_data):
    """Test functions that had symbol issues in the past"""
    close = price_data['close']
    
    # Test AVGDEV (known to have had symbol issues)
    if hasattr(talib, 'AVGDEV'):
        avgdev = talib.AVGDEV(close, timeperiod=14)
        assert not np.isnan(avgdev).all(), "AVGDEV should produce valid output"
        assert avgdev.shape == close.shape, "AVGDEV should return array of same shape"
    
    # Note: If AVGDEV is not available in the installed build, the test will be skipped
    # but the test suite will still pass. This is intentional as some builds may not have it. 