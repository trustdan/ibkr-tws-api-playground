# TA-Lib Installation Guide

TA-Lib (Technical Analysis Library) is a widely used library for technical analysis of financial market data. This guide provides cross-platform installation solutions for the common issues encountered when installing TA-Lib.

## Understanding TA-Lib

TA-Lib consists of two main components:
1. A core C/C++ library that performs the calculations
2. A Python wrapper (`talib`) that interfaces with the C library

Most installation issues stem from mismatches between these components.

## Installation Scripts

This repository includes cross-platform installation scripts:

- `scripts/bootstrap_talib.sh` - For Unix-based systems (Linux, macOS)
- `scripts/bootstrap_talib.ps1` - For Windows systems

These scripts provide a consistent installation experience across platforms using conda (recommended method) with fallbacks to platform-specific methods.

## Quick Start

### Unix-based Systems (Linux, macOS)

```bash
# Make the script executable
chmod +x scripts/bootstrap_talib.sh

# Run the installation script
./scripts/bootstrap_talib.sh
```

### Windows

```powershell
# Run the installation script in PowerShell
.\scripts\bootstrap_talib.ps1
```

## Common Issues and Solutions

### Issue 1: Package Not Found on Debian/Ubuntu

**Error**: `Unable to locate package ta-lib-dev`

**Solutions**:
- Try the correct package name: `ta-lib` or `libta-lib0`
- For Ubuntu, enable the universe repository: `sudo add-apt-repository universe`
- In GitHub Actions, switch from Azure mirror: `sudo sed -i 's/azure.archive.ubuntu.com/archive.ubuntu.com/g' /etc/apt/sources.list`
- For newer Ubuntu (24.04+), build from source (handled by the script)

### Issue 2: Library Not Found on macOS

**Error**: Missing library files on macOS, especially Apple Silicon

**Solutions**:
- Use architecture-specific installation: `arch -arm64 brew install ta-lib` for M1/M2 Macs
- Set environment variables:
  ```bash
  export TA_LIBRARY_PATH="$(brew --prefix ta-lib)/lib"
  export TA_INCLUDE_PATH="$(brew --prefix ta-lib)/include"
  ```
- Create symlinks between library naming conventions (handled by the script)

### Issue 3: Windows Installation Issues

**Error**: PowerShell script syntax errors or wheel download failures

**Solutions**:
- Use our PowerShell script which handles Python version detection
- Try multiple wheel sources with appropriate Python version
- Fall back to conda-based installation (handled by the script)

## Manual Installation Methods

If the scripts don't work for your setup, here are platform-specific manual methods:

### Conda (Cross-Platform)

```bash
# Create environment
conda create -n talib-env
conda activate talib-env

# Install from conda-forge
conda install -c conda-forge ta-lib numpy
```

### Linux (Debian/Ubuntu)

```bash
# Install system library
sudo apt-get update
sudo apt-get install ta-lib

# Install Python wrapper
pip install ta-lib
```

### macOS

```bash
# Install with Homebrew
brew install ta-lib

# Set environment variables
export TA_LIBRARY_PATH="$(brew --prefix ta-lib)/lib"
export TA_INCLUDE_PATH="$(brew --prefix ta-lib)/include"

# Install Python wrapper
pip install ta-lib
```

### Windows

```powershell
# Install from wheel (replace XX with your Python version)
pip install https://download.lfd.uci.edu/pythonlibs/archived/ta-lib-0.4.24-cpXX-cpXX-win_amd64.whl
```

## Verification

To verify your installation:

```python
import numpy as np
import talib

# Check version
print(f"TA-Lib version: {talib.__version__}")

# Check available functions
print(f"Available functions: {len(talib.get_functions())}")

# Test calculation
data = np.random.random(100)
output = talib.SMA(data)
print(f"SMA calculation successful: {output.shape}")
```

## CI/CD Integration

For GitHub Actions or other CI environments:

1. For Ubuntu, use our bootstrap script with sudo
2. For macOS, use the bootstrap script which handles arch-specific installation
3. For Windows, use the PowerShell script

## Troubleshooting

If you're still having issues:

1. Check if the C library is properly installed: `ls -la /usr/lib/libta*` or equivalent for your OS
2. Verify environment variables: `echo $TA_LIBRARY_PATH` and `echo $TA_INCLUDE_PATH`
3. Check Python wrapper: `pip show ta-lib`
4. For compilation issues, ensure you have development tools: `build-essential` on Debian/Ubuntu

## References

- [TA-Lib documentation](https://mrjbq7.github.io/ta-lib/)
- [TA-Lib GitHub repository](https://github.com/mrjbq7/ta-lib)
- [Conda-forge TA-Lib package](https://anaconda.org/conda-forge/ta-lib) 