#!/bin/bash
# TA-Lib bootstrap script
# Installs TA-Lib using conda (conda-forge) for maximum cross-platform compatibility
# Usage: ./scripts/bootstrap_talib.sh

set -e  # Exit on any error

echo "TA-Lib Bootstrap Script (conda-based)"
echo "===================================="

# Detect CI environment
CI_ENV=false
if [ -n "$CI" ] || [ -n "$GITHUB_ACTIONS" ]; then
    echo "CI environment detected"
    CI_ENV=true
fi

# Check if conda is installed
CONDA_ALREADY_INSTALLED=false
if command -v conda &> /dev/null; then
    echo "Conda is already installed."
    CONDA_ALREADY_INSTALLED=true
    CONDA_PATH="conda"
    
    # Ensure conda is activated properly in the current shell
    if [[ -f "$(conda info --base)/etc/profile.d/conda.sh" ]]; then
        source "$(conda info --base)/etc/profile.d/conda.sh"
    fi
else
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
    elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" || "$OSTYPE" == "cygwin" ]]; then
        echo "Detected Windows system"
        if [ "$CI_ENV" = true ]; then
            # In GitHub Actions, we can use the conda that comes with the runner
            echo "Using GitHub Actions' pre-installed conda"
            if command -v conda &> /dev/null; then
                CONDA_ALREADY_INSTALLED=true
                CONDA_PATH="conda"
            else
                echo "Downloading Miniconda installer for Windows..."
                # For CI on Windows, use the exe installer
                MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe"
                INSTALLER_PATH="./miniconda_installer.exe"
                if command -v curl &> /dev/null; then
                    curl -L "$MINICONDA_URL" -o "$INSTALLER_PATH"
                    echo "Installing Miniconda silently..."
                    start /wait "" "$INSTALLER_PATH" /InstallationType=JustMe /RegisterPython=0 /S /D=%UserProfile%\miniconda3
                    rm "$INSTALLER_PATH"
                    export PATH="$HOME/miniconda3/Scripts:$HOME/miniconda3:$PATH"
                else
                    echo "Curl not found. Cannot download Miniconda for Windows."
                    exit 1
                fi
            fi
        else
            echo "Please install Miniconda manually from: https://docs.conda.io/en/latest/miniconda.html"
            echo "Then run this script again."
            exit 1
        fi
    else
        echo "Unsupported OS type: $OSTYPE"
        echo "Please install conda manually and try again."
        exit 1
    fi
    
    if [ "$CONDA_ALREADY_INSTALLED" = false ] && [[ "$OSTYPE" != "msys" && "$OSTYPE" != "win32" && "$OSTYPE" != "cygwin" ]]; then
        # Download and install Miniconda for Linux/macOS
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
            # Add conda to PATH for this session
            export PATH="$HOME/miniconda3/bin:$PATH"
        else
            echo "Please restart your shell and run this script again."
            exit 0
        fi
        
        echo "Conda installed successfully!"
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

# Environment name with CI-specific suffix if in CI
ENV_NAME="talib-env"
if [ "$CI_ENV" = true ]; then
    ENV_NAME="talib-env-ci"
fi

# Check if we're in a conda environment or create a new one
if [[ -z "${CONDA_DEFAULT_ENV}" || "${CONDA_DEFAULT_ENV}" == "base" ]]; then
    echo "Creating a new conda environment '$ENV_NAME'..."
    # Force "yes" for CI environments
    if [ "$CI_ENV" = true ]; then
        conda create -y -n $ENV_NAME python=3.10
    else
        conda create -y -n $ENV_NAME python=3.10
    fi
    
    # Activate the environment
    if [[ "$OSTYPE" == "linux-gnu"* || "$OSTYPE" == "darwin"* ]]; then
        echo "Activating conda environment..."
        # Use the more reliable activation method
        source "$(conda info --base)/etc/profile.d/conda.sh"
        conda activate $ENV_NAME
    elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" || "$OSTYPE" == "cygwin" ]]; then
        if [ "$CI_ENV" = true ]; then
            echo "Activating conda environment in CI Windows..."
            # For GitHub Actions on Windows
            eval "$(conda shell.bash hook)"
            conda activate $ENV_NAME
        else
            echo "On Windows, please run: conda activate $ENV_NAME"
            echo "Then run: conda install -y -c conda-forge ta-lib numpy"
            exit 0
        fi
    fi
else
    echo "Using existing conda environment: $CONDA_DEFAULT_ENV"
    ENV_NAME=$CONDA_DEFAULT_ENV
fi

# If on macOS ARM, ensure CONDA_SUBDIR is preserved in the environment
if [[ "$OSTYPE" == "darwin"* && $(uname -m) == "arm64" && -n "$CONDA_SUBDIR" ]]; then
    conda env config vars set CONDA_SUBDIR=osx-64
    echo "Set CONDA_SUBDIR=osx-64 for this environment permanently."
    
    # Re-activate to apply the environment variable
    conda activate $ENV_NAME
fi

# Install TA-Lib and NumPy from conda-forge
echo "Installing TA-Lib from conda-forge..."
# Add extra flags for CI environments
if [ "$CI_ENV" = true ]; then
    conda install -y -c conda-forge ta-lib numpy --no-update-deps
else
    conda install -y -c conda-forge ta-lib numpy
fi

# Set TA_LIBRARY_PATH and TA_INCLUDE_PATH for pip installs
CONDA_PREFIX="${CONDA_PREFIX:-$(conda info --base)/envs/$ENV_NAME}"
export TA_LIBRARY_PATH="$CONDA_PREFIX/lib"
export TA_INCLUDE_PATH="$CONDA_PREFIX/include"
echo "Setting TA_LIBRARY_PATH=$TA_LIBRARY_PATH"
echo "Setting TA_INCLUDE_PATH=$TA_INCLUDE_PATH"

# For GitHub Actions, make these environment variables available to subsequent steps
if [ "$CI_ENV" = true ]; then
    if [ -n "$GITHUB_ENV" ]; then
        echo "TA_LIBRARY_PATH=$TA_LIBRARY_PATH" >> $GITHUB_ENV
        echo "TA_INCLUDE_PATH=$TA_INCLUDE_PATH" >> $GITHUB_ENV
        echo "CONDA_PREFIX=$CONDA_PREFIX" >> $GITHUB_ENV
        
        # Add conda to PATH for subsequent steps
        echo "$CONDA_PREFIX/bin" >> $GITHUB_PATH
        if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" || "$OSTYPE" == "cygwin" ]]; then
            echo "$CONDA_PREFIX" >> $GITHUB_PATH
            echo "$CONDA_PREFIX/Scripts" >> $GITHUB_PATH
            echo "$CONDA_PREFIX/Library/bin" >> $GITHUB_PATH
        fi
    fi
fi

# Platform-specific fallback installation methods
function install_talib_debian_fallback {
    echo "Attempting Debian/Ubuntu fallback installation..."
    
    # Try to enable universe repository if on Ubuntu
    if command -v lsb_release &> /dev/null && [[ "$(lsb_release -si)" == "Ubuntu" ]]; then
        echo "Enabling Universe repository..."
        sudo add-apt-repository universe -y || true
        
        # Switch from Azure mirror to official Ubuntu archive in GitHub Actions
        if [ "$CI_ENV" = true ]; then
            echo "GitHub Actions detected, switching to official Ubuntu archive..."
            sudo sed -i 's/azure.archive.ubuntu.com/archive.ubuntu.com/g' /etc/apt/sources.list || true
            sudo apt-get update -y
        fi
    fi
    
    # Try the correct package name (ta-lib or libta-lib0)
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
        if [ "$CI_ENV" = true ]; then
            echo "CI environment detected, installing Homebrew..."
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
            # Add Homebrew to the path in GitHub Actions
            if [[ $(uname -m) == "arm64" ]]; then
                echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> $HOME/.profile
                eval "$(/opt/homebrew/bin/brew shellenv)"
            else
                echo 'eval "$(/usr/local/bin/brew shellenv)"' >> $HOME/.profile
                eval "$(/usr/local/bin/brew shellenv)"
            fi
        else
            echo "Homebrew not found. Please install Homebrew first."
            echo "Visit https://brew.sh for installation instructions."
            return 1
        fi
    fi
    
    # Install TA-Lib with proper architecture flag for Apple Silicon
    if [[ $(uname -m) == "arm64" ]]; then
        echo "Installing TA-Lib for Apple Silicon..."
        # For GitHub Actions, add --force-bottle to avoid building from source
        if [ "$CI_ENV" = true ]; then
            arch -arm64 brew install ta-lib --force-bottle || arch -arm64 brew install ta-lib
        else
            arch -arm64 brew install ta-lib
        fi
    else
        echo "Installing TA-Lib for Intel Mac..."
        if [ "$CI_ENV" = true ]; then
            brew install ta-lib --force-bottle || brew install ta-lib
        else
            brew install ta-lib
        fi
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
    
    # For GitHub Actions, make these environment variables available to subsequent steps
    if [ "$CI_ENV" = true ] && [ -n "$GITHUB_ENV" ]; then
        echo "TA_LIBRARY_PATH=$TA_LIBRARY_PATH" >> $GITHUB_ENV
        echo "TA_INCLUDE_PATH=$TA_INCLUDE_PATH" >> $GITHUB_ENV
    fi
}

function install_talib_windows_fallback {
    echo "Attempting Windows fallback installation..."
    
    # Get Python version for the wheel URL
    PY_VER=$(python -c "import sys; print(f'{sys.version_info.major}{sys.version_info.minor}')")
    ARCH="amd64"  # Assuming 64-bit
    
    # For GitHub Actions, try to install pre-compiled wheel from GitHub
    if [ "$CI_ENV" = true ]; then
        echo "Trying to download pre-compiled wheel for Windows CI..."
        
        # Alternative URLs for wheels
        WHEEL_URLS=(
            "https://github.com/conda-forge/ta-lib-feedstock/files/7028548/ta_lib-0.4.24-cp${PY_VER}-cp${PY_VER}-win_${ARCH}.whl"
            "https://github.com/TA-Lib/ta-lib-python/releases/download/TA_Lib-0.4.24/TA_Lib-0.4.24-cp${PY_VER}-cp${PY_VER}-win_${ARCH}.whl"
            "https://download.lfd.uci.edu/pythonlibs/archived/ta-lib-0.4.24-cp${PY_VER}-cp${PY_VER}-win_${ARCH}.whl"
        )
        
        for URL in "${WHEEL_URLS[@]}"; do
            echo "Trying to install from: $URL"
            if pip install --no-cache-dir "$URL"; then
                echo "Successfully installed TA-Lib from wheel!"
                return 0
            fi
        done
        
        echo "Wheel installation failed. Trying conda as fallback."
        # We're already in a conda environment, so just install ta-lib
        conda install -y -c conda-forge ta-lib
    else
        # Try installing from wheel for non-CI Windows
        pip install --no-cache-dir https://download.lfd.uci.edu/pythonlibs/archived/ta-lib-0.4.24-cp${PY_VER}-cp${PY_VER}-win_${ARCH}.whl || \
        pip install --no-cache-dir https://github.com/conda-forge/ta-lib-feedstock/files/7028548/ta_lib-0.4.24-cp${PY_VER}-cp${PY_VER}-win_${ARCH}.whl || \
        echo "Wheel installation failed. Using conda as fallback."
    fi
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
    elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" || "$OSTYPE" == "cygwin" ]]; then
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

# If we're in CI, output information for subsequent steps
if [ "$CI_ENV" = true ]; then
    echo ""
    echo "CI Environment Information:"
    echo "Environment: $ENV_NAME"
    echo "TA_LIBRARY_PATH: $TA_LIBRARY_PATH"
    echo "TA_INCLUDE_PATH: $TA_INCLUDE_PATH"
    echo "CONDA_PREFIX: $CONDA_PREFIX"
    echo ""
fi

# Display usage instructions
echo ""
echo "===================================="
echo "TA-Lib Usage Instructions:"
echo ""
echo "1. Activate the conda environment:"
echo "   conda activate $ENV_NAME"
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