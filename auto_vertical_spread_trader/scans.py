"""
Scan module for technical analysis conditions.
Provides a unified framework for scanning stocks based on technical criteria.
"""

import logging
import pandas as pd
import pandas_ta as ta
from ib_insync import Stock, util
import os
import pickle
from pathlib import Path
import time
from concurrent.futures import ProcessPoolExecutor
import functools

logger = logging.getLogger(__name__)

def get_tech_df_cached(ib, symbol, config):
    """
    Get historical bars and calculate technical indicators with caching
    
    Args:
        ib: IB connection object
        symbol (str): Ticker symbol
        config (dict): Configuration dictionary
        
    Returns:
        DataFrame: Pandas DataFrame with price data and indicators, or None if error
    """
    # Create cache directory if it doesn't exist
    cache_dir = Path("data_cache")
    cache_dir.mkdir(exist_ok=True)
    
    cache_file = cache_dir / f"{symbol}_{config['LOOKBACK_DAYS']}.pkl"
    cache_age = time.time() - cache_file.stat().st_mtime if cache_file.exists() else float('inf')
    
    # Use cache if it exists and is fresh (less than 1 day old)
    if cache_file.exists() and cache_age < 86400:
        try:
            logger.debug(f"Loading cached data for {symbol}")
            with open(cache_file, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            logger.warning(f"Cache load failed for {symbol}: {e}")
    
    # Otherwise fetch fresh data
    df = get_tech_df(ib, symbol, config)
    
    # Cache the result if successful
    if df is not None:
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(df, f)
        except Exception as e:
            logger.warning(f"Cache save failed for {symbol}: {e}")
    
    return df

def get_tech_df(ib, symbol, config):
    """
    Get historical bars and calculate technical indicators
    
    Args:
        ib: IB connection object
        symbol (str): Ticker symbol
        config (dict): Configuration dictionary
        
    Returns:
        DataFrame: Pandas DataFrame with price data and indicators, or None if error
        
    Notes:
        - Calculates standard indicators (MA50, ATR14)
        - Returns None if insufficient data
    """
    try:
        logger.debug(f"Fetching historical data for {symbol}")
        bars = ib.reqHistoricalData(
            Stock(symbol, 'SMART', 'USD'),
            endDateTime='',
            durationStr=f'{config["LOOKBACK_DAYS"]} D',
            barSizeSetting='1 day',
            whatToShow='TRADES',
            useRTH=True)
        
        if not bars or len(bars) < 50:  # Need at least 50 days for MA50
            logger.warning(f"Insufficient historical data for {symbol}")
            return None
            
        df = util.df(bars)
        
        # Calculate all indicators at once using pandas-ta strategy
        df.ta.strategy(
            name="VerticalSpreadStrategy",
            ta=[
                {"kind": "sma", "length": 50, "close": "close", "col_names": ("MA50",)},
                {"kind": "atr", "length": 14, "col_names": ("ATR14",)}
            ]
        )
        
        # Pre-calculate indicators for high/low base patterns
        df['52w_high'] = df['close'].rolling(252).max()
        df['52w_low'] = df['close'].rolling(252).min()
        df['ATR_ratio'] = df['ATR14'] / df['ATR14'].rolling(20).mean()
        df['range_pct'] = (df['high'] - df['low']) / df['close'] * 100
        df['range_ratio'] = df['range_pct'] / df['range_pct'].rolling(20).mean()
        
        return df
        
    except Exception as e:
        logger.error(f"Error getting data for {symbol}: {e}")
        return None

def process_symbol(sym, ib, scan_name, condition_func, config):
    """Process a single symbol for scanning"""
    try:
        df = get_tech_df_cached(ib, sym, config)
        if df is None or len(df) < 52:
            return None
        
        result, data = condition_func(df)
        if result and df.iloc[-1].volume >= config['MIN_VOLUME']:
            return (sym, df.iloc[-1], df.ATR14.iloc[-1])
    except Exception as e:
        logger.error(f"Error in {scan_name} scan for {sym}: {e}")
    return None

def scan_securities_parallel(ib, symbols, scan_name, condition_func, config, max_workers=4):
    """
    Generic scanning function that applies a condition function to each symbol in parallel
    
    Args:
        ib: IB connection object
        symbols (list): List of symbols to scan
        scan_name (str): Name of the scan for logging
        condition_func (callable): Function that takes a dataframe and returns True/False plus additional data
        config (dict): Configuration dictionary
        max_workers (int): Number of parallel processes to use
        
    Returns:
        list: List of tuples: (symbol, bar, ATR)
    """
    logger.info(f"Running {scan_name} scan on {len(symbols)} symbols using {max_workers} processes")
    
    # Create a partial function with fixed parameters
    process_func = functools.partial(process_symbol, ib=ib, scan_name=scan_name, condition_func=condition_func, config=config)
    
    # Process symbols in parallel
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(process_func, symbols))
    
    # Filter out None results
    signals = [r for r in results if r is not None]
    logger.info(f"{scan_name} scan: found {len(signals)} signals")
    return signals

def scan_securities(ib, symbols, scan_name, condition_func, config):
    """
    Generic scanning function that applies a condition function to each symbol (sequential version)
    
    Args:
        ib: IB connection object
        symbols (list): List of symbols to scan
        scan_name (str): Name of the scan for logging
        condition_func (callable): Function that takes a dataframe and returns True/False plus additional data
        config (dict): Configuration dictionary
        
    Returns:
        list: List of tuples: (symbol, bar, ATR)
    """
    signals = []
    logger.info(f"Running {scan_name} scan on {len(symbols)} symbols")
    
    for sym in symbols:
        try:
            df = get_tech_df_cached(ib, sym, config)
            if df is None or len(df) < 52:
                continue
                
            result, data = condition_func(df)
            if result and df.iloc[-1].volume >= config['MIN_VOLUME']:
                signals.append((sym, df.iloc[-1], df.ATR14.iloc[-1]))
                
        except Exception as e:
            logger.error(f"Error in {scan_name} scan for {sym}: {e}")
            continue
            
    logger.info(f"{scan_name} scan: found {len(signals)} signals")
    return signals

# --- Vectorized condition functions ---

def bull_pullback_condition(df):
    """
    Bull pullback condition function (vectorized)
    
    Returns:
        tuple: (bool_result, data_dict)
        
    Criteria:
        - Two consecutive bullish candles (close > open)
        - Pullback to rising 50-day moving average
    """
    if len(df) < 3:
        return False, {}
    
    # Create boolean masks
    bullish_candles = df['close'] > df['open']
    
    # Check for two consecutive bullish candles
    two_bullish = bullish_candles.shift(2) & bullish_candles.shift(1)
    
    # Check for rising MA and price at MA
    ma_rising = df['MA50'] > df['MA50'].shift(1)
    price_at_ma = df['low'] <= df['MA50']
    
    # Combine all conditions
    condition_met = two_bullish & ma_rising & price_at_ma
    
    # Return result for the last day
    return bool(condition_met.iloc[-1]), {}

def bear_rally_condition(df):
    """
    Bear rally condition function (vectorized)
    
    Returns:
        tuple: (bool_result, data_dict)
        
    Criteria:
        - Two consecutive bearish candles (close < open)
        - Rally to falling 50-day moving average
    """
    if len(df) < 3:
        return False, {}
    
    # Create boolean masks
    bearish_candles = df['close'] < df['open']
    
    # Check for two consecutive bearish candles
    two_bearish = bearish_candles.shift(2) & bearish_candles.shift(1)
    
    # Check for falling MA and price at MA
    ma_falling = df['MA50'] < df['MA50'].shift(1)
    price_at_ma = df['high'] >= df['MA50']
    
    # Combine all conditions
    condition_met = two_bearish & ma_falling & price_at_ma
    
    # Return result for the last day
    return bool(condition_met.iloc[-1]), {}

def high_base_condition(df):
    """
    High base condition function (vectorized)
    
    Returns:
        tuple: (bool_result, data_dict)
        
    Criteria:
        - Price near 52-week high (within configured percentage)
        - Low volatility (ATR below historical average)
        - Tight consolidation (narrow range)
    """
    if len(df) < 20:  # Need at least 20 days for moving averages
        return False, {}
    
    config_values = {
        'price_threshold': 0.95,  # Within 5% of 52-week high
        'atr_threshold': 0.8,     # ATR below 80% of average
        'range_threshold': 0.8    # Range below 80% of average
    }
    
    # Create boolean masks for each condition
    near_highs = df['close'] >= config_values['price_threshold'] * df['52w_high']
    low_volatility = df['ATR_ratio'] < config_values['atr_threshold']
    tight_range = df['range_ratio'] < config_values['range_threshold']
    
    # Combine all conditions
    condition_met = near_highs & low_volatility & tight_range
    
    # Return result for the last day
    return bool(condition_met.iloc[-1]), config_values

def low_base_condition(df):
    """
    Low base condition function (vectorized)
    
    Returns:
        tuple: (bool_result, data_dict)
        
    Criteria:
        - Price near 52-week low (within configured percentage)
        - Low volatility (ATR below historical average)
        - Tight consolidation (narrow range)
    """
    if len(df) < 20:  # Need at least 20 days for moving averages
        return False, {}
    
    config_values = {
        'price_threshold': 1.05,  # Within 5% of 52-week low
        'atr_threshold': 0.8,     # ATR below 80% of average
        'range_threshold': 0.8    # Range below 80% of average
    }
    
    # Create boolean masks for each condition
    near_lows = df['close'] <= config_values['price_threshold'] * df['52w_low']
    low_volatility = df['ATR_ratio'] < config_values['atr_threshold']
    tight_range = df['range_ratio'] < config_values['range_threshold']
    
    # Combine all conditions
    condition_met = near_lows & low_volatility & tight_range
    
    # Return result for the last day
    return bool(condition_met.iloc[-1]), config_values

# --- Scan functions ---

def scan_bull_pullbacks(ib, symbols, config, parallel=True, max_workers=4):
    """Run bull pullback scan"""
    if parallel and len(symbols) > 10:  # Only parallelize for larger symbol lists
        return scan_securities_parallel(ib, symbols, "Bull Pullback", bull_pullback_condition, config, max_workers)
    else:
        return scan_securities(ib, symbols, "Bull Pullback", bull_pullback_condition, config)

def scan_bear_rallies(ib, symbols, config, parallel=True, max_workers=4):
    """Run bear rally scan"""
    if parallel and len(symbols) > 10:
        return scan_securities_parallel(ib, symbols, "Bear Rally", bear_rally_condition, config, max_workers)
    else:
        return scan_securities(ib, symbols, "Bear Rally", bear_rally_condition, config)

def scan_high_base(ib, symbols, config, parallel=True, max_workers=4):
    """Run high base scan"""
    if parallel and len(symbols) > 10:
        return scan_securities_parallel(ib, symbols, "High Base", high_base_condition, config, max_workers)
    else:
        return scan_securities(ib, symbols, "High Base", high_base_condition, config)

def scan_low_base(ib, symbols, config, parallel=True, max_workers=4):
    """Run low base scan"""
    if parallel and len(symbols) > 10:
        return scan_securities_parallel(ib, symbols, "Low Base", low_base_condition, config, max_workers)
    else:
        return scan_securities(ib, symbols, "Low Base", low_base_condition, config) 