"""
Mock implementation of TA-Lib functions for testing environments
where the actual TA-Lib cannot be installed.

This provides enough functionality to run tests, but not for production use.
"""

import numpy as np
import pandas as pd
import warnings

# Display a warning that we're using the mock version
warnings.warn(
    "Using mock_talib instead of real TA-Lib. This is only for testing/CI environments.",
    UserWarning
)

def SMA(values, timeperiod=30):
    """Simple Moving Average mock implementation"""
    values = np.asarray(values)
    return pd.Series(values).rolling(window=timeperiod).mean().values

def EMA(values, timeperiod=30):
    """Exponential Moving Average mock implementation"""
    values = np.asarray(values)
    return pd.Series(values).ewm(span=timeperiod, adjust=False).mean().values

def RSI(values, timeperiod=14):
    """Relative Strength Index mock implementation"""
    values = pd.Series(values)
    # Calculate price differences
    delta = values.diff().dropna()
    
    # Calculate gains and losses
    gains = delta.copy()
    gains[gains < 0] = 0
    losses = -delta.copy()
    losses[losses < 0] = 0
    
    # Calculate average gains and losses
    avg_gain = gains.rolling(window=timeperiod).mean()
    avg_loss = losses.rolling(window=timeperiod).mean()
    
    # Calculate RS and RSI
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    # Fill first timeperiod values with NaN
    result = np.empty_like(values)
    result[:] = np.nan
    result[timeperiod:] = rsi[timeperiod:].values
    
    return result

def BBANDS(values, timeperiod=5, nbdevup=2, nbdevdn=2, matype=0):
    """Bollinger Bands mock implementation"""
    values = np.asarray(values)
    sma = SMA(values, timeperiod)
    std = pd.Series(values).rolling(window=timeperiod).std().values
    
    upper = sma + nbdevup * std
    middle = sma
    lower = sma - nbdevdn * std
    
    return upper, middle, lower

def ATR(high, low, close, timeperiod=14):
    """Average True Range mock implementation"""
    high = pd.Series(high)
    low = pd.Series(low)
    close = pd.Series(close)
    
    # Calculate True Range
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # Calculate ATR
    atr = tr.rolling(window=timeperiod).mean().values
    
    # Fill first timeperiod values with NaN
    result = np.empty_like(close)
    result[:] = np.nan
    result[timeperiod-1:] = atr[timeperiod-1:]
    
    return result

# Function to replace imported TA-Lib functions with mocks
def patch_talib():
    """
    Apply monkey patching to modules that import TA-Lib.
    This should be called at the start of tests when TA-Lib is not available.
    """
    import sys
    
    # Create a mock talib module
    class MockTaLib:
        SMA = SMA
        EMA = EMA
        RSI = RSI
        BBANDS = BBANDS
        ATR = ATR
    
    # Add it to sys.modules so imports use this instead
    sys.modules['talib'] = MockTaLib
    
    print("Mock TA-Lib successfully applied. Functions available: SMA, EMA, RSI, BBANDS, ATR")
    return True 