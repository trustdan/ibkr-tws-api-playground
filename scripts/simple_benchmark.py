#!/usr/bin/env python
"""
Simple Benchmark Script for Auto Vertical Spread Trader
------------------------------------------------------
This script demonstrates core performance improvements:
1. Vectorized vs Row-by-Row Operations
2. With and Without Data Caching

Usage: python scripts/simple_benchmark.py
"""

import os
import time
import pandas as pd
import numpy as np
from pathlib import Path
import pickle

# Create sample data
def generate_sample_data(symbols=100, days=252):
    """Generate sample price data for multiple symbols"""
    print(f"Generating sample data for {symbols} symbols with {days} days each...")
    
    all_data = {}
    
    for i in range(symbols):
        symbol = f"SYM{i:03d}"
        
        # Generate random price series with realistic properties
        np.random.seed(i)  # For reproducibility per symbol
        
        # Start at a random price between $20-$200
        start_price = np.random.uniform(20, 200)
        
        # Random daily returns with slight upward bias
        returns = np.random.normal(0.0003, 0.015, days)
        
        # Cumulative returns to get price series
        cum_returns = np.cumprod(1 + returns)
        close = start_price * cum_returns
        
        # Generate OHLC data
        high = close * np.random.uniform(1.0, 1.03, days)
        low = close * np.random.uniform(0.97, 1.0, days)
        open_price = low + np.random.uniform(0, 1, days) * (high - low)
        
        # Generate volume
        volume = np.random.randint(100000, 10000000, days)
        
        # Create DataFrame
        dates = pd.date_range(end=pd.Timestamp.today(), periods=days)
        df = pd.DataFrame({
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        }, index=dates)
        
        all_data[symbol] = df
    
    return all_data

# Calculate indicators
def calculate_indicators(df):
    """Calculate indicators"""
    # Simple Moving Average
    df['MA50'] = df['close'].rolling(50).mean()
    
    # ATR (Average True Range) - simplified calculation
    df['TR'] = np.maximum(
        df['high'] - df['low'],
        np.maximum(
            np.abs(df['high'] - df['close'].shift(1)),
            np.abs(df['low'] - df['close'].shift(1))
        )
    )
    df['ATR14'] = df['TR'].rolling(14).mean()
    
    # Pre-calculate indicators for high/low base patterns
    df['52w_high'] = df['close'].rolling(252).max()
    df['52w_low'] = df['close'].rolling(252).min()
    df['ATR_ratio'] = df['ATR14'] / df['ATR14'].rolling(20).mean()
    df['range_pct'] = (df['high'] - df['low']) / df['close'] * 100
    df['range_ratio'] = df['range_pct'] / df['range_pct'].rolling(20).mean()
    
    return df

# Row-by-row condition function (original style)
def high_base_condition_original(df):
    """Original high base condition function (row by row)"""
    if len(df) < 252:  # Need at least a year of data
        return False
    
    today = df.iloc[-1]
    
    # High-base criteria
    near_highs = today.close >= 0.95 * today['52w_high']
    low_volatility = today.ATR_ratio < 0.8
    tight_range = today.range_pct < df.range_pct.rolling(20).mean().iloc[-1] * 0.8
    
    return near_highs and low_volatility and tight_range

# Vectorized condition function (optimized)
def high_base_condition_vectorized(df):
    """Vectorized high base condition function"""
    if len(df) < 252:  # Need at least a year of data
        return False
    
    # Create boolean masks for each condition
    near_highs = df['close'] >= 0.95 * df['52w_high']
    low_volatility = df['ATR_ratio'] < 0.8
    tight_range = df['range_pct'] < df['range_pct'].rolling(20).mean() * 0.8
    
    # Combine all conditions
    condition_met = near_highs & low_volatility & tight_range
    
    # Return result for the last day
    return bool(condition_met.iloc[-1])

# Row-by-row scan
def scan_row_by_row(all_data):
    """Scan symbols using row-by-row checks"""
    start_time = time.time()
    signals = []
    
    for symbol, df in all_data.items():
        try:
            result = high_base_condition_original(df)
            if result:
                signals.append(symbol)
        except Exception as e:
            print(f"Error in {symbol}: {e}")
    
    elapsed = time.time() - start_time
    return signals, elapsed

# Vectorized scan
def scan_vectorized(all_data):
    """Scan symbols using vectorized operations"""
    start_time = time.time()
    signals = []
    
    for symbol, df in all_data.items():
        try:
            result = high_base_condition_vectorized(df)
            if result:
                signals.append(symbol)
        except Exception as e:
            print(f"Error in {symbol}: {e}")
    
    elapsed = time.time() - start_time
    return signals, elapsed

# Cache utilities
def clear_cache():
    """Clear the cache directory"""
    cache_dir = Path("benchmark_cache")
    if cache_dir.exists():
        import shutil
        shutil.rmtree(cache_dir)
    cache_dir.mkdir(exist_ok=True)

def get_dataframe_cached(symbol, df, use_cache=True):
    """Get DataFrame with caching"""
    if not use_cache:
        # Calculate and return without caching
        return calculate_indicators(df.copy()), 0
    
    cache_dir = Path("benchmark_cache")
    cache_dir.mkdir(exist_ok=True)
    
    cache_file = cache_dir / f"{symbol}.pkl"
    
    start_time = time.time()
    if cache_file.exists():
        # Load from cache
        with open(cache_file, 'rb') as f:
            df = pickle.load(f)
        cache_time = time.time() - start_time
        return df, cache_time
    
    # Calculate indicators
    result_df = calculate_indicators(df.copy())
    
    # Save to cache
    with open(cache_file, 'wb') as f:
        pickle.dump(result_df, f)
    
    cache_time = time.time() - start_time
    return result_df, cache_time

def run_benchmarks():
    """Run all benchmarks"""
    # Generate sample data
    all_data = generate_sample_data(symbols=50, days=252)
    processed_data = {}
    
    # Pre-process data for consistent benchmarking
    print("Calculating indicators for all symbols...")
    for symbol, df in all_data.items():
        processed_data[symbol] = calculate_indicators(df.copy())
    
    # 1. Compare condition function methods
    print("\n1. Comparing condition function methods...")
    
    # Get a sample dataframe
    sample_df = processed_data["SYM000"]
    
    # Time original condition function
    iterations = 1000
    start = time.time()
    for _ in range(iterations):
        high_base_condition_original(sample_df)
    orig_cond_time = (time.time() - start)
    print(f"Original row-by-row: {orig_cond_time:.6f} seconds ({iterations} iterations)")
    
    # Time vectorized condition function
    start = time.time()
    for _ in range(iterations):
        high_base_condition_vectorized(sample_df)
    vec_cond_time = (time.time() - start)
    print(f"Vectorized: {vec_cond_time:.6f} seconds ({iterations} iterations)")
    print(f"Speedup: {orig_cond_time/vec_cond_time:.2f}x")
    
    # 2. Compare scan methods
    print("\n2. Comparing scan methods...")
    
    # Row-by-row scan
    row_signals, row_time = scan_row_by_row(processed_data)
    print(f"Row-by-row scan: {row_time:.6f} seconds, found {len(row_signals)} signals")
    
    # Vectorized scan
    vec_signals, vec_time = scan_vectorized(processed_data)
    print(f"Vectorized scan: {vec_time:.6f} seconds, found {len(vec_signals)} signals")
    print(f"Speedup: {row_time/vec_time:.2f}x")
    
    # 3. Compare with and without caching
    print("\n3. Comparing with and without caching...")
    
    # Clear cache
    clear_cache()
    
    # First run (no cache)
    start_time = time.time()
    processed = 0
    
    for symbol, df in all_data.items():
        df_copy = df.copy()
        processed_df, _ = get_dataframe_cached(symbol, df_copy, use_cache=True)
        processed += 1
    
    first_run_time = time.time() - start_time
    print(f"First run (cache miss): {first_run_time:.6f} seconds for {processed} symbols")
    
    # Second run (with cache)
    start_time = time.time()
    processed = 0
    
    for symbol, df in all_data.items():
        df_copy = df.copy()
        processed_df, _ = get_dataframe_cached(symbol, df_copy, use_cache=True)
        processed += 1
    
    second_run_time = time.time() - start_time
    print(f"Second run (cache hit): {second_run_time:.6f} seconds for {processed} symbols")
    print(f"Speedup: {first_run_time/second_run_time:.2f}x")
    
    # Final summary
    print("\nOverall performance improvements:")
    print(f"- Condition Function: {orig_cond_time/vec_cond_time:.2f}x faster with vectorization")
    print(f"- Scanning Method: {row_time/vec_time:.2f}x faster with vectorized scanning")
    print(f"- Data Loading: {first_run_time/second_run_time:.2f}x faster with caching")
    
    print("\nNote: Additional speedups with parallel processing are available")
    print("but require a more complex implementation than this simple benchmark.")

if __name__ == "__main__":
    run_benchmarks() 