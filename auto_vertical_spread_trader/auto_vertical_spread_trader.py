from ib_insync import IB, Stock, Option, ComboLeg, Order, util
import pandas as pd
import pandas_ta as ta
import time
from datetime import datetime
import pytz
import threading
import logging
import csv
from pathlib import Path
from threading import Event
import traceback
import os
import pickle
from typing import Dict, Any, List, Tuple, Optional, Union

# --- CONFIG ---
CONFIG = {
    # Universe filters
    "MIN_MARKET_CAP": 10e9,  # $10 billion minimum market cap
    "MIN_PRICE": 20,  # $20 minimum stock price
    # Technical filters
    "LOOKBACK_DAYS": 60,  # Days of historical data to fetch
    "MIN_VOLUME": 1_000_000,  # Minimum daily volume
    # Option parameters
    "TARGET_EXPIRY_INDEX": 1,  # 0=nearest, 1=next cycle (2-3 weeks)
    "MIN_DELTA": 0.30,  # Minimum absolute delta for long leg
    "MAX_COST": 500,  # Maximum spread cost in dollars
    "MIN_REWARD_RISK_RATIO": 1.0,  # Minimum reward-to-risk ratio
    "MAX_BID_ASK_PCT": 0.15,  # Maximum bid-ask spread as % of mid-price
    # Risk management
    "STOP_LOSS_ATR_MULT": 2.0,  # ATR multiplier for stop-loss
    # Execution
    "SCAN_HOUR_ET": 15,  # Hour to run scans (15 = 3PM ET)
    "MONITOR_INTERVAL_SEC": 60,  # Seconds between stop-loss checks
    "API_SLEEP": 0.1,  # Sleep time between API calls
    # Base patterns
    "HIGH_BASE_MAX_ATR_RATIO": 0.8,  # Max ATR ratio for high/low base
    "PRICE_NEAR_HIGH_PCT": 0.95,  # Price must be within 5% of 52-week high
    "PRICE_NEAR_LOW_PCT": 1.05,  # Price must be within 5% of 52-week low
    "TIGHT_RANGE_FACTOR": 0.8,  # Daily range must be below this % of average
}

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("auto_trader.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# Event flag for clean shutdown
exit_event = Event()

ib = IB()
ib.connect("127.0.0.1", 7497, clientId=99)


# --- 1. Define & filter universe ---
def load_sp500_tickers():
    """
    Load S&P 500 tickers from a local file or download them.
    Returns a list of ticker symbols.
    """
    tickers_file = Path("sp500_tickers.csv")

    # If we already have the file and it's recent (less than 7 days old), use it
    if tickers_file.exists() and (time.time() - tickers_file.stat().st_mtime < 7 * 86400):
        logger.info("Loading S&P 500 tickers from local file")
        with open(tickers_file, "r") as f:
            reader = csv.reader(f)
            return [row[0] for row in reader if row]

    # Otherwise download the list
    try:
        logger.info("Downloading S&P 500 tickers")
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        tables = pd.read_html(url)
        df = tables[0]
        tickers = df["Symbol"].str.replace(".", "-").tolist()

        # Save to file for future use
        with open(tickers_file, "w", newline="") as f:
            writer = csv.writer(f)
            for ticker in tickers:
                writer.writerow([ticker])

        return tickers
    except Exception as e:
        logger.error(f"Error downloading S&P 500 tickers: {e}")
        # Fallback to a minimal list if download fails
        logger.warning("Using fallback ticker list")
        return ["AAPL", "MSFT", "AMZN", "GOOGL", "META", "TSLA", "NVDA", "JPM", "V", "PG"]


universe = load_sp500_tickers()  # your list of S&P500 tickers


def filter_universe(symbols):
    """Filter universe to large cap, liquid, optionable stocks"""
    large = []
    logger.info(f"Filtering universe of {len(symbols)} symbols")

    for sym in symbols:
        try:
            stk = Stock(sym, "SMART", "USD")

            # 1a) market cap
            snap = ib.reqFundamentalData(stk, reportType="ReportSnapshot")
            ib.sleep(CONFIG["API_SLEEP"])

            kv = dict(item.split("=") for item in snap.split(";") if "=" in item)
            cap = float(kv.get("MarketCap", 0))
            if cap < CONFIG["MIN_MARKET_CAP"]:
                continue

            # 1b) price > minimum
            tick = ib.reqMktData(stk, "", False, False)
            ib.sleep(CONFIG["API_SLEEP"])
            price = tick.marketPrice()
            if not price or price <= CONFIG["MIN_PRICE"]:
                continue

            large.append(sym)

        except Exception as e:
            logger.error(f"Error filtering {sym}: {e}")
            continue

    logger.info(f"Filtered down to {len(large)} symbols meeting criteria")
    return large


large_caps = filter_universe(universe)


# --- 2. Fetch bars & indicators ---
def get_tech_df(symbol):
    """
    Get historical bars and calculate technical indicators
    """
    try:
        logger.debug(f"Fetching historical data for {symbol}")
        bars = ib.reqHistoricalData(
            Stock(symbol, "SMART", "USD"),
            endDateTime="",
            durationStr=f'{CONFIG["LOOKBACK_DAYS"]} D',
            barSizeSetting="1 day",
            whatToShow="TRADES",
            useRTH=True,
        )

        if not bars or len(bars) < 50:  # Need at least 50 days for MA50
            logger.warning(f"Insufficient historical data for {symbol}")
            return None

        df = util.df(bars)

        # Use pandas-ta's strategy for bulk processing of indicators
        df.ta.strategy(
            name="VerticalSpreadStrategy",
            ta=[
                {"kind": "sma", "length": 50, "close": "close", "col_names": ("MA50",)},
                {"kind": "atr", "length": 14, "col_names": ("ATR14",)},
            ],
        )

        return df

    except Exception as e:
        logger.error(f"Error getting data for {symbol}: {e}")
        return None


def get_tech_df_cached(symbol):
    """
    Get historical bars and calculate technical indicators with caching
    """
    # Create cache directory if it doesn't exist
    cache_dir = Path("data_cache")
    cache_dir.mkdir(exist_ok=True)

    cache_file = cache_dir / f"{symbol}_{CONFIG['LOOKBACK_DAYS']}.pkl"
    cache_age = time.time() - cache_file.stat().st_mtime if cache_file.exists() else float("inf")

    # Use cache if it exists and is fresh (less than 1 day old)
    if cache_file.exists() and cache_age < 86400:
        try:
            logger.debug(f"Loading cached data for {symbol}")
            with open(cache_file, "rb") as f:
                return pickle.load(f)
        except Exception as e:
            logger.warning(f"Cache load failed for {symbol}: {e}")

    # Otherwise fetch fresh data
    df = get_tech_df(symbol)

    # Cache the result if successful
    if df is not None:
        try:
            with open(cache_file, "wb") as f:
                pickle.dump(df, f)
        except Exception as e:
            logger.warning(f"Cache save failed for {symbol}: {e}")

    return df


# --- 3. Scan functions with volume filter ---
def scan_securities(symbols, scan_name, condition_func):
    """
    Generic scanning function that applies a condition function to each symbol

    Args:
        symbols: List of symbols to scan
        scan_name: Name of the scan for logging
        condition_func: Function that takes a dataframe and returns True/False plus additional data

    Returns:
        List of tuples: (symbol, bar, ATR)
    """
    signals = []
    logger.info(f"Running {scan_name} scan on {len(symbols)} symbols")

    for sym in symbols:
        try:
            df = get_tech_df_cached(sym)  # Use cached version
            if df is None or len(df) < 52:
                continue

            result, data = condition_func(df)
            if result and df.iloc[-1].volume >= CONFIG["MIN_VOLUME"]:
                signals.append((sym, df.iloc[-1], df.ATR14.iloc[-1]))

        except Exception as e:
            logger.error(f"Error in {scan_name} scan for {sym}: {e}")
            continue

    logger.info(f"{scan_name} scan: found {len(signals)} signals")
    return signals


def bull_pullback_condition(df):
    """Bull pullback condition function"""
    today, y1, y2 = df.iloc[-1], df.iloc[-2], df.iloc[-3]

    # Two bullish candles
    two_bullish = y2.close > y2.open and y1.close > y1.open

    # Pullback to rising 50MA
    ma_rising = df.MA50.iloc[-1] > df.MA50.iloc[-2]
    price_at_ma = today.low <= today.MA50

    return (two_bullish and ma_rising and price_at_ma), {}


def bear_rally_condition(df):
    """Bear rally condition function"""
    today, y1, y2 = df.iloc[-1], df.iloc[-2], df.iloc[-3]

    # Two bearish candles
    two_bearish = y2.close < y2.open and y1.close < y1.open

    # Rally into falling 50MA
    ma_falling = df.MA50.iloc[-1] < df.MA50.iloc[-2]
    price_at_ma = today.high >= today.MA50

    return (two_bearish and ma_falling and price_at_ma), {}


def high_base_condition(df):
    """High base condition function (vectorized)"""
    # Calculate additional indicators
    df["52w_high"] = df["close"].rolling(252).max()
    df["ATR_ratio"] = df["ATR14"] / df["ATR14"].rolling(20).mean()
    df["range_pct"] = (df["high"] - df["low"]) / df["close"] * 100

    if len(df) < 20:  # Need at least 20 days for moving averages
        return False, {}

    # Create boolean masks for each condition
    near_highs = df["close"] >= CONFIG["PRICE_NEAR_HIGH_PCT"] * df["52w_high"]
    low_volatility = df["ATR_ratio"] < CONFIG["HIGH_BASE_MAX_ATR_RATIO"]
    tight_range = (
        df["range_pct"] < df["range_pct"].rolling(20).mean() * CONFIG["TIGHT_RANGE_FACTOR"]
    )

    # Combine all conditions
    condition_met = near_highs & low_volatility & tight_range

    # Return result for the last day
    return bool(condition_met.iloc[-1]), {}


def low_base_condition(df):
    """Low base condition function (vectorized)"""
    # Calculate additional indicators
    df["52w_low"] = df["close"].rolling(252).min()
    df["ATR_ratio"] = df["ATR14"] / df["ATR14"].rolling(20).mean()
    df["range_pct"] = (df["high"] - df["low"]) / df["close"] * 100

    if len(df) < 20:  # Need at least 20 days for moving averages
        return False, {}

    # Create boolean masks for each condition
    near_lows = df["close"] <= CONFIG["PRICE_NEAR_LOW_PCT"] * df["52w_low"]
    low_volatility = df["ATR_ratio"] < CONFIG["HIGH_BASE_MAX_ATR_RATIO"]
    tight_range = (
        df["range_pct"] < df["range_pct"].rolling(20).mean() * CONFIG["TIGHT_RANGE_FACTOR"]
    )

    # Combine all conditions
    condition_met = near_lows & low_volatility & tight_range

    # Return result for the last day
    return bool(condition_met.iloc[-1]), {}


def scan_bull_pullbacks(symbols):
    return scan_securities(symbols, "Bull Pullback", bull_pullback_condition)


def scan_bear_rallies(symbols):
    return scan_securities(symbols, "Bear Rally", bear_rally_condition)


def scan_high_base(symbols):
    return scan_securities(symbols, "High Base", high_base_condition)


def scan_low_base(symbols):
    return scan_securities(symbols, "Low Base", low_base_condition)


# --- 4. Spread selector & placer with bidask ≤15% filter ---
def select_and_place(symbol, direction, bar, atr):
    """
    Select and place a vertical spread for the given symbol and direction
    """
    try:
        logger.info(f"Selecting {direction} spread for {symbol}")

        # Get option chain parameters
        try:
            params = ib.reqSecDefOptParams(symbol, "", "STK", Stock(symbol, "SMART", "USD").conId)
            if not params:
                logger.warning(f"No option parameters for {symbol}")
                return

            exp = sorted(params[0].expirations)[CONFIG["TARGET_EXPIRY_INDEX"]]
            strikes = sorted(params[0].strikes)

        except Exception as e:
            logger.error(f"Error fetching option parameters for {symbol}: {e}")
            return

        # Get live underlying price
        try:
            stk = Stock(symbol, "SMART", "USD")
            tick = ib.reqMktData(stk, "", False, False)
            ib.sleep(CONFIG["API_SLEEP"])
            S = tick.marketPrice()
            if not S:
                logger.warning(f"Could not get price for {symbol}")
                return

        except Exception as e:
            logger.error(f"Error getting market data for {symbol}: {e}")
            return

        for k1 in strikes:
            # pick OTM long leg
            if direction in ["bull", "high_base"] and k1 < S:
                continue
            if direction in ["bear", "low_base"] and k1 > S:
                continue

            # wing one strike away
            idx = strikes.index(k1) + (1 if direction in ["bull", "high_base"] else -1)
            if idx < 0 or idx >= len(strikes):
                continue
            k2 = strikes[idx]

            width = abs(k2 - k1)

            optType = "C" if direction in ["bull", "high_base"] else "P"
            longOpt = Option(symbol, exp, k1, optType, "SMART")
            shortOpt = Option(symbol, exp, k2, optType, "SMART")

            # fetch quotes & Greeks
            try:
                t1 = ib.reqMktData(longOpt, "", False, False)
                t2 = ib.reqMktData(shortOpt, "", False, False)
                ib.sleep(CONFIG["API_SLEEP"] * 3)  # Give more time for option data

                if not (t1.modelGreeks and t2.modelGreeks):
                    logger.debug(f"Missing Greeks for {symbol} options")
                    continue

            except Exception as e:
                logger.error(f"Error getting option data for {symbol}: {e}")
                continue

            delta = t1.modelGreeks.delta
            mid1 = (t1.bid + t1.ask) / 2
            mid2 = (t2.bid + t2.ask) / 2

            # Liquidity check: bid-ask ≤ 15% mid
            if t1.bid <= 0 or t1.ask <= 0:
                logger.debug(f"Invalid bid/ask for {symbol} long option")
                continue

            spread_pct1 = (t1.ask - t1.bid) / ((t1.ask + t1.bid) / 2)
            if spread_pct1 > CONFIG["MAX_BID_ASK_PCT"]:
                logger.debug(f"Spread too wide for {symbol} long option: {spread_pct1:.1%}")
                continue

            if t2.bid <= 0 or t2.ask <= 0:
                logger.debug(f"Invalid bid/ask for {symbol} short option")
                continue

            spread_pct2 = (t2.ask - t2.bid) / ((t2.ask + t2.bid) / 2)
            if spread_pct2 > CONFIG["MAX_BID_ASK_PCT"]:
                logger.debug(f"Spread too wide for {symbol} short option: {spread_pct2:.1%}")
                continue

            debit = round((mid1 - mid2) * 100, 2)
            reward = width * 100 - debit

            # delta filter, cost, R≥1:1
            if direction in ["bull", "high_base"] and abs(delta) < CONFIG["MIN_DELTA"]:
                continue
            if direction in ["bear", "low_base"] and abs(delta) < CONFIG["MIN_DELTA"]:
                continue
            if debit > CONFIG["MAX_COST"]:
                continue
            if reward / debit < CONFIG["MIN_REWARD_RISK_RATIO"]:
                continue

            # place the spread
            try:
                combo = Order(
                    orderType="LMT",
                    action="BUY",
                    totalQuantity=1,
                    lmtPrice=debit / 100,
                    tif="GTC",
                    comboLegs=[
                        ComboLeg(longOpt.conId, 1, "BUY"),
                        ComboLeg(shortOpt.conId, 1, "SELL"),
                    ],
                )
                trade = ib.placeOrder(longOpt, combo)
                logger.info(
                    f"Placed {direction} spread for {symbol}: {k1}/{k2} {optType}, cost: ${debit:.2f}"
                )

                # record for stop-loss
                spreadBook[symbol] = {
                    "type": direction,
                    "entryPrice": bar.close,
                    "ATR": atr,
                    "legs": [longOpt, shortOpt],
                    "order": trade,
                }
                break

            except Exception as e:
                logger.error(f"Error placing order for {symbol}: {e}")
                continue

    except Exception as e:
        logger.error(f"Error in select_and_place for {symbol}: {e}")
        traceback.print_exc()
        return


# --- 5. Stop-loss monitor ---
def monitor_stops():
    """
    Monitor open positions for stop-loss violations
    Exits cleanly when exit_event is set
    """
    logger.info("Starting stop-loss monitor thread")

    while not exit_event.is_set():
        try:
            for sym, info in list(spreadBook.items()):
                try:
                    stk = Stock(sym, "SMART", "USD")
                    tick = ib.reqMktData(stk, "", False, False)
                    ib.sleep(CONFIG["API_SLEEP"])
                    cur = tick.marketPrice()

                    if not cur:
                        continue

                    # Calculate stop price
                    stop_diff = CONFIG["STOP_LOSS_ATR_MULT"] * info["ATR"]

                    if (
                        info["type"] in ["bull", "high_base"]
                        and cur <= info["entryPrice"] - stop_diff
                    ):
                        logger.info(f"Stop triggered for {sym} {info['type']} at {cur}")
                        side = "SELL"
                    elif (
                        info["type"] in ["bear", "low_base"]
                        and cur >= info["entryPrice"] + stop_diff
                    ):
                        logger.info(f"Stop triggered for {sym} {info['type']} at {cur}")
                        side = "SELL"
                    else:
                        continue

                    # Close positions
                    for opt in info["legs"]:
                        try:
                            pos = ib.position(opt)
                            if pos and pos.position != 0:
                                close_ord = Order(
                                    orderType="MKT", action=side, totalQuantity=abs(pos.position)
                                )
                                ib.placeOrder(opt, close_ord)
                                logger.info(f"Placed close order for {sym} leg {opt.localSymbol}")
                        except Exception as e:
                            logger.error(
                                f"Error closing position for {sym} leg {opt.localSymbol}: {e}"
                            )

                    spreadBook.pop(sym)

                except Exception as e:
                    logger.error(f"Error monitoring stop for {sym}: {e}")

        except Exception as e:
            logger.error(f"Error in monitor_stops: {e}")

        # Sleep for the monitoring interval
        time.sleep(CONFIG["MONITOR_INTERVAL_SEC"])

    logger.info("Stop-loss monitor thread exiting")


# Start the monitor thread
stop_monitor_thread = threading.Thread(target=monitor_stops, daemon=True)
stop_monitor_thread.start()


# --- 6. Schedule your entry scan at 3 PM ET every trading day ---
spreadBook: Dict[str, Dict[str, Any]] = {}
tz = pytz.timezone("US/Eastern")
lastRunDate = None


def run_entries_if_time():
    """
    Run entry scans if it's time (after 3 PM ET and not already run today)
    """
    global lastRunDate
    now = datetime.now(tz)

    # only once per day, after 3pm ET
    if now.hour >= CONFIG["SCAN_HOUR_ET"] and lastRunDate != now.date():
        try:
            logger.info(f"Running daily entry scans for {now.date()}")
            lastRunDate = now.date()

            # Run all scans
            bulls = scan_bull_pullbacks(large_caps)
            bears = scan_bear_rallies(large_caps)
            high_bases = scan_high_base(large_caps)
            low_bases = scan_low_base(large_caps)

            # Place orders for each scan result
            for sym, bar, atr in bulls:
                select_and_place(sym, "bull", bar, atr)
            for sym, bar, atr in bears:
                select_and_place(sym, "bear", bar, atr)
            for sym, bar, atr in high_bases:
                select_and_place(sym, "high_base", bar, atr)
            for sym, bar, atr in low_bases:
                select_and_place(sym, "low_base", bar, atr)

            logger.info(
                f"Completed scans: found {len(bulls)} bull, {len(bears)} bear, "
                + f"{len(high_bases)} high-base, and {len(low_bases)} low-base spreads."
            )

        except Exception as e:
            logger.error(f"Error in run_entries_if_time: {e}")
            traceback.print_exc()


# --- 7. Main loop ---
logger.info("Scheduler started; will enter trades after 3 PM ET each trading day.")

try:
    while not exit_event.is_set():
        try:
            # Check connection status
            if not ib.isConnected():
                logger.error("IB connection lost. Attempting to reconnect...")
                try:
                    ib.connect("127.0.0.1", 7497, clientId=99)
                    logger.info("Reconnected to IB")
                except Exception as e:
                    logger.error(f"Failed to reconnect: {e}")
                    time.sleep(60)  # Wait before retrying
                    continue

            # Run entry scan if it's time
            run_entries_if_time()

            # Wait for next check
            time.sleep(60)

        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            time.sleep(60)  # Continue despite errors

except KeyboardInterrupt:
    logger.info("Stop signal received. Shutting down...")
    exit_event.set()  # Signal threads to exit
    logger.info("Waiting for monitor thread to exit...")
    stop_monitor_thread.join(timeout=10)  # Wait for monitor thread with timeout
    ib.disconnect()
    logger.info("Disconnected from IB. Exiting.")


# Create the main class for importing in tests and applications
class AutoVerticalSpreadTrader:
    """
    Main trader class for vertical spread trading strategies
    """
    
    def __init__(self, config_overrides: Optional[Dict[str, Any]] = None):
        """
        Initialize the trader with optional configuration overrides
        
        Args:
            config_overrides: Optional dictionary of configuration overrides
        """
        # Apply configuration overrides if provided
        self.config = CONFIG.copy()
        if config_overrides:
            self.config.update(config_overrides)
            
        self.ib = None
        self.spreadBook: Dict[str, Dict[str, Any]] = {}
        self.stop_monitor_thread = None
        self.exit_event = Event()
        self.large_caps = []
        self.lastRunDate = None
        self.tz = pytz.timezone("US/Eastern")
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[logging.FileHandler("auto_trader.log"), logging.StreamHandler()],
        )
        self.logger = logging.getLogger(__name__)
        
    def initialize(self):
        """
        Initialize the trader, connect to IB, and setup the universe
        """
        self.logger.info("Initializing trader...")
        
        # Connect to IB
        self.ib = IB()
        self.ib.connect(
            self.config["IB_HOST"],
            self.config["IB_PORT"],
            clientId=self.config["IB_CLIENT_ID"]
        )
        
        # Load universe and filter
        universe = self._load_universe()
        self.large_caps = self._filter_universe(universe)
        
        # Start the monitor thread
        self.exit_event = Event()
        self.stop_monitor_thread = threading.Thread(target=self._monitor_stops, daemon=True)
        self.stop_monitor_thread.start()
        
        self.logger.info("Trader initialized")
        return True
        
    def _load_universe(self) -> List[str]:
        """Load trading universe"""
        # For now, use the existing function
        return load_sp500_tickers()
    
    def _filter_universe(self, symbols: List[str]) -> List[str]:
        """Filter universe to large cap, liquid stocks"""
        # For now, use the existing function
        return filter_universe(symbols)
    
    def run_scan(self, scan_type: str) -> List[Tuple[str, Any, float]]:
        """
        Run a scan for the given scan type
        
        Args:
            scan_type: Type of scan to run (bull_pullbacks, bear_rallies, high_base, low_base)
            
        Returns:
            List of tuples with signal data: (symbol, bar, ATR)
        """
        if scan_type == "bull_pullbacks":
            return scan_bull_pullbacks(self.large_caps)
        elif scan_type == "bear_rallies":
            return scan_bear_rallies(self.large_caps)
        elif scan_type == "high_base":
            return scan_high_base(self.large_caps)
        elif scan_type == "low_base":
            return scan_low_base(self.large_caps)
        else:
            self.logger.error(f"Unknown scan type: {scan_type}")
            return []
    
    def _is_entry_time(self) -> bool:
        """
        Check if it's time to enter trades (after configured hour in ET)
        """
        now = datetime.now(self.tz)
        return now.hour >= self.config["SCAN_HOUR_ET"]
    
    def run_entries(self):
        """
        Run entry scans and place trades
        """
        try:
            if not self._is_entry_time():
                self.logger.info("Not entry time yet, skipping scans")
                return

            self.logger.info(f"Running entry scans")
            self.lastRunDate = datetime.now(self.tz).date()

            # Run all scans
            bulls = scan_bull_pullbacks(self.large_caps)
            bears = scan_bear_rallies(self.large_caps)
            high_bases = scan_high_base(self.large_caps)
            low_bases = scan_low_base(self.large_caps)

            # Place orders for each scan result
            for sym, bar, atr in bulls:
                select_and_place(sym, "bull", bar, atr)
            for sym, bar, atr in bears:
                select_and_place(sym, "bear", bar, atr)
            for sym, bar, atr in high_bases:
                select_and_place(sym, "high_base", bar, atr)
            for sym, bar, atr in low_bases:
                select_and_place(sym, "low_base", bar, atr)

            self.logger.info(
                f"Completed scans: found {len(bulls)} bull, {len(bears)} bear, "
                + f"{len(high_bases)} high-base, and {len(low_bases)} low-base spreads."
            )

        except Exception as e:
            self.logger.error(f"Error in run_entries: {e}")
            traceback.print_exc()
    
    def _monitor_stops(self):
        """
        Monitor open positions for stop-loss violations
        Exits cleanly when exit_event is set
        """
        # For now, use a wrapper around the existing function 
        monitor_stops()
        
    def shutdown(self):
        """
        Shutdown the trader cleanly
        """
        self.logger.info("Shutting down trader...")
        self.exit_event.set()  # Signal threads to exit
        
        if self.stop_monitor_thread:
            self.logger.info("Waiting for monitor thread to exit...")
            self.stop_monitor_thread.join(timeout=10)
            
        if self.ib and self.ib.isConnected():
            self.ib.disconnect()
            self.logger.info("Disconnected from IB")
            
        self.logger.info("Trader shutdown complete")
        
