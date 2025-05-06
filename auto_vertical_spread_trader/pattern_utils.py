"""
Candlestick pattern utilities using pandas-ta native implementations.

This module provides wrappers for pandas-ta candlestick pattern functions
without any dependency on TA-Lib.
"""

import pandas as pd
import pandas_ta as ta
from typing import Dict, List, Optional, Union

# List of patterns potentially supported by pandas-ta
# Actual support depends on the pandas-ta version
SUPPORTED_PATTERNS = [
    "doji",  # Classic doji pattern
    "inside",  # Inside bar pattern
]


def get_available_patterns() -> List[str]:
    """Return a list of available candlestick patterns."""
    return SUPPORTED_PATTERNS


def cdl_pattern(
    df: pd.DataFrame, name: Optional[str] = None, append: bool = False, scalar: float = 100.0
) -> pd.DataFrame:
    """
    A wrapper for pandas-ta cdl_pattern that only uses natively implemented patterns.

    Parameters:
    -----------
    df : pandas.DataFrame
        DataFrame with OHLC price data
    name : str, optional
        Name of specific pattern to compute
    append : bool
        Whether to return the original DataFrame with results appended
    scalar : float
        How to scale the results

    Returns:
    --------
    pandas.DataFrame
        DataFrame with pattern results
    """
    # Make sure the required columns exist
    required_cols = ["open", "high", "low", "close"]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"DataFrame must contain '{col}' column")

    # Use pandas-ta's built-in implementation
    try:
        return df.ta.cdl_pattern(name=name, append=append, scalar=scalar)
    except Exception as e:
        raise RuntimeError(f"Error running cdl_pattern: {str(e)}")


def has_pattern(df: pd.DataFrame, pattern: str, threshold: float = 0.0) -> bool:
    """
    Check if the most recent candle in the dataframe has the specified pattern.

    Parameters:
    -----------
    df : pandas.DataFrame
        DataFrame with OHLC price data
    pattern : str
        Pattern name to check for
    threshold : float
        Minimum value to consider the pattern present

    Returns:
    --------
    bool
        True if pattern is present, False otherwise
    """
    # Get the pattern values
    try:
        pattern_prefix = f"CDL_{pattern.upper()}"
        pattern_df = cdl_pattern(df, name=pattern)

        # Find matching column (pandas-ta versions use different naming conventions)
        matching_columns = [col for col in pattern_df.columns if col.startswith(pattern_prefix)]
        if not matching_columns:
            return False

        # Use the first matching column
        pattern_col = matching_columns[0]
        last_value = pattern_df[pattern_col].iloc[-1]
        return last_value is not None and abs(last_value) > threshold
    except Exception:
        # If any error occurs, return False (no pattern)
        return False
