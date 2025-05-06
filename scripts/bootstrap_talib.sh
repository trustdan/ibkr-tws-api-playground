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
    
    # Check for Debian vs Ubuntu
    if [ -f "/etc/debian_version" ]; then
        DEBIAN_VERSION=$(cat /etc/debian_version)
        if grep -q "Ubuntu" /etc/issue 2>/dev/null; then
            echo "Detected Ubuntu-based system"
            DISTRO="ubuntu"
        else
            echo "Detected Debian-based system (version: $DEBIAN_VERSION)"
            DISTRO="debian"
        fi
        
        # Update package lists
        sudo apt-get update
        
        if [ "$DISTRO" = "debian" ]; then
            # On Debian, the package is ta-lib-dev (without 'lib' prefix)
            echo "Checking if ta-lib-dev is available in Debian repositories:"
            if apt-cache policy ta-lib-dev | grep -q "Candidate:"; then
                echo "ta-lib-dev found in repositories, installing..."
                sudo apt-get install -y ta-lib-dev
                
                # Verify C library exported symbols
                echo "Verifying exported symbols:"
                if [ -f "/usr/lib/libta_lib.so" ]; then
                    # Debian typically uses underscore in the filename
                    if nm -D /usr/lib/libta_lib.so | grep -q "TA_AVGDEV_Lookback"; then
                        echo "✓ TA_AVGDEV_Lookback symbol found in libta_lib.so"
                        echo "Creating symlinks for Python wrapper..."
                        sudo ln -sf /usr/lib/libta_lib.so /usr/lib/libta-lib.so
                        sudo ln -sf /usr/lib/libta_lib.so.0 /usr/lib/libta-lib.so.0
                        sudo ldconfig
                        echo "TA-Lib C library installed successfully from Debian package!"
                    else
                        echo "Required symbols not found in installed package, falling back to source installation..."
                        sudo apt-get install -y build-essential wget autoconf libtool pkg-config
                        INSTALL_FROM_SOURCE=1
                    fi
                elif [ -f "/usr/lib/libta-lib.so" ]; then
                    # Check if dash version exists
                    if nm -D /usr/lib/libta-lib.so | grep -q "TA_AVGDEV_Lookback"; then
                        echo "✓ TA_AVGDEV_Lookback symbol found in libta-lib.so"
                        echo "TA-Lib C library installed successfully from Debian package!"
                    else
                        echo "Required symbols not found in installed package, falling back to source installation..."
                        sudo apt-get install -y build-essential wget autoconf libtool pkg-config
                        INSTALL_FROM_SOURCE=1
                    fi
                else
                    echo "Library file not found, falling back to source installation..."
                    sudo apt-get install -y build-essential wget autoconf libtool pkg-config
                    INSTALL_FROM_SOURCE=1
                fi
            else
                echo "ta-lib-dev not found in repositories"
                echo "Will install from source instead..."
                sudo apt-get install -y build-essential wget autoconf libtool pkg-config
                INSTALL_FROM_SOURCE=1
            fi
        else
            # Ubuntu handling (existing code)
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
        
        # Use dynamic prefix detection
        PREFIX=$(brew --prefix ta-lib)
        echo "TA-Lib installed at: $PREFIX"
        
        # Verify installation
        if [ -f "$PREFIX/lib/libta_lib.dylib" ] || [ -f "$PREFIX/lib/libta-lib.dylib" ]; then
            echo "TA-Lib C library installed successfully from Homebrew!"
            # Set environment variables for proper linking
            export LDFLAGS="-L$PREFIX/lib"
            export CPPFLAGS="-I$PREFIX/include"
            echo "Set LDFLAGS=$LDFLAGS"
            echo "Set CPPFLAGS=$CPPFLAGS"
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
    echo "For Windows, we recommend using conda or pre-built wheels."
    
    # Get Python version for wheel URL
    PYTHON_VERSION=$(python -c "import sys; print(f'{sys.version_info.major}{sys.version_info.minor}')")
    ARCH="win_amd64"  # Assume 64-bit Windows
    
    echo "Detected Python version: $PYTHON_VERSION"
    echo "Options for installation:"
    
    echo "1. Using pip with pre-compiled wheel:"
    echo "   pip install https://github.com/TA-Lib/ta-lib-python/releases/download/TA_Lib-0.4.28/TA_Lib-0.4.28-cp${PYTHON_VERSION}-cp${PYTHON_VERSION}-${ARCH}.whl"
    
    echo "2. Using conda (recommended if you have Anaconda/Miniconda):"
    echo "   conda install -c conda-forge ta-lib"
    
    echo "Please choose one of these methods to install TA-Lib."
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
        if [ -n "$PREFIX" ]; then
            # Use Homebrew prefix if available
            export TA_LIBRARY_PATH=$PREFIX/lib
            export TA_INCLUDE_PATH=$PREFIX/include
            export LDFLAGS="-L$PREFIX/lib"
            export CFLAGS="-I$PREFIX/include"
        else
            export TA_LIBRARY_PATH=/usr/local/lib
            export TA_INCLUDE_PATH=/usr/local/include
            export LDFLAGS="-L/usr/local/lib"
            export CFLAGS="-I/usr/local/include"
        fi
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
if [ "$INSTALL_FROM_SOURCE" = "1" ] || [[ "$OSTYPE" == "darwin"* ]]; then
    # Use no-build-isolation for source builds or macOS with Homebrew
    pip install --no-build-isolation TA-Lib
else
    pip install TA-Lib
fi

# Verify Python wrapper
echo "Verifying Python wrapper installation..."
python3 - <<EOF || python - <<EOF
import sys
import os

try:
    import ctypes, talib
    # Try loading the library directly
    if sys.platform.startswith('linux'):
        try:
            lib = ctypes.CDLL("libta-lib.so")
            print("C library loaded successfully (dash version)")
        except:
            try:
                lib = ctypes.CDLL("libta_lib.so")
                print("C library loaded successfully (underscore version)")
            except Exception as e:
                print(f"Warning: Could not load C library directly: {e}")
    
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
echo "Troubleshooting tips if you encounter issues:"
echo ""
echo "For Linux:"
echo "1. Create symbolic links between naming conventions:"
echo "   sudo ln -sf /usr/lib/libta_lib.so.0 /usr/lib/libta-lib.so.0"
echo "   sudo ln -sf /usr/lib/libta_lib.so /usr/lib/libta-lib.so"
echo "   sudo ldconfig"
echo ""
echo "For macOS:"
echo "1. Set the correct Homebrew prefix:"
echo "   export LDFLAGS=\"-L\$(brew --prefix ta-lib)/lib\""
echo "   export CPPFLAGS=\"-I\$(brew --prefix ta-lib)/include\""
echo "   pip install --no-build-isolation TA-Lib"
echo ""
echo "For Windows:"
echo "1. Install from conda-forge:"
echo "   conda install -c conda-forge ta-lib"
echo "2. Or use precompiled wheel with correct Python version:"
echo "   pip install https://github.com/TA-Lib/ta-lib-python/releases/download/TA_Lib-0.4.28/TA_Lib-0.4.28-cp311-cp311-win_amd64.whl"
echo ""
echo "Verification command:"
echo "python -c \"import talib, numpy as np; print('TA-Lib SMA output:', talib.SMA(np.random.random(100))[:5])\"" 