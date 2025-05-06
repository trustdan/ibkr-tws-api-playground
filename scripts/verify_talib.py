#!/usr/bin/env python
# TA-Lib verification script
# Cross-platform verification of TA-Lib functionality
# Usage: python scripts/verify_talib.py

import sys
import os
import platform
import numpy as np

def print_colored(message, status):
    """Print colored messages based on status (platform-independent)."""
    # ANSI color codes
    GREEN = '\033[32m'
    RED = '\033[31m'
    YELLOW = '\033[33m'
    RESET = '\033[0m'
    
    # On Windows, try to enable ANSI colors
    if platform.system() == 'Windows':
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except:
            # If ANSI colors can't be enabled, use plain text
            if status == 'success':
                print(f"✓ {message}")
            elif status == 'warning':
                print(f"! {message}")
            elif status == 'error':
                print(f"✗ {message}")
            else:
                print(message)
            return
    
    # Print with appropriate color
    if status == 'success':
        print(f"{GREEN}✓ {message}{RESET}")
    elif status == 'warning':
        print(f"{YELLOW}! {message}{RESET}")
    elif status == 'error':
        print(f"{RED}✗ {message}{RESET}")
    else:
        print(message)

def print_header(title):
    """Print a section header."""
    print("\n" + "=" * 40)
    print(title)
    print("=" * 40)

def verify_talib():
    """Main verification function."""
    print_header("TA-Lib Verification Script")
    
    # Check Python version
    py_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    print_colored(f"Python version: {py_version}", "info")
    print_colored(f"Platform: {platform.system()} {platform.release()}", "info")
    
    # Check for TA-Lib import
    print("\nChecking for TA-Lib Python package...")
    try:
        import talib
        print_colored("TA-Lib imported successfully", "success")
        print_colored(f"TA-Lib version: {talib.__version__}", "success")
        print_colored(f"Available functions: {len(talib.get_functions())}", "success")
    except ImportError as e:
        print_colored(f"Failed to import TA-Lib: {e}", "error")
        print_colored("Installation instructions:", "warning")
        if platform.system() == 'Windows':
            print_colored("Run: .\\scripts\\bootstrap_talib.ps1", "warning")
        else:
            print_colored("Run: ./scripts/bootstrap_talib.sh", "warning")
        return False
    
    # Run basic indicator tests
    print("\nRunning indicator tests...")
    try:
        # Create test data
        data = np.random.random(100)
        high, low, close = np.random.random((3, 100)), np.random.random((3, 100)), np.random.random((3, 100))
        volume = np.random.random(100) * 1000
        
        # Test SMA calculation (moving average)
        sma = talib.SMA(close, timeperiod=14)
        print_colored(f"SMA: OK (shape: {sma.shape})", "success")
        
        # Test RSI calculation (momentum)
        rsi = talib.RSI(close, timeperiod=14)
        print_colored(f"RSI: OK (shape: {rsi.shape})", "success")
        
        # Test MACD calculation (trend)
        macd, macd_signal, macd_hist = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
        print_colored(f"MACD: OK (shape: {macd.shape})", "success")
        
        # Test Bollinger Bands (volatility)
        upper, middle, lower = talib.BBANDS(close, timeperiod=20, nbdevup=2, nbdevdn=2)
        print_colored(f"BBANDS: OK (shape: {upper.shape})", "success")
        
        # Test ATR calculation (volatility)
        atr = talib.ATR(high, low, close, timeperiod=14)
        print_colored(f"ATR: OK (shape: {atr.shape})", "success")
        
        # Test Stochastic Oscillator (momentum)
        slowk, slowd = talib.STOCH(high, low, close, fastk_period=5, slowk_period=3, slowk_matype=0, slowd_period=3, slowd_matype=0)
        print_colored(f"STOCH: OK (shape: {slowk.shape})", "success")
        
        # Test ADX (trend strength)
        adx = talib.ADX(high, low, close, timeperiod=14)
        print_colored(f"ADX: OK (shape: {adx.shape})", "success")
        
        # Test OBV (volume)
        obv = talib.OBV(close, volume.astype(int))
        print_colored(f"OBV: OK (shape: {obv.shape})", "success")
        
        # Test AVGDEV (previously problematic)
        if hasattr(talib, 'AVGDEV'):
            avgdev = talib.AVGDEV(close, timeperiod=14)
            print_colored(f"AVGDEV: OK (shape: {avgdev.shape})", "success")
        else:
            print_colored("AVGDEV: Not available in this TA-Lib build", "warning")
        
        print_colored("All indicator tests completed successfully", "success")
    except Exception as e:
        print_colored(f"Error running TA-Lib functions: {e}", "error")
        return False
    
    # Run quick smoke test
    print("\nRunning quick smoke test:")
    try:
        sma_result = talib.SMA(np.arange(10))
        print_colored(f"SMA quick test: {sma_result[0:3]}", "info")
        if sma_result.shape[0] == 10:
            print_colored("Quick smoke test passed", "success")
    except Exception as e:
        print_colored(f"Quick smoke test failed: {e}", "error")
        return False
    
    print("\n✅ TA-Lib verification successful!")
    return True

if __name__ == "__main__":
    success = verify_talib()
    sys.exit(0 if success else 1) 