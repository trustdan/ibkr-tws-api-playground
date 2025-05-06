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
        
        # First try to enable Universe repository if on Ubuntu (contains libta-lib-dev)
        if command -v add-apt-repository &> /dev/null; then
            echo "Enabling Universe repository..."
            sudo add-apt-repository universe -y
        else
            echo "add-apt-repository command not found, skipping Universe repository addition"
        fi
        
        # Check if we're on an Azure VM or CI (common in GitHub Actions)
        if grep -q "azure.archive.ubuntu.com" /etc/apt/sources.list; then
            echo "Detected Azure mirror in sources.list, switching to official Ubuntu archive..."
            sudo sed -i 's|http://azure.archive.ubuntu.com/ubuntu|http://archive.ubuntu.com/ubuntu|g' /etc/apt/sources.list
        fi
        
        # Check if libta-lib-dev is available in the repositories
        sudo apt-get update
        
        # Verify Universe is active and libta-lib-dev is available
        echo "Checking if libta-lib-dev is available in repositories:"
        if apt-cache policy libta-lib-dev | grep -q "Candidate:"; then
            echo "libta-lib-dev found in repositories, installing..."
            sudo apt-get install -y libta-lib-dev
            
            # Verify C library exported symbols
            echo "Verifying exported symbols in libta-lib.so:"
            if [ -f "/usr/lib/libta-lib.so" ]; then
                # Check the library with dash in the name (standard location)
                if nm -D /usr/lib/libta-lib.so | grep -q "TA_AVGDEV_Lookback"; then
                    echo "✓ TA_AVGDEV_Lookback symbol found in libta-lib.so"
                    echo "TA-Lib C library installed successfully from package!"
                else
                    echo "Required symbols not found in installed package at /usr/lib/libta-lib.so"
                    echo "Checking alternate filename (libta_lib.so)..."
                    
                    if [ -f "/usr/lib/libta_lib.so" ] && nm -D /usr/lib/libta_lib.so | grep -q "TA_AVGDEV_Lookback"; then
                        echo "✓ TA_AVGDEV_Lookback symbol found in libta_lib.so"
                        echo "Creating symlinks for consistency..."
                        sudo ln -sf /usr/lib/libta_lib.so /usr/lib/libta-lib.so
                        sudo ln -sf /usr/lib/libta_lib.so.0 /usr/lib/libta-lib.so.0
                        sudo ldconfig
                        echo "TA-Lib C library installed successfully from package!"
                    else
                        echo "Required symbols not found in installed package, falling back to source installation..."
                        sudo apt-get install -y build-essential wget autoconf libtool pkg-config
                        INSTALL_FROM_SOURCE=1
                    fi
                fi
            else
                echo "Library file not found at /usr/lib/libta-lib.so"
                if [ -f "/usr/lib/libta_lib.so" ]; then
                    echo "Found library at /usr/lib/libta_lib.so, creating symlinks..."
                    sudo ln -sf /usr/lib/libta_lib.so /usr/lib/libta-lib.so
                    sudo ln -sf /usr/lib/libta_lib.so.0 /usr/lib/libta-lib.so.0
                    sudo ldconfig
                    
                    if nm -D /usr/lib/libta-lib.so | grep -q "TA_AVGDEV_Lookback"; then
                        echo "✓ TA_AVGDEV_Lookback symbol found in libta-lib.so"
                        echo "TA-Lib C library installed successfully from package!"
                    else
                        echo "Required symbols not found even after creating symlinks, falling back to source installation..."
                        sudo apt-get install -y build-essential wget autoconf libtool pkg-config
                        INSTALL_FROM_SOURCE=1
                    fi
                else
                    echo "No library files found, falling back to source installation..."
                    sudo apt-get install -y build-essential wget autoconf libtool pkg-config
                    INSTALL_FROM_SOURCE=1
                fi
            fi
        else
            echo "libta-lib-dev not found in repositories (common on Ubuntu 24.04+)"
            echo "Will install from source instead..."
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
            
            # Run ldconfig again to update the symlinks
            sudo ldconfig
            
            # Verify symlinks exist
            echo "Verifying symlinks:"
            ls -la $LIB_DIR/libta_lib.so*
            ls -la $LIB_DIR/libta-lib.so*
            
            # Verify C library exported symbols (now using the dashed symlink)
            echo "Verifying exported symbols in libta-lib.so:"
            if nm -D $LIB_DIR/libta-lib.so | grep -q "TA_AVGDEV_Lookback"; then
                echo "✓ TA_AVGDEV_Lookback symbol found in libta-lib.so"
            else
                echo "Warning: Required symbols not found in compiled library!"
                echo "Installation might not work correctly."
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
    functions = talib.get_functions()
    print(f"Available functions (sample): {functions[:5]}")
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

# Display installation summary
if [ "$INSTALL_FROM_SOURCE" = "1" ]; then
    echo "Installation method: Built from source"
else
    echo "Installation method: System package"
fi
echo "--------------------------------------"
echo "Verification steps to run manually if needed:"
echo "1. Check library symbols: nm -D /usr/lib/libta-lib.so | grep TA_AVGDEV_Lookback"
echo "2. Test Python wrapper: python -c \"import talib; print(talib.get_functions()[:5])\"" 