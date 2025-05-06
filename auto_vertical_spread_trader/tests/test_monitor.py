"""
Unit tests for the monitor module
"""

import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
import numpy as np
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add the parent directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

class TestRiskManagement(unittest.TestCase):
    """Test cases for risk management logic"""
    
    def setUp(self):
        """Set up mock objects for testing"""
        # Create a mock IB connection
        self.mock_ib = MagicMock()
        
        # Mock config with reasonable defaults
        self.config = {
            'STOP_LOSS_ATR_MULT': 1.5,
            'MAX_POSITIONS': 10,
            'MAX_DAILY_TRADES': 2,
        }
        
        # Mock a position for testing
        self.mock_position = self._create_mock_position()
        
        # Patch utility functions
        self.patch_get_stock_data = patch('monitor.get_stock_data')
        self.mock_get_stock_data = self.patch_get_stock_data.start()
        
        # Mock stock data with ATR
        self.mock_stock_data = pd.DataFrame({
            'date': pd.date_range(end=datetime.now(), periods=30),
            'open': np.random.rand(30) * 100 + 100,
            'high': np.random.rand(30) * 100 + 100,
            'low': np.random.rand(30) * 100 + 100,
            'close': np.random.rand(30) * 100 + 100,
            'ATR14': np.random.rand(30) * 5 + 2  # Random ATR values around 2-7
        })
        self.mock_stock_data.set_index('date', inplace=True)
        self.mock_get_stock_data.return_value = self.mock_stock_data
    
    def tearDown(self):
        """Clean up patches after tests"""
        self.patch_get_stock_data.stop()
    
    def _create_mock_position(self):
        """Create a mock position for testing"""
        position = {
            'symbol': 'AAPL',
            'direction': 'bull',  # or 'bear'
            'entry_price': 100.0,
            'entry_date': datetime.now() - timedelta(days=5),
            'stop_price': 95.0,
            'option_spread': {
                'long_strike': 105,
                'short_strike': 110,
                'expiry': datetime.now() + timedelta(days=40),
                'cost': 2.0
            }
        }
        return position
    
    @patch('monitor.check_stop_loss')
    def test_monitor_positions_stop_hit(self, mock_check_stop):
        """Test monitoring positions for stop loss hits"""
        from monitor import monitor_positions
        
        # Set up the mock to indicate stop loss hit
        mock_check_stop.return_value = True
        
        # Run the monitor function with our mock position
        results = monitor_positions(
            self.mock_ib, 
            [self.mock_position], 
            self.config
        )
        
        # Check if the position was flagged for exit
        self.assertTrue(len(results) > 0)
        self.assertEqual(results[0]['symbol'], 'AAPL')
        
    @patch('monitor.check_stop_loss')
    def test_monitor_positions_no_stop(self, mock_check_stop):
        """Test monitoring positions when no stop is hit"""
        from monitor import monitor_positions
        
        # Set up the mock to indicate no stop loss hit
        mock_check_stop.return_value = False
        
        # Run the monitor function with our mock position
        results = monitor_positions(
            self.mock_ib, 
            [self.mock_position], 
            self.config
        )
        
        # Check that no positions were flagged for exit
        self.assertEqual(len(results), 0)
    
    def test_check_stop_loss_hit(self):
        """Test detecting when a stop loss is hit"""
        from monitor import check_stop_loss
        
        # Set current price below stop price
        current_price = 94.0
        stop_price = 95.0
        
        # Test for a long/bull position (stop is hit when price falls below stop)
        result = check_stop_loss(
            current_price,
            stop_price,
            'bull'
        )
        self.assertTrue(result)
        
        # Test for a short/bear position (stop is hit when price rises above stop)
        current_price = 96.0
        result = check_stop_loss(
            current_price,
            stop_price,
            'bear'
        )
        self.assertTrue(result)
    
    def test_check_stop_loss_not_hit(self):
        """Test detecting when a stop loss is not hit"""
        from monitor import check_stop_loss
        
        # Set current price above stop price
        current_price = 96.0
        stop_price = 95.0
        
        # Test for a long/bull position (stop is not hit when price stays above stop)
        result = check_stop_loss(
            current_price,
            stop_price,
            'bull'
        )
        self.assertFalse(result)
        
        # Test for a short/bear position (stop is not hit when price stays below stop)
        current_price = 94.0
        result = check_stop_loss(
            current_price,
            stop_price,
            'bear'
        )
        self.assertFalse(result)
    
    def test_calculate_initial_stop(self):
        """Test calculating the initial stop loss based on ATR"""
        from monitor import calculate_initial_stop
        
        stock_data = self.mock_stock_data
        current_price = 100.0
        direction = 'bull'
        atr_multiple = 1.5
        
        # Get the current ATR
        atr = stock_data['ATR14'].iloc[-1]
        
        # Calculate expected stop price for bull position
        expected_stop = current_price - (atr * atr_multiple)
        
        # Test the function
        result = calculate_initial_stop(
            stock_data, 
            current_price, 
            direction, 
            atr_multiple
        )
        
        # Verify the result
        self.assertAlmostEqual(result, expected_stop, places=2)
        
        # Test for bear position
        direction = 'bear'
        expected_stop = current_price + (atr * atr_multiple)
        
        result = calculate_initial_stop(
            stock_data, 
            current_price, 
            direction, 
            atr_multiple
        )
        
        self.assertAlmostEqual(result, expected_stop, places=2)

if __name__ == '__main__':
    unittest.main() 