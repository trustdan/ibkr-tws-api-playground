"""
Unit tests for scan conditions
"""

import unittest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch
import sys
from pathlib import Path

# Add the parent directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from auto_vertical_spread_trader.scans import (
    bull_pullback_condition,
    bear_rally_condition,
    high_base_condition,
    low_base_condition,
)


class TestScanConditions(unittest.TestCase):
    """Test cases for scan conditions"""

    def setUp(self):
        """Set up test dataframes for each test"""
        # Create a base dataframe with 60 days of data
        dates = pd.date_range(end=pd.Timestamp.today(), periods=60)
        self.df = pd.DataFrame(
            {
                "date": dates,
                "open": np.random.rand(60) * 100 + 100,  # Random prices between 100-200
                "high": np.random.rand(60) * 100 + 100,
                "low": np.random.rand(60) * 100 + 100,
                "close": np.random.rand(60) * 100 + 100,
                "volume": np.random.rand(60) * 1000000,  # Random volume
            }
        )
        self.df.set_index("date", inplace=True)

        # Calculate standard indicators
        self.df["MA50"] = self.df["close"].rolling(50).mean()
        self.df["ATR14"] = (
            self.df["high"].rolling(14).mean() - self.df["low"].rolling(14).mean()
        )  # Simple proxy for ATR
        self.df["52w_high"] = self.df["close"].rolling(252, min_periods=50).max()
        self.df["52w_low"] = self.df["close"].rolling(252, min_periods=50).min()
        self.df["ATR_ratio"] = (
            self.df["ATR14"] / self.df["ATR14"].rolling(20, min_periods=10).mean()
        )
        self.df["range_pct"] = (self.df["high"] - self.df["low"]) / self.df["close"] * 100
        self.df["range_ratio"] = (
            self.df["range_pct"] / self.df["range_pct"].rolling(20, min_periods=10).mean()
        )

    def test_bull_pullback_true(self):
        """Test bull pullback condition when it should return True"""
        # Set up the data to match bull pullback condition
        self.df.iloc[-3, self.df.columns.get_loc("open")] = 150
        self.df.iloc[-3, self.df.columns.get_loc("close")] = 155  # Bullish day

        self.df.iloc[-2, self.df.columns.get_loc("open")] = 155
        self.df.iloc[-2, self.df.columns.get_loc("close")] = 160  # Bullish day

        # Set up MA rising
        self.df.iloc[-1, self.df.columns.get_loc("MA50")] = 152
        self.df.iloc[-2, self.df.columns.get_loc("MA50")] = 151

        # Price pulls back to MA
        self.df.iloc[-1, self.df.columns.get_loc("low")] = 151

        result, _ = bull_pullback_condition(self.df)
        self.assertTrue(result)

    def test_bull_pullback_false(self):
        """Test bull pullback condition when it should return False"""
        # Set up the data to fail bull pullback condition
        self.df.iloc[-3, self.df.columns.get_loc("open")] = 155
        self.df.iloc[-3, self.df.columns.get_loc("close")] = 150  # Bearish day

        self.df.iloc[-2, self.df.columns.get_loc("open")] = 150
        self.df.iloc[-2, self.df.columns.get_loc("close")] = 155  # Bullish day (only one bullish)

        # Set up MA rising
        self.df.iloc[-1, self.df.columns.get_loc("MA50")] = 152
        self.df.iloc[-2, self.df.columns.get_loc("MA50")] = 151

        # Price pulls back to MA
        self.df.iloc[-1, self.df.columns.get_loc("low")] = 151

        result, _ = bull_pullback_condition(self.df)
        self.assertFalse(result)

    def test_bear_rally_true(self):
        """Test bear rally condition when it should return True"""
        # Set up the data to match bear rally condition
        self.df.iloc[-3, self.df.columns.get_loc("open")] = 155
        self.df.iloc[-3, self.df.columns.get_loc("close")] = 150  # Bearish day

        self.df.iloc[-2, self.df.columns.get_loc("open")] = 150
        self.df.iloc[-2, self.df.columns.get_loc("close")] = 145  # Bearish day

        # Set up MA falling
        self.df.iloc[-1, self.df.columns.get_loc("MA50")] = 151
        self.df.iloc[-2, self.df.columns.get_loc("MA50")] = 152

        # Price rallies to MA
        self.df.iloc[-1, self.df.columns.get_loc("high")] = 152

        result, _ = bear_rally_condition(self.df)
        self.assertTrue(result)

    def test_high_base_true(self):
        """Test high base condition when it should return True"""
        # Set up the data to match high base condition
        # Price near 52-week high
        self.df.iloc[-1, self.df.columns.get_loc("close")] = 195
        self.df.iloc[-1, self.df.columns.get_loc("52w_high")] = 200

        # Low volatility
        self.df.iloc[-1, self.df.columns.get_loc("ATR_ratio")] = 0.7

        # Tight range
        self.df["range_pct"] = (self.df["high"] - self.df["low"]) / self.df["close"] * 100
        # Make range tighter than average
        avg_range = self.df["range_pct"].rolling(20, min_periods=1).mean().iloc[-1]
        self.df.iloc[-1, self.df.columns.get_loc("range_pct")] = avg_range * 0.7

        result, _ = high_base_condition(self.df)
        self.assertTrue(result)

    def test_low_base_true(self):
        """Test low base condition when it should return True"""
        # Set up the data to match low base condition
        # Price near 52-week low
        self.df.iloc[-1, self.df.columns.get_loc("close")] = 105
        self.df.iloc[-1, self.df.columns.get_loc("52w_low")] = 100

        # Low volatility
        self.df.iloc[-1, self.df.columns.get_loc("ATR_ratio")] = 0.7

        # Tight range
        self.df["range_pct"] = (self.df["high"] - self.df["low"]) / self.df["close"] * 100
        # Make range tighter than average
        avg_range = self.df["range_pct"].rolling(20, min_periods=1).mean().iloc[-1]
        self.df.iloc[-1, self.df.columns.get_loc("range_pct")] = avg_range * 0.7

        result, _ = low_base_condition(self.df)
        self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()
