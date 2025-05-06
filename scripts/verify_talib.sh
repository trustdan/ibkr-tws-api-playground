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
    # First detect if we're on Debian or Ubuntu
    if [ -f "/etc/debian_version" ]; then
        DEBIAN_VERSION=$(cat /etc/debian_version)
        if grep -q "Ubuntu" /etc/issue 2>/dev/null; then
            echo "Detected Ubuntu-based system"
            DISTRO="ubuntu"
        else
            echo "Detected Debian-based system (version: $DEBIAN_VERSION)"
            DISTRO="debian"
        fi
        
        # Check if the package is installed
        if [ "$DISTRO" = "debian" ] && dpkg -l | grep -q "ta-lib-dev"; then
            echo "✓ Found ta-lib-dev package (Debian)"
        elif [ "$DISTRO" = "ubuntu" ] && dpkg -l | grep -q "libta-lib-dev"; then
            echo "✓ Found libta-lib-dev package (Ubuntu)"
        fi
    fi
    
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
    # macOS - check both system and homebrew locations with dynamic prefix detection
    if command -v brew &> /dev/null; then
        PREFIX=$(brew --prefix ta-lib 2>/dev/null || echo "/usr/local")
        echo "Checking for TA-Lib in Homebrew prefix: $PREFIX"
        
        LIB_PATHS=(
            "$PREFIX/lib/libta_lib.dylib"
            "$PREFIX/lib/libta-lib.dylib"
            "/usr/local/lib/libta_lib.dylib"
            "/usr/local/lib/libta-lib.dylib"
        )
    else
        LIB_PATHS=(
            "/usr/local/lib/libta_lib.dylib"
            "/usr/local/lib/libta-lib.dylib"
        )
    fi
    
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
        echo "! Then: export LDFLAGS=\"-L\$(brew --prefix ta-lib)/lib\" CPPFLAGS=\"-I\$(brew --prefix ta-lib)/include\""
    fi
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" || "$OSTYPE" == "cygwin" ]]; then
    # Windows - check for Python wheel installation and provide better guidance
    echo "! Windows system detected - checking for TA-Lib Python wheel"
    
    # Try to use Powershell if available for better Windows detection
    if command -v powershell &>/dev/null; then
        PYTHON_SITE=$(powershell -Command "python -c 'import site; print(site.getsitepackages()[0])'")
        PYTHON_VERSION=$(powershell -Command "python -c 'import sys; print(f\"{sys.version_info.major}{sys.version_info.minor}\")'")
        ARCH="win_amd64"  # Assume 64-bit Windows
        
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
        echo "! On Windows, install TA-Lib using one of these methods:"
        
        if [ -n "$PYTHON_VERSION" ]; then
            echo "! 1. Download and install a pre-built wheel:"
            echo "!    pip install https://github.com/TA-Lib/ta-lib-python/releases/download/TA_Lib-0.4.28/TA_Lib-0.4.28-cp${PYTHON_VERSION}-cp${PYTHON_VERSION}-${ARCH}.whl"
        else
            echo "! 1. Download and install a pre-built wheel matching your Python version"
        fi
        
        echo "! 2. Install from conda-forge (if using Anaconda/Miniconda):"
        echo "!    conda install -c conda-forge ta-lib"
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
    
    # Expanded test for multiple indicators to ensure comprehensive functionality
    if $PYTHON_CMD -c "
import talib, numpy as np
try:
    # Create test data
    data = np.random.random(100)
    high, low, close = np.random.random((3, 100)), np.random.random((3, 100)), np.random.random((3, 100))
    volume = np.random.random(100) * 1000
    
    print('Testing common TA-Lib indicators:')
    
    # Test SMA calculation (moving average)
    sma = talib.SMA(close, timeperiod=14)
    print('✓ SMA: OK (shape:', sma.shape, ')')
    
    # Test RSI calculation (momentum)
    rsi = talib.RSI(close, timeperiod=14)
    print('✓ RSI: OK (shape:', rsi.shape, ')')
    
    # Test MACD calculation (trend)
    macd, macd_signal, macd_hist = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
    print('✓ MACD: OK (shape:', macd.shape, ')')
    
    # Test Bollinger Bands (volatility)
    upper, middle, lower = talib.BBANDS(close, timeperiod=20, nbdevup=2, nbdevdn=2)
    print('✓ BBANDS: OK (shape:', upper.shape, ')')
    
    # Test ATR calculation (volatility)
    atr = talib.ATR(high, low, close, timeperiod=14)
    print('✓ ATR: OK (shape:', atr.shape, ')')
    
    # Test Stochastic Oscillator (momentum)
    slowk, slowd = talib.STOCH(high, low, close, fastk_period=5, slowk_period=3, slowk_matype=0, slowd_period=3, slowd_matype=0)
    print('✓ STOCH: OK (shape:', slowk.shape, ')')
    
    # Test ADX (trend strength)
    adx = talib.ADX(high, low, close, timeperiod=14)
    print('✓ ADX: OK (shape:', adx.shape, ')')
    
    # Test OBV (volume)
    obv = talib.OBV(close, volume.astype(int))
    print('✓ OBV: OK (shape:', obv.shape, ')')
    
    # Test AVGDEV (previously problematic)
    if hasattr(talib, 'AVGDEV'):
        avgdev = talib.AVGDEV(close, timeperiod=14)
        print('✓ AVGDEV: OK (shape:', avgdev.shape, ')')
    else:
        print('⚠ AVGDEV: Not available in this TA-Lib build')
    
    print('✓ All indicator tests completed successfully')
    print('Available functions:', len(talib.get_functions()))
    
except Exception as e:
    print('Error running TA-Lib functions:', e)
    exit(1)
" 2>/dev/null; then
        echo "✓ Comprehensive indicator test successful"
    else
        echo "✗ Comprehensive indicator test failed (wrapper installed but not working correctly)"
        exit 1
    fi
else
    echo "✗ Python wrapper import failed"
    if [ "$FOUND_LIB" -eq 1 ]; then
        echo "! C library found but Python wrapper missing or broken"
        
        if [[ "$OSTYPE" == "darwin"* ]]; then
            echo "! For macOS, make sure to set the dynamic prefix:"
            echo "! export LDFLAGS=\"-L\$(brew --prefix ta-lib)/lib\" CPPFLAGS=\"-I\$(brew --prefix ta-lib)/include\""
            echo "! pip install --no-build-isolation TA-Lib"
        elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
            echo "! For Linux, create symbolic links if needed:"
            echo "! sudo ln -sf /usr/lib/libta_lib.so /usr/lib/libta-lib.so"
            echo "! sudo ln -sf /usr/lib/libta_lib.so.0 /usr/lib/libta-lib.so.0"
            echo "! sudo ldconfig"
            echo "! pip install TA-Lib"
        else
            echo "! Run: pip install TA-Lib"
        fi
    else
        echo "! Both C library and Python wrapper are missing"
        echo "! Run: ./scripts/bootstrap_talib.sh"
    fi
    exit 1
fi

# Run quick smoke test
echo -e "\nRunning quick smoke test:"
$PYTHON_CMD - <<EOF
import talib, numpy as np
sma_result = talib.SMA(np.arange(10))
print("SMA quick test:", sma_result[0:3])
if sma_result.shape[0] == 10:
    print("✓ Quick smoke test passed")
EOF

echo -e "\n✅ TA-Lib verification successful!"
exit 0 