"""
End-to-end integration tests for the trading system
"""

import logging
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd

# Add the parent directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the main trader class
from auto_vertical_spread_trader import AutoVerticalSpreadTrader


class MockIBConnection:
    """Mock IB connection for testing"""

    def __init__(self):
        """Initialize the mock connection"""
        self.isConnected = MagicMock(return_value=True)
        self.reqHistoricalData = MagicMock()
        self.reqContractDetails = MagicMock()
        self.reqMktData = MagicMock()
        self.cancelMktData = MagicMock()
        self.qualifyContracts = MagicMock()
        self.reqAccountSummary = MagicMock()
        self.placeOrder = MagicMock()
        self.connect = MagicMock()
        self.disconnect = MagicMock()
        self.run = MagicMock()

        # Set up mock bar data
        self._setup_mock_data()

    def _setup_mock_data(self):
        """Setup mock data responses"""
        # Create a mock bar response for historical data
        dates = pd.date_range(end=datetime.now(), periods=60)
        self.mock_bars = []

        for i, date in enumerate(dates):
            # Create bullish price action for test stock
            close_price = 100 + (i * 0.5) + (np.sin(i / 10) * 5)  # Trending upward with oscillation

            bar = MagicMock()
            bar.date = date
            bar.open = close_price - 1
            bar.high = close_price + 1
            bar.low = close_price - 2
            bar.close = close_price
            bar.volume = 100000

            self.mock_bars.append(bar)

        # Make reqHistoricalData return the mock bars
        self.reqHistoricalData.return_value = self.mock_bars


class TestIntegration(unittest.TestCase):
    """End-to-end integration tests"""

    def setUp(self):
        """Set up test environment"""
        # Disable logging during tests
        logging.disable(logging.CRITICAL)

        # Create a mock IB connection
        self.mock_ib = MockIBConnection()

        # Patch ib_insync.IB to return our mock
        self.patch_ib = patch("ib_insync.IB", return_value=self.mock_ib)
        self.patch_ib.start()

        # Create test config
        self.config = {
            "IB_HOST": "localhost",
            "IB_PORT": 7497,
            "IB_CLIENT_ID": 1,
            "MAX_POSITIONS": 5,
            "MAX_DAILY_TRADES": 2,
            "MIN_DELTA": 0.30,
            "MAX_DELTA": 0.50,
            "TARGET_DAYS_TO_EXPIRY": 45,
            "MIN_VOLUME": 100000,
            "LOOKBACK_DAYS": 60,
            "STOP_LOSS_ATR_MULT": 1.5,
            "SCAN_END_HOUR": 15,  # 3 PM
            "SCAN_END_MINUTE": 0,
            "UNIVERSE_FILE": "test_universe.csv",
        }

        # Mock universe data
        self.mock_universe = [
            {"symbol": "AAPL", "market_cap": 20000000000, "price": 150.0},
            {"symbol": "MSFT", "market_cap": 18000000000, "price": 250.0},
            {"symbol": "AMZN", "market_cap": 16000000000, "price": 120.0},
        ]

        # Patch universe loading
        self.patch_universe = patch("universe.load_universe", return_value=self.mock_universe)
        self.patch_universe.start()

        # Create the trader instance with mocked components
        self.trader = AutoVerticalSpreadTrader(config_overrides=self.config)

    def tearDown(self):
        """Clean up after tests"""
        self.patch_ib.stop()
        self.patch_universe.stop()
        logging.disable(logging.NOTSET)

    @patch("scans.bull_pullback_condition")
    def test_scan_execution(self, mock_condition):
        """Test that scan execution works end-to-end"""
        # Set up the condition to return True for our test
        mock_condition.return_value = (True, {})

        # Initialize the trader
        self.trader.initialize()

        # Run a bull pullback scan
        results = self.trader.run_scan("bull_pullbacks")

        # Verify we get results back
        self.assertTrue(len(results) > 0)

        # Verify we attempted to get historical data
        self.assertTrue(self.mock_ib.reqHistoricalData.called)

    @patch("executor.find_option_spread")
    @patch("scans.bull_pullback_condition")
    def test_entry_execution(self, mock_condition, mock_find_spread):
        """Test that entry execution works end-to-end"""
        # Set up condition to return True
        mock_condition.return_value = (True, {})

        # Set up mock option spread
        mock_find_spread.return_value = (
            {"strike": 105, "expiry": datetime.now() + timedelta(days=30), "bid": 1.0, "ask": 1.1},
            {"strike": 110, "expiry": datetime.now() + timedelta(days=30), "bid": 0.5, "ask": 0.6},
            0.5,  # debit
        )

        # Initialize the trader
        self.trader.initialize()

        # Override the trading hours check to always return True
        self.trader._is_entry_time = MagicMock(return_value=True)

        # Run entries
        self.trader.run_entries()

        # Verify we attempted to place an order
        self.assertTrue(self.mock_ib.placeOrder.called)


if __name__ == "__main__":
    unittest.main()
