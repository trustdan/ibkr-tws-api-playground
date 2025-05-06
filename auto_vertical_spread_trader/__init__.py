"""
Auto Vertical Spread Trader
A modular system for identifying and trading vertical option spreads on IB TWS.

This package provides automated scanning, selection, and risk management
for bull pullbacks, bear rallies, high base, and low base trading strategies.
"""

__version__ = "1.0.0"

from auto_vertical_spread_trader.auto_vertical_spread_trader import AutoVerticalSpreadTrader
from auto_vertical_spread_trader.scans import (
    scan_bull_pullbacks,
    scan_bear_rallies,
    scan_high_base,
    scan_low_base,
    bull_pullback_condition,
    bear_rally_condition,
    high_base_condition,
    low_base_condition,
)
