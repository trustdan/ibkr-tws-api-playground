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
        echo "Detected Ubuntu/Debian-based system"
        echo "Installing TA-Lib from system package (recommended method)..."
        sudo apt-get update
        sudo apt-get install -y libta-lib-dev
        
        # Verify installation
        if [ -f "/usr/lib/libta-lib.so" ] || [ -f "/usr/lib/libta-lib.so.0" ]; then
            echo "TA-Lib C library installed successfully from package!"
        else
            echo "System package installation failed, falling back to source installation..."
            sudo apt-get install -y build-essential wget autoconf libtool pkg-config
            INSTALL_FROM_SOURCE=1
        fi
    elif command -v yum &> /dev/null; then
        echo "Installing dependencies with yum..."
        sudo yum install -y gcc gcc-c++ make wget autoconf libtool pkgconfig
        INSTALL_FROM_SOURCE=1
    else
        echo "Please install build-essential, wget, autoconf, libtool, and pkg-config manually."
        INSTALL_FROM_SOURCE=1
    fi
elif [[ "$OSTYPE" == "darwin"* ]]; then
    echo "Detected macOS system"
    if command -v brew &> /dev/null; then
        echo "Installing TA-Lib with Homebrew..."
        brew install ta-lib
        
        # Verify installation
        if [ -f "/usr/local/lib/libta_lib.dylib" ] || [ -f "/usr/local/lib/libta-lib.dylib" ]; then
            echo "TA-Lib C library installed successfully from Homebrew!"
        else
            echo "Homebrew installation failed, falling back to source installation..."
            brew install wget automake libtool
            INSTALL_FROM_SOURCE=1
        fi
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

# If system package installation failed or not available, install from source
if [ "$INSTALL_FROM_SOURCE" = "1" ]; then
    echo "Installing TA-Lib from source..."
    
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

    # Create symlinks for the Python wrapper on Linux
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
    
    # Cleanup
    echo "Cleaning up..."
    rm -rf ta-lib-0.4.0-src.tar.gz ta-lib
fi

# Install Python wrapper
echo "Installing TA-Lib Python wrapper..."
pip install numpy
if [ "$INSTALL_FROM_SOURCE" = "1" ]; then
    pip install --no-build-isolation TA-Lib
else
    pip install TA-Lib
fi

# Verify Python wrapper
echo "Verifying Python wrapper installation..."
python3 - <<EOF
import sys
import os

try:
    import ctypes, talib
    # Try loading the library directly
    lib = ctypes.CDLL("libta-lib.so")
    print(f"C library loaded successfully")
    
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
except Exception as e:
    print(f"Error using talib: {e}")
    sys.exit(1)
EOF

echo "TA-Lib bootstrap complete! ✓"
echo "You can now import talib in your Python projects." 