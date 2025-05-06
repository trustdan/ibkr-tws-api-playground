"""
Auto Vertical Spread Trader
A modular system for identifying and trading vertical option spreads on IB TWS.

This package provides automated scanning, selection, and risk management
for bull pullbacks, bear rallies, high base, and low base trading strategies.
"""

__version__ = "1.0.0"

from auto_vertical_spread_trader.auto_vertical_spread_trader import AutoVerticalSpreadTrader
from auto_vertical_spread_trader.pattern_utils import (
    get_available_patterns,
    cdl_pattern,
    has_pattern,
)
from auto_vertical_spread_trader.scans import (
    bear_rally_condition,
    bull_pullback_condition,
    high_base_condition,
    low_base_condition,
    scan_bear_rallies,
    scan_bull_pullbacks,
    scan_high_base,
    scan_low_base,
)
