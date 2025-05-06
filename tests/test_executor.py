"""
Unit tests for the executor module
"""

import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
import numpy as np
import sys
from pathlib import Path

# Add the parent directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestOptionSelection(unittest.TestCase):
    """Test cases for option selection logic"""

    def setUp(self):
        """Set up mock objects for testing"""
        # Create a mock IB connection
        self.mock_ib = MagicMock()

        # Mock config with reasonable defaults
        self.config = {
            "MIN_DELTA": 0.30,
            "MAX_DELTA": 0.50,
            "TARGET_DAYS_TO_EXPIRY": 45,
            "MAX_SPREAD_COST": 500,
            "MAX_BID_ASK_SPREAD_PCT": 10.0,
        }

        # Mock options chain data
        self.mock_options = self._create_mock_options_chain()

        # Patch the options fetching function
        self.options_patcher = patch("executor.get_options_chain")
        self.mock_get_options = self.options_patcher.start()
        self.mock_get_options.return_value = self.mock_options

    def tearDown(self):
        """Clean up patches after tests"""
        self.options_patcher.stop()

    def _create_mock_options_chain(self):
        """Create a mock options chain for testing"""
        # Mock structure with call and put options at different strikes and expiries
        chain = {
            "2023-07-21": {  # ~45 days out
                "calls": pd.DataFrame(
                    {
                        "strike": [95, 100, 105, 110, 115],
                        "bid": [6.0, 3.8, 2.0, 0.9, 0.4],
                        "ask": [6.2, 4.0, 2.2, 1.0, 0.5],
                        "delta": [0.70, 0.55, 0.40, 0.25, 0.15],
                        "volume": [100, 250, 300, 150, 50],
                    }
                ),
                "puts": pd.DataFrame(
                    {
                        "strike": [95, 100, 105, 110, 115],
                        "bid": [0.4, 0.9, 2.0, 3.8, 6.0],
                        "ask": [0.5, 1.0, 2.2, 4.0, 6.2],
                        "delta": [-0.15, -0.25, -0.40, -0.55, -0.70],
                        "volume": [50, 150, 300, 250, 100],
                    }
                ),
            },
            "2023-06-16": {  # ~30 days out
                "calls": pd.DataFrame(
                    {
                        "strike": [95, 100, 105, 110, 115],
                        "bid": [5.5, 3.4, 1.7, 0.7, 0.3],
                        "ask": [5.7, 3.6, 1.9, 0.8, 0.4],
                        "delta": [0.75, 0.60, 0.42, 0.27, 0.12],
                        "volume": [80, 200, 250, 100, 30],
                    }
                ),
                "puts": pd.DataFrame(
                    {
                        "strike": [95, 100, 105, 110, 115],
                        "bid": [0.3, 0.7, 1.7, 3.4, 5.5],
                        "ask": [0.4, 0.8, 1.9, 3.6, 5.7],
                        "delta": [-0.12, -0.27, -0.42, -0.60, -0.75],
                        "volume": [30, 100, 250, 200, 80],
                    }
                ),
            },
        }
        return chain

    @patch("executor.select_vertical_spread")
    def test_find_call_vertical(self, mock_select_vertical):
        """Test finding a call vertical spread"""
        from executor import find_option_spread

        # Set up the mock to return a valid spread
        mock_select_vertical.return_value = (
            {"strike": 105, "bid": 2.0, "ask": 2.2, "delta": 0.40},  # Long option
            {"strike": 110, "bid": 0.9, "ask": 1.0, "delta": 0.25},  # Short option
            1.2,  # Net debit
        )

        # Test with a stock price of 100, bull strategy (calls)
        result = find_option_spread(self.mock_ib, "AAPL", 100.0, "bull", self.config)

        # Assert the function was called with right parameters
        mock_select_vertical.assert_called_once()
        args, kwargs = mock_select_vertical.call_args

        # Verify it's trying to select call options
        self.assertEqual(kwargs["option_type"], "calls")

        # Verify it returns the expected result format
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 3)

    @patch("executor.select_vertical_spread")
    def test_find_put_vertical(self, mock_select_vertical):
        """Test finding a put vertical spread"""
        from executor import find_option_spread

        # Set up the mock to return a valid spread
        mock_select_vertical.return_value = (
            {"strike": 105, "bid": 2.0, "ask": 2.2, "delta": -0.40},  # Long option
            {"strike": 100, "bid": 0.9, "ask": 1.0, "delta": -0.25},  # Short option
            1.2,  # Net debit
        )

        # Test with a stock price of 100, bear strategy (puts)
        result = find_option_spread(self.mock_ib, "AAPL", 100.0, "bear", self.config)

        # Assert the function was called with right parameters
        mock_select_vertical.assert_called_once()
        args, kwargs = mock_select_vertical.call_args

        # Verify it's trying to select put options
        self.assertEqual(kwargs["option_type"], "puts")

        # Verify it returns the expected result format
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 3)

    def test_select_vertical_spread_calls(self):
        """Test selecting a call vertical spread with target deltas"""
        from executor import select_vertical_spread

        options_chain = self.mock_options["2023-07-21"]
        current_price = 100.0

        # Test selecting a valid call spread
        long_opt, short_opt, debit = select_vertical_spread(
            options_chain,
            current_price,
            option_type="calls",
            min_delta=0.35,
            max_delta=0.45,
            max_spread_cost=200,
        )

        # Verify it selected the right strikes based on delta
        self.assertEqual(long_opt["strike"], 105)  # Delta 0.40
        self.assertEqual(short_opt["strike"], 110)  # Delta 0.25

        # Verify debit calculation
        expected_debit = long_opt["ask"] - short_opt["bid"]
        self.assertEqual(debit, expected_debit)


if __name__ == "__main__":
    unittest.main()
