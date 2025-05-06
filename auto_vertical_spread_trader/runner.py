"""
Main runner module for the auto vertical spread trader.
Handles IB connection, trading schedule, and clean shutdown.
"""

import logging
import time
import traceback
import smtplib
import datetime
import pytz
from email.mime.text import MIMEText
from threading import Event

from ib_insync import IB, util
util.patchAsyncio()  # To avoid asyncio conflicts

from config import CONFIG
import universe
import scans
import executor
from monitor import StopLossMonitor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("auto_trader.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AutoVerticalSpreadTrader:
    """
    Main trader class that orchestrates the entire trading process
    """
    
    def __init__(self, config=CONFIG):
        """
        Initialize the trader
        
        Args:
            config (dict): Configuration dictionary
        """
        self.config = config
        self.ib = IB()
        self.exit_event = Event()
        self.spread_book = {}
        self.last_run_date = None
        self.universe = []
        self.filtered_universe = []
        self.monitor = None
        self.tz = pytz.timezone('US/Eastern')
        
    def connect(self):
        """
        Connect to IB with retry
        
        Returns:
            bool: True if connected, False otherwise
        """
        for attempt in range(3):
            try:
                if not self.ib.isConnected():
                    self.ib.connect(
                        self.config['IB_HOST'], 
                        self.config['IB_PORT'], 
                        clientId=self.config['IB_CLIENT_ID']
                    )
                    logger.info(f"Connected to IB on {self.config['IB_HOST']}:{self.config['IB_PORT']}")
                return True
            except Exception as e:
                logger.error(f"Connection attempt {attempt+1} failed: {e}")
                if attempt < 2:
                    time.sleep(5)
                    
        logger.critical("Could not connect to IB after multiple attempts")
        return False
        
    def initialize(self):
        """
        Initialize the trader
        - Connect to IB
        - Load universe
        - Start monitor thread
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            # Connect to IB
            if not self.connect():
                return False
                
            # Load universe
            self.universe = universe.load_sp500_tickers()
            logger.info(f"Loaded universe with {len(self.universe)} symbols")
            
            # Filter universe
            self.filtered_universe = universe.filter_universe(self.ib, self.universe, self.config)
            
            # Initialize stop-loss monitor
            self.monitor = StopLossMonitor(self.ib, self.spread_book, self.config, self.exit_event)
            self.monitor.start()
            
            return True
            
        except Exception as e:
            logger.critical(f"Initialization failed: {e}")
            traceback.print_exc()
            return False
            
    def run_entries_if_time(self):
        """
        Run entry scans if it's time (after configured hour ET and not already run today)
        
        Returns:
            bool: True if scans were run, False otherwise
        """
        now = datetime.datetime.now(self.tz)
        
        # Only once per day, after configured hour ET
        if now.hour >= self.config['SCAN_HOUR_ET'] and self.last_run_date != now.date():
            try:
                logger.info(f"Running daily entry scans for {now.date()}")
                self.last_run_date = now.date()
                
                # Refresh filtered universe once per day
                self.filtered_universe = universe.filter_universe(self.ib, self.universe, self.config)
                
                # Check if we're at position limit
                if len(self.spread_book) >= self.config['MAX_POSITIONS']:
                    logger.warning(f"Position limit reached ({len(self.spread_book)}/{self.config['MAX_POSITIONS']}). Skipping scan.")
                    return False
                
                # Run all scans
                bulls = scans.scan_bull_pullbacks(self.ib, self.filtered_universe, self.config)
                bears = scans.scan_bear_rallies(self.ib, self.filtered_universe, self.config)
                high_bases = scans.scan_high_base(self.ib, self.filtered_universe, self.config)
                low_bases = scans.scan_low_base(self.ib, self.filtered_universe, self.config)
                
                # Combine all signals and limit total entries
                all_signals = []
                for sym, bar, atr in bulls:
                    all_signals.append(('bull', sym, bar, atr))
                for sym, bar, atr in bears:
                    all_signals.append(('bear', sym, bar, atr))
                for sym, bar, atr in high_bases:
                    all_signals.append(('high_base', sym, bar, atr))
                for sym, bar, atr in low_bases:
                    all_signals.append(('low_base', sym, bar, atr))
                    
                # Limit number of new trades per day
                space_available = min(
                    self.config['MAX_DAILY_TRADES'],
                    self.config['MAX_POSITIONS'] - len(self.spread_book)
                )
                
                if space_available <= 0:
                    logger.info(f"No space for new trades. Current positions: {len(self.spread_book)}")
                    return True
                    
                # Prioritize signals: try to get a mix of strategies
                if len(all_signals) > space_available:
                    all_signals = all_signals[:space_available]
                    
                # Place orders
                trades_placed = 0
                for direction, sym, bar, atr in all_signals:
                    # Skip if symbol is already in the book
                    if sym in self.spread_book:
                        continue
                        
                    # Place trade
                    if executor.select_and_place(self.ib, sym, direction, bar, atr, self.config, self.spread_book):
                        trades_placed += 1
                        
                    # Check if we've reached the daily limit
                    if trades_placed >= space_available:
                        break
                        
                # Log summary
                logger.info(f"Completed scans: found {len(bulls)} bull, {len(bears)} bear, " +
                           f"{len(high_bases)} high_base, and {len(low_bases)} low_base signals")
                logger.info(f"Placed {trades_placed} new trades. Total positions: {len(self.spread_book)}")
                
                # Send email alert if configured
                if self.config['ENABLE_EMAIL_ALERTS'] and trades_placed > 0:
                    self._send_email_alert(
                        "Auto Trader: New trades placed", 
                        f"Placed {trades_placed} new trades on {now.date()}.\n"
                        f"Current positions: {len(self.spread_book)}"
                    )
                    
                return True
                           
            except Exception as e:
                logger.error(f"Error in run_entries_if_time: {e}")
                traceback.print_exc()
                return False
                
        return False
        
    def _send_email_alert(self, subject, body):
        """
        Send email alert
        
        Args:
            subject (str): Email subject
            body (str): Email body
        """
        if not self.config['ENABLE_EMAIL_ALERTS']:
            return
            
        try:
            msg = MIMEText(body)
            msg['Subject'] = subject
            msg['From'] = self.config['EMAIL_FROM']
            msg['To'] = self.config['EMAIL_TO']
            
            server = smtplib.SMTP(self.config['EMAIL_SERVER'], self.config['EMAIL_PORT'])
            server.starttls()
            server.login(self.config['EMAIL_FROM'], self.config['EMAIL_PASSWORD'])
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Sent email alert: {subject}")
            
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
            
    def main_loop(self):
        """
        Main trading loop
        """
        logger.info("Starting main loop")
        
        while not self.exit_event.is_set():
            try:
                # Check connection status
                if not self.ib.isConnected():
                    logger.error("IB connection lost. Attempting to reconnect...")
                    if not self.connect():
                        time.sleep(60)  # Wait before retrying
                        continue
                    
                # Run entry scan if it's time
                self.run_entries_if_time()
                
                # Wait for next check
                time.sleep(self.config['MAIN_LOOP_INTERVAL'])
                
            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received. Shutting down...")
                self.shutdown()
                break
                
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(60)  # Continue despite errors
                
        logger.info("Main loop exited")
            
    def shutdown(self):
        """
        Shut down the trader
        - Signal threads to exit
        - Disconnect from IB
        """
        logger.info("Shutting down trader...")
        self.exit_event.set()
        
        if self.monitor:
            self.monitor.stop()
            
        if self.ib.isConnected():
            self.ib.disconnect()
            logger.info("Disconnected from IB")
            
        logger.info("Shutdown complete")
        
def main():
    """
    Main entry point for the application
    """
    logger.info("=== Auto Vertical Spread Trader Starting ===")
    trader = AutoVerticalSpreadTrader()
    
    if trader.initialize():
        try:
            trader.main_loop()
        except Exception as e:
            logger.critical(f"Unhandled error in main loop: {e}")
            traceback.print_exc()
        finally:
            trader.shutdown()
    else:
        logger.critical("Initialization failed. Exiting.")
        
    logger.info("=== Auto Vertical Spread Trader Stopped ===")
    
if __name__ == "__main__":
    main() 