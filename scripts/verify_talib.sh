#!/bin/bash
# Comprehensive TA-Lib verification script
# This script runs extended tests on TA-Lib functionality
# Usage: bash scripts/verify_talib.sh

set -e  # Exit on any error

# Define terminal colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}==========================================${NC}"
echo -e "${BLUE}Comprehensive TA-Lib Verification Script${NC}"
echo -e "${BLUE}==========================================${NC}"

# Check Python version
PYTHON_VERSION=$(python --version)
echo -e "Python version: ${YELLOW}$PYTHON_VERSION${NC}"

# Check platform
PLATFORM=$(python -c "import platform; print(platform.platform())")
echo -e "Platform: ${YELLOW}$PLATFORM${NC}"

# Create a temporary Python script for comprehensive verification
VERIFY_SCRIPT=$(cat << 'EOF'
import sys
import numpy as np
import platform
import traceback

def test_talib():
    print(f"\nRunning comprehensive TA-Lib tests...")
    success_count = 0
    failure_count = 0
    tests = []
    
    try:
        import talib
        from talib import abstract
        print(f"TA-Lib version: {talib.__version__}")
        print(f"Available functions: {len(talib.get_functions())}")
        
        # Test data generation
        print("\nGenerating test data...")
        data_length = 200
        close = np.random.random(data_length)
        open_price = np.random.random(data_length)
        high = np.maximum(close, open_price) + np.random.random(data_length) * 0.1
        low = np.minimum(close, open_price) - np.random.random(data_length) * 0.1
        volume = np.random.randint(1, 1000, size=data_length).astype(np.float64)  # Generate integer-like values but keep as float64
        
        # Generate test cases for various function groups
        tests = [
            # Moving Averages
            {"name": "SMA", "func": lambda: talib.SMA(close, timeperiod=14)},
            {"name": "EMA", "func": lambda: talib.EMA(close, timeperiod=14)},
            {"name": "WMA", "func": lambda: talib.WMA(close, timeperiod=14)},
            {"name": "DEMA", "func": lambda: talib.DEMA(close, timeperiod=14)},
            {"name": "TEMA", "func": lambda: talib.TEMA(close, timeperiod=14)},
            {"name": "TRIMA", "func": lambda: talib.TRIMA(close, timeperiod=14)},
            {"name": "KAMA", "func": lambda: talib.KAMA(close, timeperiod=14)},
            {"name": "MAMA", "func": lambda: talib.MAMA(close, fastlimit=0.5, slowlimit=0.05)},
            
            # Momentum Indicators
            {"name": "RSI", "func": lambda: talib.RSI(close, timeperiod=14)},
            {"name": "MACD", "func": lambda: talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)},
            {"name": "STOCH", "func": lambda: talib.STOCH(high, low, close, fastk_period=5, slowk_period=3, slowk_matype=0, slowd_period=3, slowd_matype=0)},
            {"name": "STOCHRSI", "func": lambda: talib.STOCHRSI(close, timeperiod=14, fastk_period=5, fastd_period=3, fastd_matype=0)},
            {"name": "ADX", "func": lambda: talib.ADX(high, low, close, timeperiod=14)},
            {"name": "ADXR", "func": lambda: talib.ADXR(high, low, close, timeperiod=14)},
            {"name": "CCI", "func": lambda: talib.CCI(high, low, close, timeperiod=14)},
            {"name": "MOM", "func": lambda: talib.MOM(close, timeperiod=10)},
            
            # Volume Indicators
            {"name": "OBV", "func": lambda: talib.OBV(close, volume)},
            {"name": "AD", "func": lambda: talib.AD(high, low, close, volume)},
            {"name": "ADOSC", "func": lambda: talib.ADOSC(high, low, close, volume, fastperiod=3, slowperiod=10)},
            
            # Volatility Indicators
            {"name": "ATR", "func": lambda: talib.ATR(high, low, close, timeperiod=14)},
            {"name": "NATR", "func": lambda: talib.NATR(high, low, close, timeperiod=14)},
            {"name": "TRANGE", "func": lambda: talib.TRANGE(high, low, close)},
            {"name": "BBANDS", "func": lambda: talib.BBANDS(close, timeperiod=20, nbdevup=2, nbdevdn=2, matype=0)},
            
            # Pattern Recognition
            {"name": "CDL3INSIDE", "func": lambda: talib.CDL3INSIDE(open_price, high, low, close)},
            {"name": "CDLENGULFING", "func": lambda: talib.CDLENGULFING(open_price, high, low, close)},
            {"name": "CDLHAMMER", "func": lambda: talib.CDLHAMMER(open_price, high, low, close)},
            
            # Abstract API Test
            {"name": "Abstract RSI", "func": lambda: abstract.RSI(close, timeperiod=14)},
            {"name": "Abstract MACD", "func": lambda: abstract.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)},
        ]
        
        print(f"\nRunning {len(tests)} indicator tests:")
        print("=" * 50)
        
        # Run all tests
        for test in tests:
            try:
                result = test["func"]()
                if isinstance(result, tuple):
                    # Check if all values in the tuple are valid arrays
                    all_valid = all(isinstance(arr, np.ndarray) and not np.isnan(arr).all() for arr in result)
                    if all_valid:
                        success_count += 1
                        print(f"✓ {test['name']} - Success")
                    else:
                        failure_count += 1
                        print(f"✗ {test['name']} - Array contains all NaN values")
                else:
                    # Check if the result is a valid array
                    if isinstance(result, np.ndarray) and not np.isnan(result).all():
                        success_count += 1
                        print(f"✓ {test['name']} - Success")
                    else:
                        failure_count += 1
                        print(f"✗ {test['name']} - Result invalid or contains all NaN values")
            except Exception as e:
                failure_count += 1
                print(f"✗ {test['name']} - Failed: {str(e)}")
                traceback.print_exc()
        
        print("=" * 50)
        print(f"Total tests: {len(tests)}")
        print(f"Successful: {success_count}")
        print(f"Failed: {failure_count}")
        
        if failure_count == 0:
            print("\n✅ All TA-Lib tests passed successfully!")
            return True
        else:
            print(f"\n❌ {failure_count} tests failed.")
            return False
            
    except ImportError as e:
        print(f"Failed to import TA-Lib: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_talib()
    sys.exit(0 if success else 1)
EOF
)

# Write the verification script to a temporary file
TEMP_FILE=$(mktemp)
echo "$VERIFY_SCRIPT" > "$TEMP_FILE"

# Run the comprehensive verification
echo -e "\n${BLUE}Running comprehensive TA-Lib tests...${NC}"
python "$TEMP_FILE"
TEST_RESULT=$?

# Clean up
rm "$TEMP_FILE"

# Final status
if [ $TEST_RESULT -eq 0 ]; then
    echo -e "\n${GREEN}✅ TA-Lib verification completed successfully!${NC}"
    exit 0
else
    echo -e "\n${RED}❌ TA-Lib verification failed!${NC}"
    exit 1
fi