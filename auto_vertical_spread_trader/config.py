"""
Configuration module for the auto vertical spread trader.
Centralizes all configurable parameters.
"""

# Configuration dictionary for the auto vertical spread trader
CONFIG = {
    # Universe filters
    'MIN_MARKET_CAP': 10e9,        # $10 billion minimum market cap
    'MIN_PRICE': 20,               # $20 minimum stock price
    
    # Technical filters
    'LOOKBACK_DAYS': 60,           # Days of historical data to fetch
    'MIN_VOLUME': 1_000_000,       # Minimum daily volume
    
    # Option parameters
    'TARGET_EXPIRY_INDEX': 1,      # 0=nearest, 1=next cycle (2-3 weeks)
    'MIN_DELTA': 0.30,             # Minimum absolute delta for long leg
    'MAX_COST': 500,               # Maximum spread cost in dollars
    'MIN_REWARD_RISK_RATIO': 1.0,  # Minimum reward-to-risk ratio
    'MAX_BID_ASK_PCT': 0.15,       # Maximum bid-ask spread as % of mid-price
    
    # Risk management
    'STOP_LOSS_ATR_MULT': 2.0,     # ATR multiplier for stop-loss
    'MAX_DAILY_TRADES': 3,         # Maximum number of new trades per day
    'MAX_POSITIONS': 10,           # Maximum number of open positions
    
    # Execution
    'SCAN_HOUR_ET': 15,            # Hour to run scans (15 = 3PM ET)
    'MONITOR_INTERVAL_SEC': 60,    # Seconds between stop-loss checks
    'API_SLEEP': 0.1,              # Sleep time between API calls
    'MAIN_LOOP_INTERVAL': 60,      # Seconds between main loop iterations
    
    # Base patterns
    'HIGH_BASE_MAX_ATR_RATIO': 0.8,  # Max ATR ratio for high/low base
    'PRICE_NEAR_HIGH_PCT': 0.95,     # Price must be within 5% of 52-week high
    'PRICE_NEAR_LOW_PCT': 1.05,      # Price must be within 5% of 52-week low
    'TIGHT_RANGE_FACTOR': 0.8,       # Daily range must be below this % of average
    
    # Exit strategy
    'USE_FIBONACCI_TARGETS': True,    # Use Fibonacci extensions for profit targets
    'FIBONACCI_EXTENSION': 1.618,     # Extension level: 1.618 (golden ratio)
    'FIBONACCI_ALT_LEVELS': [1.272, 2.0, 2.618],  # Alternative extension levels
    'USE_R_MULTIPLE_TARGETS': False,  # Use R-multiple for profit targets
    'TARGET_R_MULTIPLE': 2.0,         # Target as multiple of initial risk
    'USE_ATR_TARGETS': False,         # Use ATR multiples for profit targets
    'TARGET_ATR_MULTIPLE': 3.0,       # Target as multiple of ATR
    'TRAILING_STOP_ENABLED': False,   # Enable trailing stops after price target reached
    'TRAILING_STOP_BUFFER': 0.5,      # Buffer for trailing stop as ATR multiple
    
    # Connection
    'IB_HOST': '127.0.0.1',          # TWS/IB Gateway host
    'IB_PORT': 7497,                 # TWS/IB Gateway port (7497 for TWS, 4002 for Gateway)
    'IB_CLIENT_ID': 99,              # Client ID for IB connection
    
    # Alerts
    'ENABLE_EMAIL_ALERTS': False,     # Enable email alerts
    'EMAIL_FROM': '',                 # Sender email
    'EMAIL_TO': '',                   # Recipient email
    'EMAIL_PASSWORD': '',             # Email password or app password
    'EMAIL_SERVER': 'smtp.gmail.com', # SMTP server
    'EMAIL_PORT': 587                 # SMTP port
} 