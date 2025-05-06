#!/bin/bash
# TA-Lib bootstrap script
# Installs TA-Lib using conda (conda-forge) for maximum cross-platform compatibility
# Usage: ./scripts/bootstrap_talib.sh

set -e  # Exit on any error

echo "TA-Lib Bootstrap Script (conda-based)"
echo "===================================="

# Check if conda is installed
if ! command -v conda &> /dev/null; then
    echo "Conda not found. Installing Miniconda..."
    
    # Detect OS for miniconda installer
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "Detected Linux system"
        MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "Detected macOS system"
        if [[ $(uname -m) == "arm64" ]]; then
            echo "Detected Apple Silicon (ARM64)"
            MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-arm64.sh"
        else
            echo "Detected Intel Mac"
            MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-x86_64.sh"
        fi
    elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        echo "Detected Windows system"
        echo "Please install Miniconda manually from: https://docs.conda.io/en/latest/miniconda.html"
        echo "Then run this script again."
        exit 1
    else
        echo "Unsupported OS type: $OSTYPE"
        echo "Please install conda manually and try again."
        exit 1
    fi
    
    # Download and install Miniconda
    INSTALLER_PATH="./miniconda_installer.sh"
    echo "Downloading Miniconda from $MINICONDA_URL"
    if command -v wget &> /dev/null; then
        wget "$MINICONDA_URL" -O "$INSTALLER_PATH"
    elif command -v curl &> /dev/null; then
        curl -L "$MINICONDA_URL" -o "$INSTALLER_PATH"
    else
        echo "Neither wget nor curl found. Please install one of these tools."
        exit 1
    fi
    
    echo "Installing Miniconda..."
    bash "$INSTALLER_PATH" -b -p "$HOME/miniconda3"
    rm "$INSTALLER_PATH"
    
    # Set up conda in current shell
    if [[ "$OSTYPE" == "linux-gnu"* || "$OSTYPE" == "darwin"* ]]; then
        CONDA_PATH="$HOME/miniconda3/bin/conda"
        # Use the more reliable method to activate conda
        source "$HOME/miniconda3/etc/profile.d/conda.sh"
    else
        echo "Please restart your shell and run this script again."
        exit 0
    fi
    
    echo "Conda installed successfully!"
else
    echo "Conda is already installed."
    CONDA_PATH="conda"
    
    # Ensure conda is activated properly in the current shell
    if [[ -f "$(conda info --base)/etc/profile.d/conda.sh" ]]; then
        source "$(conda info --base)/etc/profile.d/conda.sh"
    fi
fi

# Add conda-forge channel
echo "Adding conda-forge channel..."
conda config --add channels conda-forge
conda config --set channel_priority strict

# Handle macOS ARM architecture
if [[ "$OSTYPE" == "darwin"* && $(uname -m) == "arm64" ]]; then
    echo "Detected macOS ARM architecture (Apple Silicon)"
    
    # Try to install with native ARM support first
    if ! conda search -c conda-forge ta-lib | grep -q "osx-arm64"; then
        echo "No native ARM builds found for TA-Lib. Configuring x86_64 emulation..."
        export CONDA_SUBDIR=osx-64
        
        # Permanently configure this environment to use osx-64
        conda config --env --set subdir osx-64
        
        echo "Configured conda to use x86_64 architecture for this installation."
        echo "This will use Rosetta 2 for emulation if needed."
    else
        echo "Native ARM builds for TA-Lib are available. Using osx-arm64 architecture."
    fi
fi

# Check if we're in a conda environment
if [[ -z "${CONDA_DEFAULT_ENV}" ]]; then
    echo "Creating a new conda environment 'talib-env'..."
    conda create -y -n talib-env python=3.10
    
    # Activate the environment
    if [[ "$OSTYPE" == "linux-gnu"* || "$OSTYPE" == "darwin"* ]]; then
        echo "Activating conda environment..."
        # Use the more reliable activation method
        source "$(conda info --base)/etc/profile.d/conda.sh"
        conda activate talib-env
    elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        echo "On Windows, please run: conda activate talib-env"
        echo "Then run: conda install -y -c conda-forge ta-lib numpy"
        exit 0
    fi
else
    echo "Using existing conda environment: $CONDA_DEFAULT_ENV"
fi

# If on macOS ARM, ensure CONDA_SUBDIR is preserved in the environment
if [[ "$OSTYPE" == "darwin"* && $(uname -m) == "arm64" && -n "$CONDA_SUBDIR" ]]; then
    conda env config vars set CONDA_SUBDIR=osx-64
    echo "Set CONDA_SUBDIR=osx-64 for this environment permanently."
    echo "You may need to reactivate the environment: conda activate talib-env"
    
    # Re-activate to apply the environment variable
    conda activate talib-env
fi

# Install TA-Lib and NumPy from conda-forge
echo "Installing TA-Lib from conda-forge..."
# Removed version pinning as suggested for better cross-platform compatibility
conda install -y -c conda-forge ta-lib numpy

# Set TA_LIBRARY_PATH and TA_INCLUDE_PATH for pip installs
CONDA_PREFIX="${CONDA_PREFIX:-$HOME/miniconda3/envs/talib-env}"
export TA_LIBRARY_PATH="$CONDA_PREFIX/lib"
export TA_INCLUDE_PATH="$CONDA_PREFIX/include"
echo "Setting TA_LIBRARY_PATH=$TA_LIBRARY_PATH"
echo "Setting TA_INCLUDE_PATH=$TA_INCLUDE_PATH"

# Platform-specific fallback installation methods
function install_talib_debian_fallback {
    echo "Attempting Debian/Ubuntu fallback installation..."
    
    # Try to enable universe repository if on Ubuntu
    if command -v lsb_release &> /dev/null && [[ "$(lsb_release -si)" == "Ubuntu" ]]; then
        echo "Enabling Universe repository..."
        sudo add-apt-repository universe -y || true
        
        # Switch from Azure mirror to official Ubuntu archive in GitHub Actions
        if [[ -n "$GITHUB_ACTIONS" ]]; then
            echo "GitHub Actions detected, switching to official Ubuntu archive..."
            sudo sed -i 's/azure.archive.ubuntu.com/archive.ubuntu.com/g' /etc/apt/sources.list || true
        fi
    fi
    
    sudo apt-get update
    
    # Try the correct package name (ta-lib not ta-lib-dev)
    echo "Installing TA-Lib C library..."
    if ! sudo apt-get install -y ta-lib libta-lib0; then
        echo "Package installation failed, building from source..."
        
        # Install build dependencies
        sudo apt-get install -y build-essential wget
        
        # Download and build TA-Lib from source
        wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
        tar -xzf ta-lib-0.4.0-src.tar.gz
        cd ta-lib/
        ./configure --prefix=/usr
        make
        sudo make install
        cd ..
        rm -rf ta-lib ta-lib-0.4.0-src.tar.gz
        
        # Run ldconfig to update library cache
        sudo ldconfig
    fi
    
    # Install the Python wrapper
    pip install --no-cache-dir ta-lib
}

function install_talib_macos_fallback {
    echo "Attempting macOS fallback installation..."
    
    if ! command -v brew &> /dev/null; then
        echo "Homebrew not found. Please install Homebrew first."
        echo "Visit https://brew.sh for installation instructions."
        return 1
    fi
    
    # Install TA-Lib with proper architecture flag for Apple Silicon
    if [[ $(uname -m) == "arm64" ]]; then
        echo "Installing TA-Lib for Apple Silicon..."
        arch -arm64 brew install ta-lib
    else
        echo "Installing TA-Lib for Intel Mac..."
        brew install ta-lib
    fi
    
    # Set environment variables
    export TA_LIBRARY_PATH="$(brew --prefix ta-lib)/lib"
    export TA_INCLUDE_PATH="$(brew --prefix ta-lib)/include"
    echo "Setting TA_LIBRARY_PATH=$TA_LIBRARY_PATH"
    echo "Setting TA_INCLUDE_PATH=$TA_INCLUDE_PATH"
    
    # Create symlinks if needed
    if [ -f "$TA_LIBRARY_PATH/libta_lib.dylib" ] && [ ! -f "$TA_LIBRARY_PATH/libta-lib.dylib" ]; then
        echo "Creating symlink from libta_lib.dylib to libta-lib.dylib..."
        ln -sf "$TA_LIBRARY_PATH/libta_lib.dylib" "$TA_LIBRARY_PATH/libta-lib.dylib"
    fi
    
    # Install Python wrapper
    pip install --no-cache-dir ta-lib
}

function install_talib_windows_fallback {
    echo "Attempting Windows fallback installation..."
    
    # Get Python version for the wheel URL
    PY_VER=$(python -c "import sys; print(f'{sys.version_info.major}{sys.version_info.minor}')")
    ARCH="amd64"  # Assuming 64-bit
    
    # Try installing from wheel
    pip install --no-cache-dir https://download.lfd.uci.edu/pythonlibs/archived/ta-lib-0.4.24-cp${PY_VER}-cp${PY_VER}-win_${ARCH}.whl || \
    pip install --no-cache-dir https://github.com/conda-forge/ta-lib-feedstock/files/7028548/ta_lib-0.4.24-cp${PY_VER}-cp${PY_VER}-win_${ARCH}.whl || \
    echo "Wheel installation failed. Using conda as fallback."
}

# Verify installation
echo "Verifying TA-Lib installation..."

# Use a compatible verification method for all platforms
if ! python -c "
import sys
try:
    import numpy as np
    import talib
    print(f'TA-Lib version: {talib.__version__}')
    print(f'Available functions: {len(talib.get_functions())}')
    
    # Test SMA function
    data = np.random.random(100)
    output = talib.SMA(data)
    print(f'SMA calculation successful: {output.shape}')
    print('TA-Lib installation successful! ✓')
    sys.exit(0)
except ImportError as e:
    print(f'Error importing talib: {e}')
    sys.exit(1)
except Exception as e:
    print(f'Error using talib: {e}')
    sys.exit(1)
"; then
    echo "TA-Lib verification failed. Attempting platform-specific fallback installation..."
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        install_talib_debian_fallback
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        install_talib_macos_fallback
    elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        install_talib_windows_fallback
    fi
    
    # Verify again after fallback
    python -c "
    import sys
    try:
        import numpy as np
        import talib
        print(f'TA-Lib version: {talib.__version__}')
        print(f'Available functions: {len(talib.get_functions())}')
        
        # Test SMA function
        data = np.random.random(100)
        output = talib.SMA(data)
        print(f'SMA calculation successful: {output.shape}')
        print('TA-Lib installation successful! ✓')
        sys.exit(0)
    except ImportError as e:
        print(f'Error importing talib: {e}')
        sys.exit(1)
    except Exception as e:
        print(f'Error using talib: {e}')
        sys.exit(1)
    " || echo "TA-Lib installation failed even after fallback attempt."
fi

echo "TA-Lib bootstrap complete! ✓"

# Display usage instructions
echo ""
echo "===================================="
echo "TA-Lib Usage Instructions:"
echo ""
echo "1. Activate the conda environment:"
echo "   conda activate talib-env"
echo ""
echo "2. Import in Python:"
echo "   import talib"
echo "   import numpy as np"
echo ""
echo "3. Example usage:"
echo "   close_prices = np.array([44.55, 44.3, 44.36, 43.82, 44.46, 44.49, 44.7])"
echo "   sma = talib.SMA(close_prices, timeperiod=3)"
echo ""
echo "4. List available functions:"
echo "   print(talib.get_functions())"
echo "===================================="
echo ""
echo "Installation Notes:"
echo "* If you're using this in a CI environment, make sure to set TA_LIBRARY_PATH and TA_INCLUDE_PATH"
echo "* For Debian/Ubuntu, package names vary: try 'ta-lib' or 'libta-lib0'"
echo "* For macOS, ensure brew installs correctly and check for lib naming consistency"
echo "* For macOS ARM (Apple Silicon), Rosetta 2 may be used if native builds aren't available"
echo "* For Windows, pip install may need specific wheel versions"
echo "=====================================" 