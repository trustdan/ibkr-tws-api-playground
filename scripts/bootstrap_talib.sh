#!/bin/bash
# TA-Lib bootstrap script
# Installs both TA-Lib C library and Python wrapper
# Usage: ./scripts/bootstrap_talib.sh

set -e  # Exit on any error

echo "TA-Lib Bootstrap Script"
echo "======================="

# Check OS type and install dependencies
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "Detected Linux system"
    if command -v apt-get &> /dev/null; then
        echo "Installing dependencies with apt..."
        sudo apt-get update
        sudo apt-get install -y build-essential wget autoconf libtool pkg-config
    elif command -v yum &> /dev/null; then
        echo "Installing dependencies with yum..."
        sudo yum install -y gcc gcc-c++ make wget autoconf libtool pkgconfig
    else
        echo "Please install build-essential, wget, autoconf, libtool, and pkg-config manually."
    fi
elif [[ "$OSTYPE" == "darwin"* ]]; then
    echo "Detected macOS system"
    if command -v brew &> /dev/null; then
        echo "Installing dependencies with Homebrew..."
        brew install wget automake libtool
    else
        echo "Please install Homebrew (https://brew.sh) and try again."
        exit 1
    fi
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    echo "Detected Windows system"
    echo "For Windows, we recommend using conda or the pre-built wheels."
    echo "See: https://github.com/mrjbq7/ta-lib#windows"
    exit 0
else
    echo "Unsupported OS type: $OSTYPE"
    echo "Please install TA-Lib manually."
    exit 1
fi

# Download and install TA-Lib C library
echo "Downloading TA-Lib C library source..."
wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
tar -xzf ta-lib-0.4.0-src.tar.gz
cd ta-lib/

# Configure and install
echo "Building and installing TA-Lib C library..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    ./configure --prefix=/usr/local
else
    ./configure --prefix=/usr
fi
make
sudo make install
cd ..

# Run ldconfig to update shared library cache (Linux only)
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "Updating shared library cache with ldconfig..."
    sudo ldconfig
fi

# Find the installed TA-Lib shared library
echo "Locating installed TA-Lib library..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    LIB_DIR="/usr/local/lib"
else
    LIB_DIR="/usr/lib"
fi
TA_LIB_FILES=$(find $LIB_DIR -name "libta_lib*" 2>/dev/null)
echo "Found TA-Lib files: $TA_LIB_FILES"

# Create symlinks for the Python wrapper
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "Creating symlinks for Python wrapper..."
    ACTUAL_LIB_PATH=$(find $LIB_DIR -name "libta_lib.so*" -type f | head -1)
    if [ -n "$ACTUAL_LIB_PATH" ]; then
        echo "Creating symlink from $ACTUAL_LIB_PATH to $LIB_DIR/libta-lib.so"
        sudo ln -sf $ACTUAL_LIB_PATH $LIB_DIR/libta-lib.so
        
        if [[ "$ACTUAL_LIB_PATH" == *".0.0.0" ]]; then
            BASE_LIB=${ACTUAL_LIB_PATH%.0.0.0}
            echo "Creating symlink from ${BASE_LIB}.0 to $LIB_DIR/libta-lib.so.0"
            sudo ln -sf ${BASE_LIB}.0 $LIB_DIR/libta-lib.so.0
        else
            echo "Creating symlink from $ACTUAL_LIB_PATH to $LIB_DIR/libta-lib.so.0"
            sudo ln -sf $ACTUAL_LIB_PATH $LIB_DIR/libta-lib.so.0
        fi
    fi
fi

# Verify C library and symbols
echo "Verifying installed C library..."
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "Checking dynamic symbols:"
    nm -D $ACTUAL_LIB_PATH | grep -E "TA_AVGDEV_Lookback|TA_ATR|TA_SMA" || echo "Warning: Expected symbols not found!"
    
    echo "Available TA-Lib libraries in the system:"
    ldconfig -p | grep -i ta

    # Verify direct library loading
    echo "Verifying direct library loading..."
    python3 - <<EOF
import ctypes
import os

try:
    # Try with absolute path first
    lib = ctypes.CDLL("$ACTUAL_LIB_PATH")
    print("C library loaded successfully with absolute path")
    
    # Then try with just the name to test loader path
    lib = ctypes.CDLL("libta-lib.so")
    print("C library loaded successfully with loader path")
except Exception as e:
    print(f"Error loading library: {e}")
    exit(1)
EOF
fi

# Set environment variables for Python wrapper installation
echo "Setting up environment for Python wrapper installation..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    export TA_LIBRARY_PATH=/usr/local/lib
    export TA_INCLUDE_PATH=/usr/local/include
    export LDFLAGS="-L/usr/local/lib"
    export CFLAGS="-I/usr/local/include"
else
    export TA_LIBRARY_PATH=/usr/lib
    export TA_INCLUDE_PATH=/usr/include
    export LDFLAGS="-L/usr/lib"
    export CFLAGS="-I/usr/include"
fi

# Install Python wrapper
echo "Installing TA-Lib Python wrapper..."
pip install numpy
pip install --no-build-isolation TA-Lib

# Verify Python wrapper
echo "Verifying Python wrapper installation..."
python3 - <<EOF
import sys
import os

try:
    import talib
    print(f"TA-Lib version: {talib.__version__}")
    print(f"Available functions (sample): {talib.get_functions()[:5]}")
    print(f"ATR function available: {hasattr(talib, 'ATR')}")
    print(f"SMA function available: {hasattr(talib, 'SMA')}")
    
    # Test a simple function call
    import numpy as np
    close = np.random.random(100)
    output = talib.SMA(close)
    print(f"SMA calculation successful: {output.shape}")
    
    print("\nTA-Lib installation successful! ✓")
except ImportError as e:
    print(f"Error importing talib: {e}")
    sys.exit(1)
EOF

# Cleanup
echo "Cleaning up..."
rm -rf ta-lib-0.4.0-src.tar.gz ta-lib

echo "TA-Lib bootstrap complete! ✓"
echo "You can now import talib in your Python projects." 