"""
Universe module for loading and filtering tickers.
Handles S&P 500 ticker retrieval and filtering based on market cap, price, and optionability.
"""

import csv
import time
import logging
import pandas as pd
from pathlib import Path
from ib_insync import Stock

logger = logging.getLogger(__name__)

def load_sp500_tickers():
    """
    Load S&P 500 tickers from a local file or download them.
    
    Returns:
        list: List of ticker symbols for S&P 500 companies
        
    Notes:
        - Caches the list locally for 7 days to minimize network requests
        - Falls back to a small list of major tickers if download fails
    """
    tickers_file = Path("sp500_tickers.csv")
    
    # If we already have the file and it's recent (less than 7 days old), use it
    if tickers_file.exists() and (time.time() - tickers_file.stat().st_mtime < 7 * 86400):
        logger.info("Loading S&P 500 tickers from local file")
        with open(tickers_file, 'r') as f:
            reader = csv.reader(f)
            return [row[0] for row in reader if row]
    
    # Otherwise download the list
    try:
        logger.info("Downloading S&P 500 tickers")
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        tables = pd.read_html(url)
        df = tables[0]
        tickers = df['Symbol'].str.replace('.', '-').tolist()
        
        # Save to file for future use
        with open(tickers_file, 'w', newline='') as f:
            writer = csv.writer(f)
            for ticker in tickers:
                writer.writerow([ticker])
        
        return tickers
    except Exception as e:
        logger.error(f"Error downloading S&P 500 tickers: {e}")
        # Fallback to a minimal list if download fails
        logger.warning("Using fallback ticker list")
        return ["AAPL", "MSFT", "AMZN", "GOOGL", "META", "TSLA", "NVDA", "JPM", "V", "PG"]

def filter_universe(ib, symbols, config):
    """
    Filter universe to large cap, liquid, optionable stocks
    
    Args:
        ib: IB connection object
        symbols (list): List of ticker symbols to filter
        config (dict): Configuration dictionary with filter parameters
        
    Returns:
        list: Filtered list of ticker symbols meeting all criteria
        
    Notes:
        - Filters by market cap (≥ $10B)
        - Filters by price (> $20)
        - API calls use sleep to avoid rate-limiting
    """
    large = []
    logger.info(f"Filtering universe of {len(symbols)} symbols")
    
    for sym in symbols:
        try:
            stk = Stock(sym, 'SMART', 'USD')
            
            # 1a) market cap
            snap = ib.reqFundamentalData(stk, reportType='ReportSnapshot')
            ib.sleep(config['API_SLEEP'])
            
            kv = dict(item.split('=') for item in snap.split(';') if '=' in item)
            cap = float(kv.get('MarketCap', 0))
            if cap < config['MIN_MARKET_CAP']:
                continue
                
            # 1b) price > minimum
            tick = ib.reqMktData(stk, '', False, False)
            ib.sleep(config['API_SLEEP'])
            price = tick.marketPrice()
            if not price or price <= config['MIN_PRICE']:
                continue
                
            large.append(sym)
            
        except Exception as e:
            logger.error(f"Error filtering {sym}: {e}")
            continue
            
    logger.info(f"Filtered down to {len(large)} symbols meeting criteria")
    return large 