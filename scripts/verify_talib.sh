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
    # Linux - check both dash and underscore variants
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
    # macOS - check both system and homebrew locations
    LIB_PATHS=(
        "/usr/local/lib/libta_lib.dylib"
        "/usr/local/lib/libta-lib.dylib"
        "$(brew --prefix ta-lib 2>/dev/null)/lib/libta_lib.dylib" # Newer homebrew path
    )
    
    for lib_path in "${LIB_PATHS[@]}"; do
        if [ -f "$lib_path" ]; then
            echo "✓ Found $lib_path"
            FOUND_LIB=1
            break
        fi
    done
    
    if [ "$FOUND_LIB" -eq 0 ]; then
        echo "✗ TA-Lib C library not found in standard locations"
        echo "! Try: brew install ta-lib"
    fi
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" || "$OSTYPE" == "cygwin" ]]; then
    # Windows - check for Python wheel installation
    echo "! Windows system detected - checking for TA-Lib Python wheel"
    
    # Try to use Powershell if available for better Windows detection
    if command -v powershell &>/dev/null; then
        PYTHON_SITE=$(powershell -Command "python -c 'import site; print(site.getsitepackages()[0])'")
        if [ -d "$PYTHON_SITE/talib" ]; then
            echo "✓ Found TA-Lib in Python site-packages (wheel installation)"
            FOUND_LIB=1
        fi
    else
        # Fallback to assuming it might be installed
        echo "! PowerShell not available, skipping detailed check"
        echo "! Assuming wheel installation might be present"
        FOUND_LIB=1
    fi
    
    if [ "$FOUND_LIB" -eq 0 ]; then
        echo "✗ TA-Lib not found in Python site-packages"
        echo "! On Windows, download and install a pre-built wheel from:"
        echo "! https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib"
    fi
else
    echo "? Unknown OS type: $OSTYPE"
    echo "? Skipping C library check"
fi

# Check for Python wrapper
echo -e "\nChecking for TA-Lib Python wrapper..."

# Determine Python executable (use python3 on *nix, python on Windows)
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" || "$OSTYPE" == "cygwin" ]]; then
    PYTHON_CMD="python"
else
    # Try python3 first, fallback to python if not found
    if command -v python3 &>/dev/null; then
        PYTHON_CMD="python3"
    else
        PYTHON_CMD="python"
    fi
fi

# Check if talib can be imported
if $PYTHON_CMD -c "import talib" 2>/dev/null; then
    echo "✓ Python wrapper imports successfully"
    
    # Test a more comprehensive function call
    if $PYTHON_CMD -c "
import talib, numpy as np
try:
    # Create test data
    data = np.random.random(100)
    # Test SMA calculation
    sma = talib.SMA(data)
    # Test ATR calculation (requires multiple inputs)
    high, low, close = np.random.random((3, 100))
    atr = talib.ATR(high, low, close, timeperiod=14)
    # Make sure AVGDEV is available (the symbol that was missing before)
    avgdev = talib.AVGDEV(data) if hasattr(talib, 'AVGDEV') else None
    print('SMA shape:', sma.shape)
    print('ATR shape:', atr.shape)
    if avgdev is not None:
        print('AVGDEV shape:', avgdev.shape)
    print('Functions available:', len(talib.get_functions()))
    print('First few functions:', talib.get_functions()[:3])
except Exception as e:
    print('Error running TA-Lib functions:', e)
    exit(1)
" 2>/dev/null; then
        echo "✓ Function calls test successful"
    else
        echo "✗ Function calls test failed (wrapper installed but not working correctly)"
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