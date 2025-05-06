"""
Monitor module for handling stop-loss management.
Tracks open positions and closes them based on ATR-based stops or profit targets.
"""

import logging
import time
import threading
from ib_insync import Stock, Order
from executor import retry_api_call

logger = logging.getLogger(__name__)

class StopLossMonitor:
    """
    Stop-loss monitor class that runs in a separate thread to monitor positions
    """
    
    def __init__(self, ib, spread_book, config, exit_event):
        """
        Initialize the stop-loss monitor
        
        Args:
            ib: IB connection object
            spread_book (dict): Dictionary tracking open spreads
            config (dict): Configuration dictionary
            exit_event (Event): Threading event for clean shutdown
        """
        self.ib = ib
        self.spread_book = spread_book
        self.config = config
        self.exit_event = exit_event
        self.thread = None
        self.trades_closed = 0
        self.max_loss = 0
        self.profits_taken = 0
        self.total_profit_pct = 0
        
    def start(self):
        """
        Start the monitoring thread
        """
        if self.thread is None or not self.thread.is_alive():
            self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.thread.start()
            logger.info("Started stop-loss monitor thread")
            
    def stop(self, timeout=10):
        """
        Stop the monitoring thread
        
        Args:
            timeout (float): Maximum time to wait for thread to exit
            
        Returns:
            bool: True if thread exited cleanly, False if timed out
        """
        if self.thread and self.thread.is_alive():
            self.exit_event.set()
            self.thread.join(timeout)
            if self.thread.is_alive():
                logger.warning("Stop-loss monitor thread did not exit within timeout")
                return False
            else:
                logger.info("Stop-loss monitor thread exited cleanly")
                return True
        return True
        
    def _monitor_loop(self):
        """
        Main monitoring loop
        Runs until exit_event is set
        """
        logger.info("Stop-loss monitor thread started")
        
        while not self.exit_event.is_set():
            try:
                self._check_all_positions()
                
                # Sleep for the monitoring interval
                time.sleep(self.config['MONITOR_INTERVAL_SEC'])
                
            except Exception as e:
                logger.error(f"Error in stop-loss monitor loop: {e}")
                time.sleep(5)  # Short sleep on error
                
        logger.info("Stop-loss monitor thread exiting")
        
    def _check_all_positions(self):
        """Check all positions for stop-loss violations or profit targets"""
        for sym, info in list(self.spread_book.items()):
            try:
                self._check_position(sym, info)
            except Exception as e:
                logger.error(f"Error checking position for {sym}: {e}")
                
    def _check_position(self, symbol, info):
        """
        Check a single position for stop-loss violations or profit targets
        
        Args:
            symbol (str): Symbol to check
            info (dict): Position information from spread_book
        """
        # Add symbol to the info dict for easier logging
        if 'symbol' not in info:
            info['symbol'] = symbol
            
        # Add config to info dict for easier access
        if 'config' not in info:
            info['config'] = self.config
            
        # Get current price with retry
        def get_current_price():
            stk = Stock(symbol, 'SMART', 'USD')
            tick = self.ib.reqMktData(stk, '', False, False)
            self.ib.sleep(self.config['API_SLEEP'])
            return tick.marketPrice()
            
        cur = retry_api_call(get_current_price, max_retries=3, ib=self.ib)
        
        if not cur:
            logger.warning(f"Could not get current price for {symbol}")
            return
            
        # Check for exit conditions
        exit_reason = self._check_exit_conditions(symbol, info, cur)
            
        # If no exit triggered, update trailing stop if enabled
        if exit_reason is None:
            if self.config['TRAILING_STOP_ENABLED'] and 'trailing_stop_price' in info:
                self._update_trailing_stop(symbol, info, cur)
            return
        
        # Exit the position
        if self._exit_position(symbol, info, exit_reason, cur):
            # Remove from spread book
            self.spread_book.pop(symbol)
            
    def _check_exit_conditions(self, symbol, info, current_price):
        """
        Check if any exit conditions are met
        
        Args:
            symbol (str): Symbol to check
            info (dict): Position information
            current_price (float): Current price of the underlying
            
        Returns:
            str or None: Exit reason ('stop_loss', 'profit_target', 'trailing_stop') or None
        """
        direction = info['type']
        entry_price = info['entryPrice']
        
        # Check stop loss
        stop_diff = self.config['STOP_LOSS_ATR_MULT'] * info['ATR']
        
        # Check stop loss conditions
        if direction in ['bull', 'high_base'] and current_price <= entry_price - stop_diff:
            logger.info(f"Stop-loss triggered for {symbol} {direction} at {current_price:.2f}")
            return "stop_loss"
        elif direction in ['bear', 'low_base'] and current_price >= entry_price + stop_diff:
            logger.info(f"Stop-loss triggered for {symbol} {direction} at {current_price:.2f}")
            return "stop_loss"
        
        # Check profit target if it exists
        if 'price_target' in info:
            if direction in ['bull', 'high_base'] and current_price >= info['price_target']:
                logger.info(f"Profit target reached for {symbol} {direction} at {current_price:.2f} "
                           f"({info['target_type']})")
                
                # If trailing stops enabled, start tracking high price
                if self.config['TRAILING_STOP_ENABLED']:
                    info['trailing_stop_price'] = current_price - (info['ATR'] * self.config['TRAILING_STOP_BUFFER'])
                    info['trailing_high'] = current_price
                    logger.info(f"Enabling trailing stop for {symbol} at {info['trailing_stop_price']:.2f}")
                    return None  # Don't exit yet, use trailing stop
                return "profit_target"
                
            elif direction in ['bear', 'low_base'] and current_price <= info['price_target']:
                logger.info(f"Profit target reached for {symbol} {direction} at {current_price:.2f} "
                           f"({info['target_type']})")
                
                # If trailing stops enabled, start tracking low price
                if self.config['TRAILING_STOP_ENABLED']:
                    info['trailing_stop_price'] = current_price + (info['ATR'] * self.config['TRAILING_STOP_BUFFER'])
                    info['trailing_low'] = current_price
                    logger.info(f"Enabling trailing stop for {symbol} at {info['trailing_stop_price']:.2f}")
                    return None  # Don't exit yet, use trailing stop
                return "profit_target"
        
        # Check trailing stop if active
        if 'trailing_stop_price' in info:
            if direction in ['bull', 'high_base'] and current_price <= info['trailing_stop_price']:
                logger.info(f"Trailing stop triggered for {symbol} {direction} at {current_price:.2f}")
                return "trailing_stop"
            elif direction in ['bear', 'low_base'] and current_price >= info['trailing_stop_price']:
                logger.info(f"Trailing stop triggered for {symbol} {direction} at {current_price:.2f}")
                return "trailing_stop"
                
        return None
        
    def _update_trailing_stop(self, symbol, info, current_price):
        """
        Update trailing stop level as price moves in favor
        
        Args:
            symbol (str): Symbol to check
            info (dict): Position information
            current_price (float): Current price of the underlying
        """
        direction = info['type']
        
        # Update trailing stop for bullish positions when price makes new high
        if direction in ['bull', 'high_base'] and current_price > info.get('trailing_high', 0):
            info['trailing_high'] = current_price
            info['trailing_stop_price'] = current_price - (info['ATR'] * self.config['TRAILING_STOP_BUFFER'])
            logger.debug(f"Updated trailing stop for {symbol} to {info['trailing_stop_price']:.2f}")
            
        # Update trailing stop for bearish positions when price makes new low
        elif direction in ['bear', 'low_base'] and current_price < info.get('trailing_low', float('inf')):
            info['trailing_low'] = current_price
            info['trailing_stop_price'] = current_price + (info['ATR'] * self.config['TRAILING_STOP_BUFFER'])
            logger.debug(f"Updated trailing stop for {symbol} to {info['trailing_stop_price']:.2f}")
            
    def _exit_position(self, symbol, info, exit_reason, current_price):
        """
        Exit the position by placing orders to close all legs
        
        Args:
            symbol (str): Symbol to exit
            info (dict): Position information
            exit_reason (str): Reason for exit
            current_price (float): Current price of the underlying
            
        Returns:
            bool: True if exit was successful, False otherwise
        """
        # Always SELL to close long positions (we're always buying spreads)
        side = 'SELL'
        
        # Close positions
        success = True
        for opt in info['legs']:
            try:
                pos = self.ib.position(opt)
                if pos and pos.position != 0:
                    close_ord = Order(orderType='MKT', action=side,
                                     totalQuantity=abs(pos.position))
                    self.ib.placeOrder(opt, close_ord)
                    logger.info(f"Placed close order for {symbol} leg {opt.localSymbol}")
            except Exception as e:
                logger.error(f"Error closing position for {symbol} leg {opt.localSymbol}: {e}")
                success = False
                
        if success:
            # Calculate and log P&L
            entry_price = info['entryPrice']
            if exit_reason == "stop_loss":
                loss_pct = (abs(current_price - entry_price) / entry_price) * 100
                logger.info(f"Closed {symbol} {info['type']} spread with {loss_pct:.1f}% loss")
                self.trades_closed += 1
                self.max_loss = max(self.max_loss, loss_pct)
            else:  # profit_target or trailing_stop
                gain_pct = (abs(current_price - entry_price) / entry_price) * 100
                logger.info(f"Closed {symbol} {info['type']} spread with {gain_pct:.1f}% gain ({exit_reason})")
                self.trades_closed += 1
                self.profits_taken += 1
                self.total_profit_pct += gain_pct
            
        return success
            
    def get_stats(self):
        """
        Get monitoring statistics
        
        Returns:
            dict: Dictionary with monitoring statistics
        """
        avg_profit = self.total_profit_pct / max(1, self.profits_taken)
        return {
            'trades_closed': self.trades_closed,
            'profits_taken': self.profits_taken,
            'max_loss_pct': self.max_loss,
            'avg_profit_pct': avg_profit,
            'active_positions': len(self.spread_book),
            'win_rate': (self.profits_taken / max(1, self.trades_closed)) * 100
        } 