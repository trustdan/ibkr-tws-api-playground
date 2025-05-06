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

- **Migrated from TA-Lib to pandas-ta**: We've replaced TA-Lib with pandas-ta for technical indicators:
  - No C/C++ dependencies required
  - Easier installation across all platforms
  - DataFrame-centric API that's more intuitive
  - Same functionality but with simpler code

- **Improved Technical Analysis**: Enhanced indicator functionality with pandas-ta's extensive indicator library
  
- **Simplified Installation**: Removed complex TA-Lib installation requirements

- **CI Performance**: Optimized CI builds with no compilation required for indicators

## Features

- **Fundamental Filtering**: Market cap ≥ $10B, price > $20, optionable stocks
- **Technical Analysis**: 50 DMA trend analysis, volume filtering, consolidation patterns
- **Option Selection**: Delta-based strike selection, cost limits, R:R ratio enforcement
- **Risk Management**: ATR-based stop losses, position limits, daily trade limits
- **Execution**: Late-day trade entries, clean reconnection handling, email alerts

## Requirements

- Python 3.8+
- Interactive Brokers account with TWS or IB Gateway
- pandas-ta (technical analysis library)

## Installation

### Installing the Package

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

3. Verify pandas-ta installation:
   ```
   python scripts/verify_pandas_ta.py
   ```

## Migration from TA-Lib to pandas-ta

We've migrated from TA-Lib to pandas-ta for several key benefits:

1. **Simplified Installation**: No C/C++ compilation required
2. **DataFrame-Centric API**: More intuitive and pythonic usage
3. **Cross-Platform Compatibility**: Works consistently across all operating systems
4. **Extensive Indicator Library**: Over 130+ technical indicators available

### Key API Differences

TA-Lib and pandas-ta have different syntax patterns. Here's a comparison:

**TA-Lib (old):**
```python
import talib
df['ATR14'] = talib.ATR(df['high'], df['low'], df['close'], timeperiod=14)
df['RSI14'] = talib.RSI(df['close'], timeperiod=14)
```

**pandas-ta (new):**
```python
import pandas_ta as ta
df['ATR14'] = df.ta.atr(length=14)
df['RSI14'] = df.ta.rsi(length=14)
```

### Verifying the Migration

Run the verification script to ensure all indicators work correctly:
```
python scripts/verify_pandas_ta.py
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

- **pandas-ta Installation Issues**: 
  - If encountering import errors, first try our `scripts/bootstrap_pandas_ta.sh` script
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
- [pandas-ta](https://github.com/twopirllc/pandas-ta) for technical analysis indicators

### Version Information

This project uses:

- **pandas-ta**: version 0.3.0b0 or higher
- **pandas**: version 1.3.0 or higher 
- **numpy**: version 1.20.0 or higher

For CI environments, we recommend pinning these exact versions to ensure reproducibility.