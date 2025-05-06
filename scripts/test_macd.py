#!/usr/bin/env python
# Test script specifically for MACD indicator
# Used to debug the failing MACD test on macOS

import sys
import numpy as np
import pandas as pd
import platform

def test_macd():
    """Test MACD indicator with more robust error handling."""
    print("\nRunning MACD test with enhanced data and error handling")
    print(f"Python version: {sys.version}")
    print(f"Platform: {platform.platform()}")
    
    try:
        # Import pandas-ta
        import pandas_ta as ta
        
        print(f"pandas-ta is available")
        
        # Create test data with sufficient length for MACD
        data_length = 300  # MACD requires longer history to initialize
        seed = 42  # Use fixed seed for reproducibility
        np.random.seed(seed)
        
        # Create random but trendy data
        close = np.zeros(data_length, dtype=np.float64)
        close[0] = 100.0
        
        # Add trend component and random noise
        for i in range(1, data_length):
            trend = 0.01 * (i % 100)  # Gentle uptrend with cycles
            noise = np.random.normal(0, 0.5)  # Small random noise
            close[i] = close[i-1] * (1 + trend/100 + noise/100)
        
        # Create pandas DataFrame
        df = pd.DataFrame({'close': close})
        
        # Test MACD using pandas-ta
        print("\nTesting pandas-ta MACD function:")
        macd_result = ta.macd(df['close'], fast=12, slow=26, signal=9)
        
        # Check for NaN values
        if macd_result is not None:
            for column in macd_result.columns:
                arr = macd_result[column].values
                nan_count = np.sum(np.isnan(arr))
                valid_count = len(arr) - nan_count
                print(f"{column} - Shape: {arr.shape}, NaN: {nan_count}, Valid: {valid_count}")
                if valid_count > 0:
                    print(f"First 5 valid values for {column}: {arr[~np.isnan(arr)][:5]}")
            
            has_valid_values = any(np.sum(~np.isnan(macd_result[col].values)) > 0 for col in macd_result.columns)
            
            if has_valid_values:
                print("✓ pandas-ta MACD: Success")
                return True
            else:
                print("✗ pandas-ta MACD: All values are NaN")
                return False
        else:
            print("✗ pandas-ta MACD: Function returned None")
            return False
        
    except ImportError as e:
        print(f"Failed to import pandas-ta: {e}")
        print("To install pandas-ta, run: pip install pandas-ta>=0.3.0b0")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_macd()
    sys.exit(0 if success else 1) 