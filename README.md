# Auto Vertical Spread Trader

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://github.com/yourusername/auto-vertical-spread-trader/graphs/commit-activity)
[![Tests](https://github.com/yourusername/auto-vertical-spread-trader/actions/workflows/python-tests.yml/badge.svg)](https://github.com/yourusername/auto-vertical-spread-trader/actions/workflows/python-tests.yml)
[![codecov](https://codecov.io/gh/yourusername/auto-vertical-spread-trader/branch/main/graph/badge.svg)](https://codecov.io/gh/yourusername/auto-vertical-spread-trader)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A modular, production-ready system for automated vertical spread trading with Interactive Brokers.

## Overview

This system scans for technical setups on S&P 500 stocks and trades vertical option spreads based on four strategies:

1. **Bull Pullbacks** - Long call verticals on bullish stocks pulling back to 50-day MA
2. **Bear Rallies** - Long put verticals on bearish stocks rallying to 50-day MA
3. **High Base** - Long call verticals on stocks consolidating near 52-week highs
4. **Low Base** - Long put verticals on stocks consolidating near 52-week lows

All trades include automated stop losses based on ATR.

## Recent Updates

- **Improved TA-Lib Installation**: We've enhanced TA-Lib installation across all platforms:
  - Switched from Ubuntu to Debian for CI builds (more reliable `ta-lib-dev` package availability)
  - Added dynamic Homebrew prefix detection for macOS (`brew --prefix ta-lib`)
  - Enhanced Windows wheel installation with proper version detection
  - Implemented comprehensive test suite for TA-Lib indicator verification

- **Comprehensive Verification**: Added `scripts/verify_talib.sh` to test 8+ indicator types and ensure proper library linking

- **CI Performance**: Optimized CI builds with caching for pip and Homebrew dependencies

## Features

- **Fundamental Filtering**: Market cap ≥ $10B, price > $20, optionable stocks
- **Technical Analysis**: 50 DMA trend analysis, volume filtering, consolidation patterns
- **Option Selection**: Delta-based strike selection, cost limits, R:R ratio enforcement
- **Risk Management**: ATR-based stop losses, position limits, daily trade limits
- **Execution**: Late-day trade entries, clean reconnection handling, email alerts

## Requirements

- Python 3.8+
- Interactive Brokers account with TWS or IB Gateway
- TA-Lib (technical analysis library)

## Installation

### 1. Installing TA-Lib

TA-Lib is a critical dependency for this system and requires a two-step installation: the C library must be installed first, followed by the Python wrapper.

#### Platform-Specific One-Liners

The simplest installation method depends on your operating system:

**Conda (cross-platform):**
```bash
# The easiest cross-platform option if you use conda
conda install -c conda-forge ta-lib
```

**Debian:**
```bash
# Debian has a native ta-lib-dev package
sudo apt-get update && sudo apt-get install -y ta-lib-dev && pip install TA-Lib
```

**Ubuntu (22.04 or earlier):**
```bash
# libta-lib-dev is in the Universe repository, which needs to be enabled first
sudo add-apt-repository universe && sudo apt-get update && sudo apt-get install -y libta-lib-dev && pip install TA-Lib
```

**Azure-based CI environments (including GitHub Actions):**
```bash
# Use Debian container for CI instead of Ubuntu for reliable TA-Lib installation
# In GitHub Actions, use:
container:
  image: debian:bookworm-slim
# Then install ta-lib-dev (without 'lib' prefix)
apt-get update && apt-get install -y --no-install-recommends ta-lib-dev
```

**Ubuntu 24.04 and newer:** 
Ubuntu 24.04 (Noble Numbat) doesn't include the `libta-lib-dev` package, so you'll need to build from source (use our bootstrap script below) or switch to Debian.

**macOS:**
```bash
# Install with Homebrew and use dynamic prefix detection
brew install ta-lib
export LDFLAGS="-L$(brew --prefix ta-lib)/lib"
export CPPFLAGS="-I$(brew --prefix ta-lib)/include"
pip install --no-build-isolation TA-Lib
```

**Windows:**
```bash
# Install with correct Python version in wheel URL
python -c "import sys; print(f'pip install https://github.com/TA-Lib/ta-lib-python/releases/download/TA_Lib-0.4.28/TA_Lib-0.4.28-cp{sys.version_info.major}{sys.version_info.minor}-cp{sys.version_info.major}{sys.version_info.minor}-win_amd64.whl')" | cmd
```

Or using conda:
```bash
conda install -c conda-forge ta-lib
```

#### Verifying Your Installation

To verify TA-Lib is properly installed, we provide a quick verification script:

```bash
# Run the fail-fast verification script
./scripts/verify_talib.sh

# If it fails, you'll need to install TA-Lib
if [ $? -ne 0 ]; then
  echo "TA-Lib installation failed - run scripts/bootstrap_talib.sh and try again"
  exit 1
fi
```

You can also perform manual verification (works on all platforms):

```bash
# Basic verification
python -c "import talib; print('TA-Lib installed successfully! Functions:', talib.get_functions()[:3])"

# Complete verification (Linux/Mac)
# 1. Confirm Universe is active and package is available (Ubuntu)
apt-cache policy libta-lib-dev

# 2. Verify the C Library exported the needed symbols
nm -D /usr/lib/libta-lib.so | grep TA_AVGDEV_Lookback

# 3. Smoke-test the Python wrapper
python - <<'EOF'
import ctypes, talib
ctypes.CDLL('libta-lib.so')
print('Loaded:', talib.get_functions()[:5])
EOF
```

If the first command returns a list of function names (like `['ADX', 'ADXR', 'APO']`), your installation is working correctly.

#### Automated Installation: Bootstrap Script

For a guided installation that handles your specific environment, we provide a bootstrap script:

```bash
# Clone the repository if you haven't already
git clone https://github.com/yourusername/auto-vertical-spread-trader.git
cd auto-vertical-spread-trader

# Make the script executable
chmod +x scripts/bootstrap_talib.sh

# Run the bootstrap script
./scripts/bootstrap_talib.sh
```

This script will:
- Detect your operating system
- Install necessary dependencies (using system packages when available)
- Set up TA-Lib appropriately for your platform
- Verify the installation works correctly

#### Detailed Installation Instructions

If you need more control over the installation process:

##### Ubuntu/Debian
```bash
# Enable Universe repository where libta-lib-dev is located
sudo add-apt-repository universe

# For Azure-based CI systems (GitHub Actions), switch to official mirror
if grep -q "azure.archive.ubuntu.com" /etc/apt/sources.list; then
  sudo sed -i 's|http://azure.archive.ubuntu.com/ubuntu|http://archive.ubuntu.com/ubuntu|g' /etc/apt/sources.list
fi

# Install the C library and development headers
sudo apt-get update
sudo apt-get install -y libta-lib-dev

# Install the Python wrapper
pip install TA-Lib
```

##### macOS
Using Homebrew:
```bash
# Install the C library
brew install ta-lib

# Install the Python wrapper
pip install TA-Lib
```

##### Windows

1. **Using pre-built wheels** (recommended):
   - Download the appropriate wheel from [Christoph Gohlke's repository](https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib)
   - Select the version matching your Python version and architecture (e.g., `TA_Lib-0.4.27-cp39-cp39-win_amd64.whl`)
   - Install with pip:
     ```
     pip install TA_Lib-0.4.27-cp39-cp39-win_amd64.whl
     ```

2. **Building from source**:
   - Download TA-Lib C library from [TA-Lib.org](https://ta-lib.org/hdr_dw.html)
   - Unzip to `C:\ta-lib`
   - Add to environment variables: `LIB` path should include `C:\ta-lib\lib`, and `INCLUDE` should include `C:\ta-lib\include`
   - Install the Python wrapper: `pip install ta-lib`

### 2. Installing the Package

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/auto-vertical-spread-trader.git
   cd auto-vertical-spread-trader
   ```

2. Create a virtual environment and install dependencies:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Verify TA-Lib installation:
   ```python
   python -c "import talib; print('TA-Lib installed successfully!')"
   ```

## Configuration

Edit `config.py` to adjust parameters:

- Connection settings (`IB_HOST`, `IB_PORT`)
- Risk parameters (`MAX_POSITIONS`, `MAX_DAILY_TRADES`)
- Strategy parameters (ATR multiples, delta thresholds)
- Email alerts (optional)

### Key Configuration Options

| Parameter | Default | Description |
|-----------|---------|-------------|
| `MAX_POSITIONS` | 10 | Maximum open positions allowed |
| `MAX_DAILY_TRADES` | 2 | Maximum new trades per day |
| `MIN_DELTA` | 0.30 | Minimum option delta for spreads |
| `MAX_DELTA` | 0.50 | Maximum option delta for spreads |
| `STOP_LOSS_ATR_MULT` | 1.5 | ATR multiplier for stop losses |
| `TARGET_DAYS_TO_EXPIRY` | 45 | Target days to expiry for options |
| `MAX_SPREAD_COST` | 500 | Maximum cost per spread ($) |

## Environment Variables

The application supports using environment variables for sensitive configuration:

- `EMAIL_PASSWORD` - For email alert notifications
- `IB_ACCOUNT_ID` - Your IB account identifier

We recommend using a `.env` file with [python-dotenv](https://pypi.org/project/python-dotenv/) to manage these variables.

### Security Note

**Important:** Never commit your `.env` file or any file containing credentials to version control. The repository includes a `.gitignore` file that excludes `.env` by default. For CI/CD pipelines, use environment secrets provided by your CI platform (like GitHub Secrets) rather than committing sensitive information.

## Usage

1. Start TWS or IB Gateway and ensure API connections are enabled.
2. Run the application:
   ```
   python runner.py
   ```
   
   Or if installed as a package:
   ```
   auto-trader
   ```

3. The system will:
   - Connect to Interactive Brokers
   - Load and filter the universe
   - Run scans after 3 PM ET each trading day
   - Place trades that meet all criteria
   - Monitor open positions for stop losses

### Quickstart Examples

**Run a specific scan without trading:**
```bash
python runner.py --scan bull_pullbacks
```

**Run the system in paper trading mode:**
```bash
python runner.py --paper
```

**Run in REPL or your own script:**
```python
from auto_vertical_spread_trader import AutoVerticalSpreadTrader

# Initialize the trader
trader = AutoVerticalSpreadTrader()
trader.initialize()

# Run specific scans
results = trader.run_scan("bull_pullbacks")
print(f"Found {len(results)} potential trades")

# Or run entries if during trading hours
trader.run_entries_if_time()
```

### Troubleshooting

Common issues and solutions:

- **Connection Errors**: Ensure TWS/Gateway is running and API connections are enabled (Configure > API > Settings)

- **TA-Lib Installation Issues**: 
  - If encountering import errors, first try our `scripts/bootstrap_talib.sh` script
  - For "undefined symbol" errors on Linux, use the system package: `sudo apt-get install libta-lib-dev` 
  - Library not found: Make sure to enable Universe repository with `sudo add-apt-repository universe`
  - Unable to locate package libta-lib-dev in Azure/GitHub Actions: Switch to official Ubuntu mirror with `sudo sed -i 's|http://azure.archive.ubuntu.com/ubuntu|http://archive.ubuntu.com/ubuntu|g' /etc/apt/sources.list`
  - Common error: `ImportError: libta_lib.so.0: cannot open shared object file`
    - Run `sudo ldconfig` after installation to update the shared library cache
    - For Ubuntu/Debian, use the system package which handles this automatically
  - For Windows, using pre-built wheels is strongly recommended

- **Rate Limiting**: If you encounter "Pacing Violation" errors, increase the `QUERY_DELAY` in config.py

- **Missing Data**: For "No market data permissions" errors, ensure your IB account is subscribed to relevant data feeds

Check `auto_trader.log` for detailed error information.

## File Structure

- `config.py` - Configuration parameters and constants
- `universe.py` - Universe loading and filtering logic
- `scans.py` - Technical scanning functions for trade setups
- `executor.py` - Option spread selection and trade execution
- `exits.py` - Profit-target and stop-loss logic
- `monitor.py` - Position monitoring and ATR-based stop management
- `runner.py` - Main application loop and command handling
- `auto_vertical_spread_trader.py` - Core trader implementation

## Testing

Run tests with pytest:
```bash
pytest
```

Run tests with coverage report:
```bash
pytest --cov=auto_vertical_spread_trader
```

Tests are located in the `tests/` directory and validate strategy logic, option selection, and risk management.

## Code Quality

This project uses several tools to maintain code quality:

- **Black**: Code formatting
- **Flake8**: Linting
- **MyPy**: Type checking
- **isort**: Import sorting

You can run all checks using the pre-configured tools:

```bash
# Format code
black .

# Sort imports
isort .

# Run linting
flake8 .

# Run type checking
mypy .
```

## Continuous Integration

This project uses GitHub Actions for continuous integration, running tests and code quality checks on every push and pull request.

## Logging

Logs are stored in `auto_trader.log` with detailed information on scans, trades, and errors.

## License

MIT License - See LICENSE file for details.

## Contributing

Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to contribute to this project.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for a history of changes to this project.

## Acknowledgments

- [IB Insync](https://github.com/erdewit/ib_insync) for the Interactive Brokers API
- [TA-Lib](https://github.com/mrjbq7/ta-lib) for technical analysis

### Version Information

This project uses:

- **TA-Lib C library**: version 0.4.0 (most reliable and widely compatible version)
- **Python wrapper**: 
  - Linux/macOS: Use version matching your platform (built against C library 0.4.0)
  - Windows: Pre-built wheels version 0.4.27 or 0.4.28 from Christoph Gohlke's repository

For CI environments, we recommend pinning these exact versions to ensure reproducibility:
- Ubuntu 22.04: `libta-lib-dev` from Universe repository
- Ubuntu 24.04+: Source build from ta-lib-0.4.0
- macOS: `brew install ta-lib`
- Windows: Use appropriate wheel for your Python version from [Gohlke's repository](https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib)
- Conda (all platforms): `conda install -c conda-forge ta-lib`