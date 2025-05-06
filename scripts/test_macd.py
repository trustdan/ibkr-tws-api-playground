#!/usr/bin/env python
# Test script specifically for MACD indicator
# Used to debug the failing MACD test on macOS

import sys
import numpy as np
import platform

def test_macd():
    """Test MACD indicator with more robust error handling."""
    print("\nRunning MACD test with enhanced data and error handling")
    print(f"Python version: {sys.version}")
    print(f"Platform: {platform.platform()}")
    
    try:
        # Import TA-Lib
        import talib
        from talib import abstract
        
        print(f"TA-Lib version: {talib.__version__}")
        
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
        
        # Test standard MACD
        print("\nTesting standard MACD function:")
        macd, macdsignal, macdhist = talib.MACD(
            close, 
            fastperiod=12, 
            slowperiod=26, 
            signalperiod=9
        )
        
        # Check for NaN values
        nan_count = np.sum(np.isnan(macd))
        valid_count = len(macd) - nan_count
        print(f"MACD output shape: {macd.shape}")
        print(f"NaN values: {nan_count}, Valid values: {valid_count}")
        print(f"First 5 valid values: {macd[~np.isnan(macd)][:5]}")
        
        if valid_count > 0:
            print("✓ Standard MACD: Success")
        else:
            print("✗ Standard MACD: All values are NaN")
        
        # Test abstract MACD
        print("\nTesting abstract MACD function:")
        
        # Convert to the format expected by abstract API (dict with 'close' key)
        input_data = {'close': close}
        
        # Call abstract MACD
        macd_result = abstract.MACD(
            input_data,
            fastperiod=12, 
            slowperiod=26, 
            signalperiod=9
        )
        
        if isinstance(macd_result, dict):
            # For newer versions that return a dict
            print("Abstract API returned a dictionary")
            for key, arr in macd_result.items():
                nan_count = np.sum(np.isnan(arr))
                valid_count = len(arr) - nan_count
                print(f"{key} - Shape: {arr.shape}, NaN: {nan_count}, Valid: {valid_count}")
                
            has_valid_values = any(np.sum(~np.isnan(arr)) > 0 for arr in macd_result.values())
        else:
            # For older versions that return a tuple
            print("Abstract API returned a tuple")
            macd, macdsignal, macdhist = macd_result
            
            for i, (name, arr) in enumerate([("macd", macd), ("signal", macdsignal), ("hist", macdhist)]):
                nan_count = np.sum(np.isnan(arr))
                valid_count = len(arr) - nan_count
                print(f"{name} - Shape: {arr.shape}, NaN: {nan_count}, Valid: {valid_count}")
            
            has_valid_values = np.sum(~np.isnan(macd)) > 0 or np.sum(~np.isnan(macdsignal)) > 0 or np.sum(~np.isnan(macdhist)) > 0
        
        if has_valid_values:
            print("✓ Abstract MACD: Success")
            return True
        else:
            print("✗ Abstract MACD: All values are NaN")
            return False
        
    except ImportError as e:
        print(f"Failed to import TA-Lib: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_macd()
    sys.exit(0 if success else 1) 