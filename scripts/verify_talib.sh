#!/bin/bash
# TA-Lib verification script
# Quickly checks if TA-Lib is properly installed and functioning
# Usage: ./scripts/verify_talib.sh

set -e  # Exit on any error

echo "TA-Lib Verification Script"
echo "=========================="

# Check for the C library
echo "Checking for TA-Lib C library..."
FOUND_LIB=0

if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    if [ -f "/usr/lib/libta-lib.so" ]; then
        echo "✓ Found libta-lib.so"
        # Check for required symbols
        if nm -D /usr/lib/libta-lib.so | grep -q "TA_AVGDEV_Lookback"; then
            echo "✓ TA_AVGDEV_Lookback symbol found in libta-lib.so"
            FOUND_LIB=1
        else
            echo "✗ TA_AVGDEV_Lookback symbol NOT found in libta-lib.so"
        fi
    elif [ -f "/usr/lib/libta_lib.so" ]; then
        echo "✓ Found libta_lib.so (underscore version)"
        # Check for required symbols
        if nm -D /usr/lib/libta_lib.so | grep -q "TA_AVGDEV_Lookback"; then
            echo "✓ TA_AVGDEV_Lookback symbol found in libta_lib.so"
            echo "! Warning: Python wrapper expects libta-lib.so (with dash)"
            echo "! Run: sudo ln -sf /usr/lib/libta_lib.so /usr/lib/libta-lib.so && sudo ldconfig"
            FOUND_LIB=1
        else
            echo "✗ TA_AVGDEV_Lookback symbol NOT found in libta_lib.so"
        fi
    else
        echo "✗ Neither libta-lib.so nor libta_lib.so found"
    fi
elif [[ "$OSTYPE" == "darwin"* ]]; then
    if [ -f "/usr/local/lib/libta_lib.dylib" ]; then
        echo "✓ Found libta_lib.dylib"
        FOUND_LIB=1
    elif [ -f "/usr/local/lib/libta-lib.dylib" ]; then
        echo "✓ Found libta-lib.dylib"
        FOUND_LIB=1
    else
        echo "✗ TA-Lib C library not found in /usr/local/lib"
    fi
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    echo "! Windows system detected - skipping C library check"
    echo "! On Windows, using pre-built wheels is recommended"
    FOUND_LIB=1  # Assume success on Windows with wheel installation
else
    echo "? Unknown OS type: $OSTYPE"
    echo "? Skipping C library check"
fi

# Check for Python wrapper
echo -e "\nChecking for TA-Lib Python wrapper..."
if python3 -c "import talib" 2>/dev/null; then
    echo "✓ Python wrapper imports successfully"
    # Test a simple function
    if python3 -c "import talib, numpy; print('SMA test:', talib.SMA(numpy.random.random(10)).shape)" 2>/dev/null; then
        echo "✓ Function call test successful"
    else
        echo "✗ Function call test failed (wrapper installed but not working correctly)"
        exit 1
    fi
else
    echo "✗ Python wrapper import failed"
    if [ "$FOUND_LIB" -eq 1 ]; then
        echo "! C library found but Python wrapper missing or broken"
        echo "! Run: pip install TA-Lib"
    else
        echo "! Both C library and Python wrapper are missing"
        echo "! Run: ./scripts/bootstrap_talib.sh"
    fi
    exit 1
fi

echo -e "\n✅ TA-Lib verification successful!"
exit 0 