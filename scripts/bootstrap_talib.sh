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
        eval "$("$HOME/miniconda3/bin/conda" shell.bash hook)"
    else
        echo "Please restart your shell and run this script again."
        exit 0
    fi
    
    echo "Conda installed successfully!"
else
    echo "Conda is already installed."
    CONDA_PATH="conda"
fi

# Add conda-forge channel
echo "Adding conda-forge channel..."
conda config --add channels conda-forge
conda config --set channel_priority strict

# Check if we're in a conda environment
if [[ -z "${CONDA_DEFAULT_ENV}" ]]; then
    echo "Creating a new conda environment 'talib-env'..."
    conda create -y -n talib-env python=3.9
    
    # Activate the environment
    if [[ "$OSTYPE" == "linux-gnu"* || "$OSTYPE" == "darwin"* ]]; then
        echo "Activating conda environment..."
        eval "$(conda shell.bash hook)"
        conda activate talib-env
    elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        echo "On Windows, please run: conda activate talib-env"
        echo "Then run: conda install -y -c conda-forge ta-lib numpy"
        exit 0
    fi
else
    echo "Using existing conda environment: $CONDA_DEFAULT_ENV"
fi

# Install TA-Lib and NumPy from conda-forge
echo "Installing TA-Lib from conda-forge..."
conda install -y -c conda-forge ta-lib=0.4.24 numpy

# Verify installation
echo "Verifying TA-Lib installation..."

# Use a compatible verification method for all platforms
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
except ImportError as e:
    print(f'Error importing talib: {e}')
    sys.exit(1)
except Exception as e:
    print(f'Error using talib: {e}')
    sys.exit(1)
"

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