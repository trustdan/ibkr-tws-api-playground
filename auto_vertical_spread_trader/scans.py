"""
Scan module for technical analysis conditions.
Provides a unified framework for scanning stocks based on technical criteria.
"""

import logging
import pandas as pd
import talib
from ib_insync import Stock, util

logger = logging.getLogger(__name__)

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
        
        # Calculate base indicators used by all scan types
        df['MA50'] = df['close'].rolling(50).mean()
        df['ATR14'] = talib.ATR(df['high'], df['low'], df['close'], timeperiod=14)
        
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

def scan_securities(ib, symbols, scan_name, condition_func, config):
    """
    Generic scanning function that applies a condition function to each symbol
    
    Args:
        ib: IB connection object
        symbols (list): List of symbols to scan
        scan_name (str): Name of the scan for logging
        condition_func (callable): Function that takes a dataframe and returns True/False plus additional data
        config (dict): Configuration dictionary
        
    Returns:
        list: List of tuples: (symbol, bar, ATR)
        
    Notes:
        - Handles errors for individual symbols without crashing
        - Enforces volume requirement from config
    """
    signals = []
    logger.info(f"Running {scan_name} scan on {len(symbols)} symbols")
    
    for sym in symbols:
        try:
            df = get_tech_df(ib, sym, config)
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

# --- Condition functions ---

def bull_pullback_condition(df):
    """
    Bull pullback condition function
    
    Returns:
        tuple: (bool_result, data_dict)
        
    Criteria:
        - Two consecutive bullish candles (close > open)
        - Pullback to rising 50-day moving average
    """
    today, y1, y2 = df.iloc[-1], df.iloc[-2], df.iloc[-3]
    
    # Two bullish candles
    two_bullish = y2.close > y2.open and y1.close > y1.open
    
    # Pullback to rising 50MA
    ma_rising = df.MA50.iloc[-1] > df.MA50.iloc[-2]
    price_at_ma = today.low <= today.MA50
    
    return (two_bullish and ma_rising and price_at_ma), {}

def bear_rally_condition(df):
    """
    Bear rally condition function
    
    Returns:
        tuple: (bool_result, data_dict)
        
    Criteria:
        - Two consecutive bearish candles (close < open)
        - Rally to falling 50-day moving average
    """
    today, y1, y2 = df.iloc[-1], df.iloc[-2], df.iloc[-3]
    
    # Two bearish candles
    two_bearish = y2.close < y2.open and y1.close < y1.open
    
    # Rally into falling 50MA
    ma_falling = df.MA50.iloc[-1] < df.MA50.iloc[-2]
    price_at_ma = today.high >= today.MA50
    
    return (two_bearish and ma_falling and price_at_ma), {}

def high_base_condition(df):
    """
    High base condition function
    
    Returns:
        tuple: (bool_result, data_dict)
        
    Criteria:
        - Price near 52-week high (within configured percentage)
        - Low volatility (ATR below historical average)
        - Tight consolidation (narrow range)
    """
    today = df.iloc[-1]
    config_values = {
        'price_threshold': 0.95,  # Within 5% of 52-week high
        'atr_threshold': 0.8,     # ATR below 80% of average
        'range_threshold': 0.8    # Range below 80% of average
    }
    
    # High-base criteria
    near_highs = today.close >= config_values['price_threshold'] * today['52w_high']
    low_volatility = today.ATR_ratio < config_values['atr_threshold']
    tight_range = today.range_ratio < config_values['range_threshold']
    
    return (near_highs and low_volatility and tight_range), config_values

def low_base_condition(df):
    """
    Low base condition function
    
    Returns:
        tuple: (bool_result, data_dict)
        
    Criteria:
        - Price near 52-week low (within configured percentage)
        - Low volatility (ATR below historical average)
        - Tight consolidation (narrow range)
    """
    today = df.iloc[-1]
    config_values = {
        'price_threshold': 1.05,  # Within 5% of 52-week low
        'atr_threshold': 0.8,     # ATR below 80% of average
        'range_threshold': 0.8    # Range below 80% of average
    }
    
    # Low-base criteria
    near_lows = today.close <= config_values['price_threshold'] * today['52w_low']
    low_volatility = today.ATR_ratio < config_values['atr_threshold']
    tight_range = today.range_ratio < config_values['range_threshold']
    
    return (near_lows and low_volatility and tight_range), config_values

# --- Scan functions ---

def scan_bull_pullbacks(ib, symbols, config):
    """Run bull pullback scan"""
    return scan_securities(ib, symbols, "Bull Pullback", bull_pullback_condition, config)

def scan_bear_rallies(ib, symbols, config):
    """Run bear rally scan"""
    return scan_securities(ib, symbols, "Bear Rally", bear_rally_condition, config)

def scan_high_base(ib, symbols, config):
    """Run high base scan"""
    return scan_securities(ib, symbols, "High Base", high_base_condition, config)

def scan_low_base(ib, symbols, config):
    """Run low base scan"""
    return scan_securities(ib, symbols, "Low Base", low_base_condition, config) 