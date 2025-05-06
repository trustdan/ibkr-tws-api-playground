#!/usr/bin/env python
"""
Optimized Benchmark Script for Auto Vertical Spread Trader
---------------------------------------------------------
This script demonstrates performance improvements with:
1. Vectorized operations for larger datasets
2. Data caching for repeated calculations
3. Optimized implementations

Usage: python scripts/optimized_benchmark.py
"""

import os
import time
import pandas as pd
import numpy as np
from pathlib import Path
import pickle

def print_header(message):
    """Print a formatted header message"""
    print("\n" + "=" * 70)
    print(f"  {message}")
    print("=" * 70)

# Create sample data with more rows to better highlight vectorization benefits
def generate_sample_data(symbols=20, days=1000):
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

# Calculate indicators - non-vectorized version
def calculate_indicators_non_vectorized(df):
    """Calculate indicators one by one with loops"""
    start_time = time.time()
    
    # Copy to avoid modifying the original
    result_df = df.copy()
    
    # Calculate MA50 row by row
    ma50 = np.zeros(len(df))
    for i in range(50, len(df)):
        window = df['close'].iloc[i-50:i].values
        ma50[i] = np.mean(window)
    result_df['MA50'] = ma50
    
    # Calculate ATR row by row
    tr = np.zeros(len(df))
    for i in range(1, len(df)):
        tr[i] = max(
            df['high'].iloc[i] - df['low'].iloc[i],
            abs(df['high'].iloc[i] - df['close'].iloc[i-1]),
            abs(df['low'].iloc[i] - df['close'].iloc[i-1])
        )
    
    # Manual ATR calculation
    atr14 = np.zeros(len(df))
    for i in range(14, len(df)):
        atr14[i] = np.mean(tr[i-14:i])
    result_df['ATR14'] = atr14
    
    # 52-week high and low
    for i in range(252, len(df)):
        result_df.loc[result_df.index[i], '52w_high'] = df['close'].iloc[i-252:i].max()
        result_df.loc[result_df.index[i], '52w_low'] = df['close'].iloc[i-252:i].min()
    
    # Fill missing values with NaN
    result_df['MA50'] = result_df['MA50'].replace(0, np.nan)
    result_df['ATR14'] = result_df['ATR14'].replace(0, np.nan)
    
    elapsed = time.time() - start_time
    return result_df, elapsed

# Calculate indicators - vectorized version
def calculate_indicators_vectorized(df):
    """Calculate indicators using vectorized pandas operations"""
    start_time = time.time()
    
    # Copy to avoid modifying the original
    result_df = df.copy()
    
    # Calculate MA50
    result_df['MA50'] = df['close'].rolling(50).mean()
    
    # Calculate ATR using vectorized operations
    tr = pd.DataFrame({
        'hl': df['high'] - df['low'],
        'hc': (df['high'] - df['close'].shift(1)).abs(),
        'lc': (df['low'] - df['close'].shift(1)).abs()
    }).max(axis=1)
    
    result_df['ATR14'] = tr.rolling(14).mean()
    
    # 52-week high and low
    result_df['52w_high'] = df['close'].rolling(252).max()
    result_df['52w_low'] = df['close'].rolling(252).min()
    
    elapsed = time.time() - start_time
    return result_df, elapsed

# Filter test - non-vectorized version with loops
def filter_signals_non_vectorized(dfs, threshold=0.95):
    """Find signals using loops and if conditions"""
    start_time = time.time()
    signals = []
    
    for symbol, df in dfs.items():
        # Skip if not enough data
        if len(df) < 252 or df['52w_high'].iloc[-1] is None:
            continue
        
        # Check conditions on the last row
        if df['close'].iloc[-1] >= threshold * df['52w_high'].iloc[-1]:
            signals.append(symbol)
    
    elapsed = time.time() - start_time
    return signals, elapsed

# Filter test - vectorized version
def filter_signals_vectorized(dfs, threshold=0.95):
    """Find signals using vectorized operations"""
    start_time = time.time()
    signals = []
    
    for symbol, df in dfs.items():
        # Skip if not enough data
        if len(df) < 252:
            continue
            
        # Create condition mask
        near_highs = df['close'] >= threshold * df['52w_high']
        
        # Check if the last day meets the condition
        if near_highs.iloc[-1]:
            signals.append(symbol)
    
    elapsed = time.time() - start_time
    return signals, elapsed

# Cache test functions
def clear_cache():
    """Clear the cache directory"""
    cache_dir = Path("benchmark_cache")
    if cache_dir.exists():
        import shutil
        shutil.rmtree(cache_dir)
    cache_dir.mkdir(exist_ok=True)

def calculate_with_cache(symbols_data, cache_enabled=True):
    """Calculate indicators with or without caching"""
    cache_dir = Path("benchmark_cache")
    cache_dir.mkdir(exist_ok=True)
    
    start_time = time.time()
    results = {}
    
    for symbol, df in symbols_data.items():
        cache_file = cache_dir / f"{symbol}.pkl"
        
        if cache_enabled and cache_file.exists():
            # Load from cache
            with open(cache_file, 'rb') as f:
                results[symbol] = pickle.load(f)
        else:
            # Calculate and cache
            processed_df, _ = calculate_indicators_vectorized(df)
            results[symbol] = processed_df
            
            if cache_enabled:
                with open(cache_file, 'wb') as f:
                    pickle.dump(processed_df, f)
    
    elapsed = time.time() - start_time
    return results, elapsed

def run_benchmarks():
    """Run all benchmark tests"""
    # Generate sample data
    all_data = generate_sample_data(symbols=20, days=1000)
    
    # 1. Benchmark: Indicator Calculation
    print_header("BENCHMARK 1: INDICATOR CALCULATION")
    
    # Select a sample dataframe
    sample_symbol = list(all_data.keys())[0]
    sample_df = all_data[sample_symbol]
    
    # Test non-vectorized calculation
    print(f"Running non-vectorized calculation for {len(sample_df)} rows...")
    _, non_vec_time = calculate_indicators_non_vectorized(sample_df)
    print(f"Non-vectorized: {non_vec_time:.6f} seconds")
    
    # Test vectorized calculation
    print(f"Running vectorized calculation for {len(sample_df)} rows...")
    _, vec_time = calculate_indicators_vectorized(sample_df)
    print(f"Vectorized: {vec_time:.6f} seconds")
    
    # Calculate speedup
    if vec_time > 0:
        speedup = non_vec_time / vec_time
        print(f"Speedup: {speedup:.2f}x faster with vectorization")
    
    # 2. Benchmark: Data Filtering
    print_header("BENCHMARK 2: DATA FILTERING")
    
    # Prepare data for filtering tests
    processed_data = {}
    for symbol, df in all_data.items():
        processed_data[symbol], _ = calculate_indicators_vectorized(df)
    
    # Test non-vectorized filtering
    print(f"Running non-vectorized filtering on {len(processed_data)} symbols...")
    _, non_vec_filter_time = filter_signals_non_vectorized(processed_data)
    print(f"Non-vectorized filtering: {non_vec_filter_time:.6f} seconds")
    
    # Test vectorized filtering
    print(f"Running vectorized filtering on {len(processed_data)} symbols...")
    _, vec_filter_time = filter_signals_vectorized(processed_data)
    print(f"Vectorized filtering: {vec_filter_time:.6f} seconds")
    
    # Calculate speedup
    if vec_filter_time > 0:
        filter_speedup = non_vec_filter_time / vec_filter_time
        print(f"Speedup: {filter_speedup:.2f}x faster with vectorization")
    
    # 3. Benchmark: Data Caching
    print_header("BENCHMARK 3: DATA CACHING")
    
    # Clear cache
    clear_cache()
    
    # Test without cache (first run)
    print(f"Running without cache ({len(all_data)} symbols)...")
    _, no_cache_time = calculate_with_cache(all_data, cache_enabled=False)
    print(f"No cache: {no_cache_time:.6f} seconds")
    
    # Test with cache (first fill)
    print(f"Filling cache ({len(all_data)} symbols)...")
    _, cache_fill_time = calculate_with_cache(all_data, cache_enabled=True)
    print(f"Cache fill: {cache_fill_time:.6f} seconds")
    
    # Test with cache (subsequent read)
    print(f"Reading from cache ({len(all_data)} symbols)...")
    _, cache_read_time = calculate_with_cache(all_data, cache_enabled=True)
    print(f"Cache read: {cache_read_time:.6f} seconds")
    
    # Calculate speedup
    if cache_read_time > 0:
        cache_speedup = no_cache_time / cache_read_time
        print(f"Speedup: {cache_speedup:.2f}x faster with caching")
    
    # Summary
    print_header("BENCHMARK SUMMARY")
    print("Performance improvements with optimizations:")
    if 'speedup' in locals():
        print(f"1. Indicator Calculation: {speedup:.2f}x faster with vectorization")
    if 'filter_speedup' in locals():
        print(f"2. Data Filtering: {filter_speedup:.2f}x faster with vectorization")
    if 'cache_speedup' in locals():
        print(f"3. Data Loading: {cache_speedup:.2f}x faster with caching")
    
    print("\nNote: Real-world performance may vary based on:")
    print("- Dataset size (vectorization benefits increase with larger data)")
    print("- Hardware (CPU speed, memory bandwidth, disk speed)")
    print("- Implementation details (optimize for your specific use case)")

if __name__ == "__main__":
    run_benchmarks() 