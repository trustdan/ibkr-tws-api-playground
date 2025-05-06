#!/usr/bin/env python
"""
Benchmark Script for Auto Vertical Spread Trader
------------------------------------------------
This script benchmarks the performance of different optimization strategies:
1. Original vs. Vectorized Operations
2. Sequential vs. Parallel Processing
3. With and Without Data Caching

Usage: python scripts/benchmark.py
"""

import sys
import os
import time
import pandas as pd
import numpy as np
import logging
import concurrent.futures
from pathlib import Path
import pickle
import matplotlib.pyplot as plt

# Configure minimal logging
logging.basicConfig(level=logging.WARNING)

# Add parent directory to path to import our modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


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
        df = pd.DataFrame(
            {"open": open_price, "high": high, "low": low, "close": close, "volume": volume},
            index=dates,
        )

        all_data[symbol] = df

    return all_data


# Original style indicator calculation
def calculate_indicators_original(df):
    """Calculate indicators one by one as in the original code"""
    start_time = time.time()

    # Moving averages
    df["MA50"] = df["close"].rolling(50).mean()

    # ATR
    high = df["high"].values
    low = df["low"].values
    close = df["close"].values

    import pandas_ta as ta

    df["ATR14"] = ta.atr(high=df["high"], low=df["low"], close=df["close"], length=14)

    # Pre-calculate indicators for high/low base patterns
    df["52w_high"] = df["close"].rolling(252).max()
    df["52w_low"] = df["close"].rolling(252).min()
    df["ATR_ratio"] = df["ATR14"] / df["ATR14"].rolling(20).mean()
    df["range_pct"] = (df["high"] - df["low"]) / df["close"] * 100
    df["range_ratio"] = df["range_pct"] / df["range_pct"].rolling(20).mean()

    return time.time() - start_time


# Optimized bulk indicator calculation
def calculate_indicators_optimized(df):
    """Calculate indicators in bulk using pandas-ta strategy"""
    start_time = time.time()

    import pandas_ta as ta

    # Use pandas-ta's strategy for bulk processing
    df.ta.strategy(
        name="VerticalSpreadStrategy",
        ta=[
            {"kind": "sma", "length": 50, "close": "close", "col_names": ("MA50",)},
            {"kind": "atr", "length": 14, "col_names": ("ATR14",)},
        ],
    )

    # Additional indicators
    df["52w_high"] = df["close"].rolling(252).max()
    df["52w_low"] = df["close"].rolling(252).min()
    df["ATR_ratio"] = df["ATR14"] / df["ATR14"].rolling(20).mean()
    df["range_pct"] = (df["high"] - df["low"]) / df["close"] * 100
    df["range_ratio"] = df["range_pct"] / df["range_pct"].rolling(20).mean()

    return time.time() - start_time


# Original style condition function
def high_base_condition_original(df):
    """Original high base condition function"""
    today = df.iloc[-1]

    # High-base criteria
    near_highs = today.close >= 0.95 * today["52w_high"]
    low_volatility = today.ATR_ratio < 0.8
    tight_range = today.range_pct < df.range_pct.rolling(20).mean().iloc[-1] * 0.8

    return (near_highs and low_volatility and tight_range), {}


# Vectorized condition function
def high_base_condition_vectorized(df):
    """Vectorized high base condition function"""
    if len(df) < 20:
        return False, {}

    # Create boolean masks for each condition
    near_highs = df["close"] >= 0.95 * df["52w_high"]
    low_volatility = df["ATR_ratio"] < 0.8
    tight_range = df["range_pct"] < df["range_pct"].rolling(20).mean() * 0.8

    # Combine all conditions
    condition_met = near_highs & low_volatility & tight_range

    # Return result for the last day
    return bool(condition_met.iloc[-1]), {}


# Sequential scan
def scan_sequential(all_data, condition_func):
    """Scan symbols sequentially"""
    start_time = time.time()
    signals = []

    for symbol, df in all_data.items():
        try:
            result, _ = condition_func(df)
            if result:
                signals.append(symbol)
        except Exception as e:
            print(f"Error in {symbol}: {e}")

    return signals, time.time() - start_time


# Parallel scan
def scan_parallel(all_data, condition_func, max_workers=4):
    """Scan symbols in parallel"""
    start_time = time.time()

    def process_symbol(item):
        symbol, df = item
        try:
            result, _ = condition_func(df)
            if result:
                return symbol
            return None
        except Exception as e:
            print(f"Error in {symbol}: {e}")
            return None

    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(process_symbol, all_data.items()))

    signals = [symbol for symbol in results if symbol is not None]
    return signals, time.time() - start_time


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
        return df, 0

    cache_dir = Path("benchmark_cache")
    cache_dir.mkdir(exist_ok=True)

    cache_file = cache_dir / f"{symbol}.pkl"

    start_time = time.time()
    if cache_file.exists():
        with open(cache_file, "rb") as f:
            df = pickle.load(f)
        return df, time.time() - start_time

    # Otherwise calculate indicators
    calculate_indicators_optimized(df)

    with open(cache_file, "wb") as f:
        pickle.dump(df, f)

    return df, time.time() - start_time


def run_benchmarks():
    """Run all benchmarks"""
    # Generate sample data
    all_data = generate_sample_data(symbols=100, days=252)

    # 1. Compare indicator calculation methods
    print("\n1. Comparing indicator calculation methods...")

    # Get a sample dataframe
    sample_df = all_data["SYM000"].copy()

    # Measure original method
    orig_time = calculate_indicators_original(sample_df.copy())
    print(f"Original method: {orig_time:.6f} seconds")

    # Measure optimized method
    opt_time = calculate_indicators_optimized(sample_df.copy())
    print(f"Optimized bulk method: {opt_time:.6f} seconds")
    print(f"Speedup: {orig_time/opt_time:.2f}x")

    # 2. Compare condition function methods
    print("\n2. Comparing condition function methods...")

    # Prepare a dataframe with indicators
    test_df = sample_df.copy()
    calculate_indicators_optimized(test_df)

    # Time original condition function
    iterations = 1000
    start = time.time()
    for _ in range(iterations):
        high_base_condition_original(test_df)
    orig_cond_time = (time.time() - start) / iterations
    print(f"Original condition function: {orig_cond_time:.6f} seconds per call")

    # Time vectorized condition function
    start = time.time()
    for _ in range(iterations):
        high_base_condition_vectorized(test_df)
    vec_cond_time = (time.time() - start) / iterations
    print(f"Vectorized condition function: {vec_cond_time:.6f} seconds per call")
    print(f"Speedup: {orig_cond_time/vec_cond_time:.2f}x")

    # 3. Compare sequential vs parallel scanning
    print("\n3. Comparing sequential vs parallel scanning...")

    # Pre-compute indicators for all data
    for symbol, df in all_data.items():
        calculate_indicators_optimized(df)

    # Sequential scan
    seq_signals, seq_time = scan_sequential(all_data, high_base_condition_vectorized)
    print(f"Sequential scan: {seq_time:.6f} seconds, found {len(seq_signals)} signals")

    # Parallel scan with different worker counts
    for workers in [2, 4, 8]:
        par_signals, par_time = scan_parallel(
            all_data, high_base_condition_vectorized, max_workers=workers
        )
        print(
            f"Parallel scan ({workers} workers): {par_time:.6f} seconds, found {len(par_signals)} signals"
        )
        print(f"Speedup: {seq_time/par_time:.2f}x")

    # 4. Compare with and without caching
    print("\n4. Comparing with and without caching...")

    # Clear cache
    clear_cache()

    # First run (no cache)
    start_time = time.time()
    processed = 0
    cache_miss_time = 0

    for symbol, df in all_data.items():
        df_copy = df.copy()
        cached_df, cache_time = get_dataframe_cached(symbol, df_copy, use_cache=True)
        cache_miss_time += cache_time
        processed += 1

    first_run_time = time.time() - start_time
    print(f"First run (cache miss): {first_run_time:.6f} seconds for {processed} symbols")

    # Second run (with cache)
    start_time = time.time()
    processed = 0
    cache_hit_time = 0

    for symbol, df in all_data.items():
        df_copy = df.copy()
        cached_df, cache_time = get_dataframe_cached(symbol, df_copy, use_cache=True)
        cache_hit_time += cache_time
        processed += 1

    second_run_time = time.time() - start_time
    print(f"Second run (cache hit): {second_run_time:.6f} seconds for {processed} symbols")
    print(f"Speedup: {first_run_time/second_run_time:.2f}x")

    # 5. Generate summary chart
    print("\n5. Generating summary chart...")

    # Prepare data for chart
    categories = [
        "Indicator\nCalculation",
        "Condition\nFunction",
        "Symbol\nScanning",
        "Data\nLoading",
    ]
    before = [orig_time, orig_cond_time, seq_time, first_run_time]
    after = [opt_time, vec_cond_time, par_time, second_run_time]  # Using 4 workers for parallel

    speedups = [b / a for b, a in zip(before, after)]

    # Create chart
    plt.figure(figsize=(12, 6))

    x = np.arange(len(categories))
    width = 0.35

    plt.bar(x - width / 2, before, width, label="Before Optimization")
    plt.bar(x + width / 2, after, width, label="After Optimization")

    plt.yscale("log")
    plt.ylabel("Time (seconds, log scale)")
    plt.title("Performance Optimization Results")
    plt.xticks(x, categories)
    plt.legend()

    # Add speedup annotations
    for i, (x_pos, y_pos, speedup) in enumerate(zip(x, after, speedups)):
        plt.annotate(
            f"{speedup:.1f}x faster",
            xy=(x_pos, y_pos),
            xytext=(0, 10),
            textcoords="offset points",
            ha="center",
            va="bottom",
        )

    # Save chart
    plt.savefig("optimization_results.png")
    plt.close()

    print(f"Chart saved to optimization_results.png")

    # Final summary
    print("\nOverall performance improvements:")
    for cat, speedup in zip(categories, speedups):
        print(f"- {cat}: {speedup:.1f}x faster")


if __name__ == "__main__":
    run_benchmarks()
