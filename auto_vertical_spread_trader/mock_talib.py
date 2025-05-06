"""
TA-Lib compatibility layer using pandas-ta under the hood.

This module provides a drop-in replacement for TA-Lib functions using pandas-ta.
It helps with transitioning from TA-Lib to pandas-ta by providing a compatible API.
Prefer using pandas-ta directly in new code.

IMPORTANT: This is a transitional module. In the future, code should directly use pandas-ta
with its native DataFrame-centric API rather than this compatibility layer.

Usage:
    # For transition only - prefer pandas-ta's native API for new code
    import auto_vertical_spread_trader.mock_talib as talib

    # Use just like regular TA-Lib
    df['ATR14'] = talib.ATR(df['high'], df['low'], df['close'], timeperiod=14)

    # Better approach for new code:
    import pandas_ta as ta
    df['ATR14'] = df.ta.atr(length=14)
"""

import warnings
from typing import List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import pandas_ta as ta
from numpy.typing import NDArray

# Emit deprecation warning when module is imported
warnings.warn(
    "The mock_talib module is a transitional compatibility layer. "
    "Please use pandas-ta directly with its native API in new code.",
    DeprecationWarning,
    stacklevel=2,
)

# Create a list of function names for compatibility with talib.get_functions()
_FUNCTIONS = [
    "ATR",
    "SMA",
    "EMA",
    "WMA",
    "DEMA",
    "TEMA",
    "TRIMA",
    "KAMA",
    "MAMA",
    "RSI",
    "MACD",
    "STOCH",
    "STOCHRSI",
    "ADX",
    "ADXR",
    "CCI",
    "MOM",
    "OBV",
    "AD",
    "ADOSC",
    "NATR",
    "TRANGE",
    "BBANDS",
]


def get_functions() -> List[str]:
    """Return a list of supported function names."""
    return _FUNCTIONS


def __version__():
    """Return pandas-ta version as a compatibility layer."""
    return ta.__version__


# ----- Moving Averages -----


def SMA(close: np.ndarray, timeperiod: int = 14) -> NDArray:
    """Simple Moving Average using pandas-ta."""
    df = pd.DataFrame({"close": close})
    result = df.ta.sma(length=timeperiod)
    return np.asarray(result.to_numpy())


def EMA(close: np.ndarray, timeperiod: int = 14) -> NDArray:
    """Exponential Moving Average using pandas-ta."""
    df = pd.DataFrame({"close": close})
    result = df.ta.ema(length=timeperiod)
    return np.asarray(result.to_numpy())


def WMA(close: np.ndarray, timeperiod: int = 14) -> NDArray:
    """Weighted Moving Average using pandas-ta."""
    df = pd.DataFrame({"close": close})
    result = df.ta.wma(length=timeperiod)
    return np.asarray(result.to_numpy())


def DEMA(close: np.ndarray, timeperiod: int = 14) -> NDArray:
    """Double Exponential Moving Average using pandas-ta."""
    df = pd.DataFrame({"close": close})
    result = df.ta.dema(length=timeperiod)
    return np.asarray(result.to_numpy())


def TEMA(close: np.ndarray, timeperiod: int = 14) -> NDArray:
    """Triple Exponential Moving Average using pandas-ta."""
    df = pd.DataFrame({"close": close})
    result = df.ta.tema(length=timeperiod)
    return np.asarray(result.to_numpy())


def TRIMA(close: np.ndarray, timeperiod: int = 14) -> NDArray:
    """Triangular Moving Average using pandas-ta."""
    df = pd.DataFrame({"close": close})
    result = df.ta.trima(length=timeperiod)
    return np.asarray(result.to_numpy())


def KAMA(close: np.ndarray, timeperiod: int = 14) -> NDArray:
    """Kaufman Adaptive Moving Average using pandas-ta."""
    df = pd.DataFrame({"close": close})
    result = df.ta.kama(length=timeperiod)
    return np.asarray(result.to_numpy())


def MAMA(
    close: np.ndarray, fastlimit: float = 0.5, slowlimit: float = 0.05
) -> Tuple[NDArray, NDArray]:
    """MESA Adaptive Moving Average using pandas-ta."""
    df = pd.DataFrame({"close": close})
    result = df.ta.mama(fast=fastlimit, slow=slowlimit)
    # Return MAMA and FAMA as tuple for TA-Lib compatibility
    return (
        np.asarray(result["MAMA"].to_numpy()),
        np.asarray(result["FAMA"].to_numpy()),
    )


# ----- Momentum Indicators -----


def RSI(close: np.ndarray, timeperiod: int = 14) -> NDArray:
    """Relative Strength Index using pandas-ta."""
    df = pd.DataFrame({"close": close})
    result = df.ta.rsi(length=timeperiod)
    return np.asarray(result.to_numpy())


def MACD(
    close: np.ndarray, fastperiod: int = 12, slowperiod: int = 26, signalperiod: int = 9
) -> Tuple[NDArray, NDArray, NDArray]:
    """Moving Average Convergence/Divergence using pandas-ta."""
    df = pd.DataFrame({"close": close})
    result = df.ta.macd(fast=fastperiod, slow=slowperiod, signal=signalperiod)
    # Return MACD, Signal, and Histogram as tuple for TA-Lib compatibility
    return (
        np.asarray(result[f"MACD_{fastperiod}_{slowperiod}_{signalperiod}"].to_numpy()),
        np.asarray(result[f"MACDs_{fastperiod}_{slowperiod}_{signalperiod}"].to_numpy()),
        np.asarray(result[f"MACDh_{fastperiod}_{slowperiod}_{signalperiod}"].to_numpy()),
    )


def STOCH(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    fastk_period: int = 5,
    slowk_period: int = 3,
    slowk_matype: int = 0,
    slowd_period: int = 3,
    slowd_matype: int = 0,
) -> Tuple[NDArray, NDArray]:
    """Stochastic Oscillator using pandas-ta."""
    df = pd.DataFrame({"high": high, "low": low, "close": close})
    result = df.ta.stoch(k=fastk_period, d=slowd_period, smooth_k=slowk_period)
    # For simplicity, we ignore the MA types as pandas-ta doesn't support them directly
    return (
        np.asarray(result[f"STOCHk_{fastk_period}_{slowk_period}_{slowd_period}"].to_numpy()),
        np.asarray(result[f"STOCHd_{fastk_period}_{slowk_period}_{slowd_period}"].to_numpy()),
    )


def STOCHRSI(
    close: np.ndarray,
    timeperiod: int = 14,
    fastk_period: int = 5,
    fastd_period: int = 3,
    fastd_matype: int = 0,
) -> Tuple[NDArray, NDArray]:
    """Stochastic RSI using pandas-ta."""
    df = pd.DataFrame({"close": close})
    result = df.ta.stochrsi(
        length=timeperiod, rsi_length=timeperiod, k=fastk_period, d=fastd_period
    )
    # For simplicity, we ignore the MA types as pandas-ta doesn't support them directly
    return (
        np.asarray(result[f"STOCHRSIk_{timeperiod}_{fastk_period}_{fastd_period}"].to_numpy()),
        np.asarray(result[f"STOCHRSId_{timeperiod}_{fastk_period}_{fastd_period}"].to_numpy()),
    )


def ADX(high: np.ndarray, low: np.ndarray, close: np.ndarray, timeperiod: int = 14) -> NDArray:
    """Average Directional Movement Index using pandas-ta."""
    df = pd.DataFrame({"high": high, "low": low, "close": close})
    result = df.ta.adx(length=timeperiod)
    return np.asarray(result["ADX_14"].to_numpy())


def ADXR(high: np.ndarray, low: np.ndarray, close: np.ndarray, timeperiod: int = 14) -> NDArray:
    """Average Directional Movement Index Rating using pandas-ta."""
    df = pd.DataFrame({"high": high, "low": low, "close": close})
    # pandas-ta doesn't have a direct ADXR function, so we calculate it
    adx = df.ta.adx(length=timeperiod)
    # ADXR is the average of current ADX and ADX from 'timeperiod' periods ago
    adxr = (adx["ADX_14"] + adx["ADX_14"].shift(timeperiod)) / 2
    return np.asarray(adxr.to_numpy())


def CCI(high: np.ndarray, low: np.ndarray, close: np.ndarray, timeperiod: int = 14) -> NDArray:
    """Commodity Channel Index using pandas-ta."""
    df = pd.DataFrame({"high": high, "low": low, "close": close})
    result = df.ta.cci(length=timeperiod)
    return np.asarray(result.to_numpy())


def MOM(close: np.ndarray, timeperiod: int = 10) -> NDArray:
    """Momentum using pandas-ta."""
    df = pd.DataFrame({"close": close})
    result = df.ta.mom(length=timeperiod)
    return np.asarray(result.to_numpy())


# ----- Volume Indicators -----


def OBV(close: np.ndarray, volume: np.ndarray) -> NDArray:
    """On Balance Volume using pandas-ta."""
    df = pd.DataFrame({"close": close, "volume": volume})
    result = df.ta.obv()
    return np.asarray(result.to_numpy())


def AD(high: np.ndarray, low: np.ndarray, close: np.ndarray, volume: np.ndarray) -> NDArray:
    """Chaikin A/D Line using pandas-ta."""
    df = pd.DataFrame({"high": high, "low": low, "close": close, "volume": volume})
    result = df.ta.ad()
    return np.asarray(result.to_numpy())


def ADOSC(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    volume: np.ndarray,
    fastperiod: int = 3,
    slowperiod: int = 10,
) -> NDArray:
    """Chaikin A/D Oscillator using pandas-ta."""
    df = pd.DataFrame({"high": high, "low": low, "close": close, "volume": volume})
    result = df.ta.adosc(fast=fastperiod, slow=slowperiod)
    return np.asarray(result.to_numpy())


# ----- Volatility Indicators -----


def ATR(high: np.ndarray, low: np.ndarray, close: np.ndarray, timeperiod: int = 14) -> NDArray:
    """Average True Range using pandas-ta."""
    df = pd.DataFrame({"high": high, "low": low, "close": close})
    result = df.ta.atr(length=timeperiod)
    return np.asarray(result.to_numpy())


def NATR(high: np.ndarray, low: np.ndarray, close: np.ndarray, timeperiod: int = 14) -> NDArray:
    """Normalized Average True Range using pandas-ta."""
    df = pd.DataFrame({"high": high, "low": low, "close": close})
    atr = df.ta.atr(length=timeperiod)
    # NATR = (ATR / CLOSE) * 100
    natr = (atr / df["close"]) * 100
    return np.asarray(natr.to_numpy())


def TRANGE(high: np.ndarray, low: np.ndarray, close: np.ndarray) -> NDArray:
    """True Range using pandas-ta."""
    df = pd.DataFrame({"high": high, "low": low, "close": close})
    result = df.ta.true_range()
    return np.asarray(result.to_numpy())


def BBANDS(
    close: np.ndarray, timeperiod: int = 20, nbdevup: float = 2, nbdevdn: float = 2, matype: int = 0
) -> Tuple[NDArray, NDArray, NDArray]:
    """Bollinger Bands using pandas-ta."""
    df = pd.DataFrame({"close": close})
    # For simplicity, we ignore matype as pandas-ta defaults to SMA
    result = df.ta.bbands(length=timeperiod, std=nbdevup)  # assuming nbdevup = nbdevdn
    # Return Upper, Middle, Lower as tuple for TA-Lib compatibility
    return (
        np.asarray(result[f"BBU_{timeperiod}_{nbdevup}.0"].to_numpy()),
        np.asarray(result[f"BBM_{timeperiod}_{nbdevup}.0"].to_numpy()),
        np.asarray(result[f"BBL_{timeperiod}_{nbdevup}.0"].to_numpy()),
    )
