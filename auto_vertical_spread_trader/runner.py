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
import argparse
import os
import shutil

from ib_insync import IB, util
util.patchAsyncio()  # To avoid asyncio conflicts

from auto_vertical_spread_trader.config import CONFIG
import universe
import scans
import auto_vertical_spread_trader.executor as executor
from auto_vertical_spread_trader.monitor import StopLossMonitor

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
    
    def __init__(self, config=CONFIG, use_cache=True, parallel=True, max_workers=4, paper_trading=False):
        """
        Initialize the trader
        
        Args:
            config (dict): Configuration dictionary
            use_cache (bool): Whether to use data caching
            parallel (bool): Whether to use parallel processing
            max_workers (int): Number of workers for parallel processing
            paper_trading (bool): Whether to use paper trading
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
        self.use_cache = use_cache
        self.parallel = parallel
        self.max_workers = max_workers
        self.paper_trading = paper_trading
        
        # Override config for paper trading
        if paper_trading:
            self.config['IB_PORT'] = 7497  # TWS Paper Trading port
            logger.info("Using paper trading mode")
        
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

    def clear_cache(self):
        """
        Clear the data cache directory
        """
        cache_dir = os.path.join(os.getcwd(), "data_cache")
        if os.path.exists(cache_dir):
            logger.info(f"Clearing cache directory: {cache_dir}")
            try:
                shutil.rmtree(cache_dir)
                os.makedirs(cache_dir)
                logger.info("Cache cleared successfully")
            except Exception as e:
                logger.error(f"Error clearing cache: {e}")
        else:
            logger.info("No cache directory found")
            
    def run_scan(self, scan_type, symbols=None):
        """
        Run a specific scan without trading
        
        Args:
            scan_type (str): Scan type ('bull_pullbacks', 'bear_rallies', 'high_base', 'low_base', 'all')
            symbols (list): Optional list of symbols to scan (defaults to filtered universe)
            
        Returns:
            dict: Scan results by type
        """
        if not self.ib.isConnected() and not self.connect():
            logger.error("Cannot run scan: not connected to IB")
            return {}
            
        symbols_to_scan = symbols if symbols else self.filtered_universe
        logger.info(f"Running {scan_type} scan on {len(symbols_to_scan)} symbols")
        
        results = {}
        
        if scan_type in ['bull_pullbacks', 'all']:
            results['bull_pullbacks'] = scans.scan_bull_pullbacks(
                self.ib, 
                symbols_to_scan, 
                self.config, 
                parallel=self.parallel, 
                max_workers=self.max_workers
            )
            
        if scan_type in ['bear_rallies', 'all']:
            results['bear_rallies'] = scans.scan_bear_rallies(
                self.ib, 
                symbols_to_scan, 
                self.config,
                parallel=self.parallel, 
                max_workers=self.max_workers
            )
            
        if scan_type in ['high_base', 'all']:
            results['high_base'] = scans.scan_high_base(
                self.ib, 
                symbols_to_scan, 
                self.config,
                parallel=self.parallel, 
                max_workers=self.max_workers
            )
            
        if scan_type in ['low_base', 'all']:
            results['low_base'] = scans.scan_low_base(
                self.ib, 
                symbols_to_scan, 
                self.config,
                parallel=self.parallel, 
                max_workers=self.max_workers
            )
            
        # Log results
        for scan_name, scan_results in results.items():
            logger.info(f"Found {len(scan_results)} signals for {scan_name}")
            
        return results
            
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
                
                # Run all scans using our optimized functions
                all_signals = []
                
                # Run the scans
                scan_results = self.run_scan('all')
                
                # Combine all signals and limit total entries
                for scan_type, signals in scan_results.items():
                    for sym, bar, atr in signals:
                        all_signals.append((scan_type, sym, bar, atr))
                    
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
                logger.info(f"Completed scans: total signals found: {len(all_signals)}")
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

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Auto Vertical Spread Trader')
    
    # Trading mode
    parser.add_argument('--paper', action='store_true', help='Use paper trading mode')
    
    # Scan options
    parser.add_argument('--scan', choices=['bull_pullbacks', 'bear_rallies', 'high_base', 'low_base', 'all'], 
                        help='Run specific scan without trading')
    parser.add_argument('--symbols', help='Comma-separated list of symbols to scan instead of S&P 500')
    
    # Performance options
    parser.add_argument('--no-cache', action='store_true', help='Disable data caching')
    parser.add_argument('--clear-cache', action='store_true', help='Clear data cache before starting')
    parser.add_argument('--no-parallel', action='store_true', help='Disable parallel processing')
    parser.add_argument('--workers', type=int, default=4, help='Number of parallel workers (default: 4)')
    
    # Logging
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    return parser.parse_args()
        
def main():
    """
    Main entry point for the application
    """
    # Parse command line arguments
    args = parse_args()
    
    # Configure logging
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        
    logger.info("=== Auto Vertical Spread Trader Starting ===")
    
    # Initialize trader with options from command line
    trader = AutoVerticalSpreadTrader(
        use_cache=not args.no_cache,
        parallel=not args.no_parallel,
        max_workers=args.workers,
        paper_trading=args.paper
    )
    
    # Clear cache if requested
    if args.clear_cache:
        trader.clear_cache()
    
    # Initialize the trader
    if trader.initialize():
        try:
            # If scan mode is enabled, run the scan and exit
            if args.scan:
                symbols = args.symbols.split(',') if args.symbols else None
                results = trader.run_scan(args.scan, symbols)
                
                # Display scan results
                for scan_type, signals in results.items():
                    print(f"\n{scan_type.upper()} SCAN RESULTS ({len(signals)} signals):")
                    for i, (symbol, bar, atr) in enumerate(signals):
                        print(f"{i+1}. {symbol}: Close=${bar.close:.2f}, ATR=${atr:.2f}")
                
                # Don't enter the main loop in scan-only mode
                trader.shutdown()
                return
            
            # Otherwise, enter the main trading loop
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