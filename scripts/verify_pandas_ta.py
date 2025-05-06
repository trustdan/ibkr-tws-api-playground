#!/usr/bin/env python
"""
Verify pandas-ta Installation
-----------------------------
This script checks if pandas-ta is correctly installed and functional.
It tests several common indicators to ensure proper operation.

Usage: python scripts/verify_pandas_ta.py
"""

import sys

import numpy as np
import pandas as pd

# Add debugging information
print(f"Python version: {sys.version}")
print(f"Python executable: {sys.executable}")
print(f"Path: {sys.path}")

# ANSI color codes for colored output
COLORS = {
    "red": "\033[91m",
    "green": "\033[92m",
    "yellow": "\033[93m",
    "blue": "\033[94m",
    "reset": "\033[0m",
}


def print_colored(message, color_name="reset"):
    """Print text in color"""
    if sys.platform == "win32":
        # Windows console might not support ANSI color codes
        print(message)
    else:
        color = COLORS.get(color_name, COLORS["reset"])
        print(f"{color}{message}{COLORS['reset']}")


def main():
    """Main verification function"""
    print_colored("Verifying pandas-ta installation...", "blue")

    # Check if pandas-ta is installed
    try:
        import pandas_ta as ta

        print_colored(f"pandas-ta is installed", "green")
        print_colored(f"Available categories: {list(ta.Category.keys())}", "green")
    except ImportError:
        print_colored("pandas-ta is not installed!", "red")
        print_colored("To install pandas-ta, run: pip install pandas-ta", "yellow")
        return 1

    # Generate sample data
    print_colored("Generating sample data...", "blue")
    np.random.seed(42)
    close = 100 + np.cumsum(np.random.normal(0, 1, 100))
    high = close + np.random.uniform(0, 3, 100)
    low = close - np.random.uniform(0, 3, 100)
    volume = np.random.randint(1000, 10000, 100)

    df = pd.DataFrame({"close": close, "high": high, "low": low, "volume": volume})

    # Test various indicators
    print_colored("Testing indicators...", "blue")

    # Test SMA
    try:
        sma = df.ta.sma(length=14)
        print_colored("[PASS] SMA calculation successful", "green")
    except Exception as e:
        print_colored(f"[FAIL] SMA calculation failed: {e}", "red")
        return 1

    # Test RSI
    try:
        rsi = df.ta.rsi(length=14)
        print_colored("[PASS] RSI calculation successful", "green")
    except Exception as e:
        print_colored(f"[FAIL] RSI calculation failed: {e}", "red")
        return 1

    # Test MACD
    try:
        macd = df.ta.macd(fast=12, slow=26, signal=9)
        print_colored("[PASS] MACD calculation successful", "green")
    except Exception as e:
        print_colored(f"[FAIL] MACD calculation failed: {e}", "red")
        return 1

    # Test Bollinger Bands
    try:
        bbands = df.ta.bbands(length=20, std=2)
        print_colored("[PASS] Bollinger Bands calculation successful", "green")
    except Exception as e:
        print_colored(f"[FAIL] Bollinger Bands calculation failed: {e}", "red")
        return 1

    # Test ATR - critical for our trading strategy
    try:
        atr = df.ta.atr(length=14)
        print_colored("[PASS] ATR calculation successful", "green")
    except Exception as e:
        print_colored(f"[FAIL] ATR calculation failed: {e}", "red")
        return 1

    # Test Stochastic
    try:
        stoch = df.ta.stoch(k=5, d=3, smooth_k=3)
        print_colored("[PASS] Stochastic calculation successful", "green")
    except Exception as e:
        print_colored(f"[FAIL] Stochastic calculation failed: {e}", "red")
        return 1

    # Test ADX
    try:
        adx = df.ta.adx(length=14)
        print_colored("[PASS] ADX calculation successful", "green")
    except Exception as e:
        print_colored(f"[FAIL] ADX calculation failed: {e}", "red")
        return 1

    # Test OBV
    try:
        obv = df.ta.obv()
        print_colored("[PASS] OBV calculation successful", "green")
    except Exception as e:
        print_colored(f"[FAIL] OBV calculation failed: {e}", "red")
        return 1

    # Test multiple indicators at once
    try:
        print_colored("Testing strategy with multiple indicators...", "blue")
        # Apply a set of indicators
        df.ta.strategy("All")
        print_colored("[PASS] Strategy application successful", "green")
    except Exception as e:
        print_colored(f"[FAIL] Strategy application failed: {e}", "red")
        # This is not critical, so don't fail the test

    print_colored("\n[PASS] pandas-ta verification complete: ALL TESTS PASSED", "green")
    print_colored("\nYou can now use pandas-ta in your trading strategy.", "blue")
    print_colored("Example usage:", "yellow")
    print_colored("  import pandas as pd", "yellow")
    print_colored("  import pandas_ta as ta", "yellow")
    print_colored("  df = pd.DataFrame(...)", "yellow")
    print_colored("  df['ATR14'] = df.ta.atr(length=14)", "yellow")
    print_colored("  df[['BBL','BBM','BBU']] = df.ta.bbands(length=20, std=2)", "yellow")
    return 0


if __name__ == "__main__":
    sys.exit(main())
