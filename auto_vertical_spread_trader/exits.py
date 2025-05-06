"""
Exit strategies module for the auto vertical spread trader.
Handles profit targets including Fibonacci extensions.
"""

import logging
import numpy as np

logger = logging.getLogger(__name__)

def find_recent_swing(df, direction):
    """
    Find recent swing high/low for Fibonacci extensions
    
    Args:
        df: DataFrame with price data
        direction: 'bull'/'high_base' or 'bear'/'low_base'
        
    Returns:
        tuple: (swing_start_price, swing_end_price, swing_start_index)
    """
    # For bullish strategies, find recent swing low to high
    if direction in ['bull', 'high_base']:
        # Look back up to 20 bars to find a swing low
        window = min(20, len(df) - 2)
        prices = df['low'].values
        for i in range(window, 1, -1):
            # Simple swing low detection (price lower than neighbors)
            if prices[-i] < prices[-i-1] and prices[-i] < prices[-i+1]:
                swing_low = prices[-i]
                # Find subsequent swing high
                swing_high = max(prices[-i+1:])
                return swing_low, swing_high, -i
                
    # For bearish strategies, find recent swing high to low
    else:
        window = min(20, len(df) - 2)
        prices = df['high'].values
        for i in range(window, 1, -1):
            # Simple swing high detection (price higher than neighbors)
            if prices[-i] > prices[-i-1] and prices[-i] > prices[-i+1]:
                swing_high = prices[-i]
                # Find subsequent swing low
                swing_low = min(prices[-i+1:])
                return swing_high, swing_low, -i
                
    # If no clear swing found, use recent range
    if direction in ['bull', 'high_base']:
        return df['low'].min(), df['high'].max(), -10
    else:
        return df['high'].max(), df['low'].min(), -10

def add_fibonacci_target(spread_info, df, extension_level=1.618):
    """
    Add Fibonacci extension target to spread info
    
    Args:
        spread_info: Dictionary with trade information
        df: DataFrame with price data
        extension_level: Fibonacci extension level (1.272, 1.618, 2.0, 2.618)
        
    Returns:
        dict: Updated spread_info with Fibonacci target
        
    Notes:
        Common extension levels: 1.272, 1.618, 2.0, 2.618
    """
    direction = spread_info['type']
    
    # Find recent swing
    swing_start, swing_end, _ = find_recent_swing(df, direction)
    swing_range = abs(swing_end - swing_start)
    
    # Calculate extension
    if direction in ['bull', 'high_base']:
        target = swing_end + (swing_range * extension_level)
    else:
        target = swing_end - (swing_range * extension_level)
        
    spread_info['price_target'] = target
    spread_info['target_type'] = f"Fib {extension_level}"
    spread_info['swing_start'] = swing_start
    spread_info['swing_end'] = swing_end
    
    logger.info(f"Added Fibonacci target for {spread_info['symbol']}: "
               f"Swing from {swing_start:.2f} to {swing_end:.2f}, "
               f"Target: {target:.2f} ({extension_level} extension)")
    
    return spread_info

def add_r_multiple_target(spread_info, r_multiple=2.0):
    """
    Add fixed R-multiple price target to spread info
    
    Args:
        spread_info: Dictionary with trade information
        r_multiple: Target as multiple of initial risk
        
    Returns:
        dict: Updated spread_info with R-multiple target
    """
    direction = spread_info['type']
    entry_price = spread_info['entryPrice']
    stop_loss = entry_price - (spread_info['ATR'] * spread_info['config']['STOP_LOSS_ATR_MULT']) if direction in ['bull', 'high_base'] else \
                entry_price + (spread_info['ATR'] * spread_info['config']['STOP_LOSS_ATR_MULT'])
    
    # Calculate R value (risk)
    r_value = abs(entry_price - stop_loss)
    
    # Set target based on direction
    if direction in ['bull', 'high_base']:
        target = entry_price + (r_value * r_multiple)
    else:
        target = entry_price - (r_value * r_multiple)
        
    spread_info['price_target'] = target
    spread_info['target_type'] = f"{r_multiple}R"
    
    logger.info(f"Added R-multiple target for {spread_info['symbol']}: "
               f"Entry: {entry_price:.2f}, Stop: {stop_loss:.2f}, "
               f"Target: {target:.2f} ({r_multiple}R)")
    
    return spread_info

def add_atr_target(spread_info, atr_multiple=3.0):
    """
    Add ATR-based price target to spread info
    
    Args:
        spread_info: Dictionary with trade information
        atr_multiple: Target as multiple of ATR
        
    Returns:
        dict: Updated spread_info with ATR-multiple target
    """
    direction = spread_info['type']
    entry_price = spread_info['entryPrice']
    atr = spread_info['ATR']
    
    # Set target based on direction
    if direction in ['bull', 'high_base']:
        target = entry_price + (atr * atr_multiple)
    else:
        target = entry_price - (atr * atr_multiple)
        
    spread_info['price_target'] = target
    spread_info['target_type'] = f"{atr_multiple}ATR"
    
    logger.info(f"Added ATR-multiple target for {spread_info['symbol']}: "
               f"Entry: {entry_price:.2f}, ATR: {atr:.2f}, "
               f"Target: {target:.2f} ({atr_multiple}ATR)")
    
    return spread_info 