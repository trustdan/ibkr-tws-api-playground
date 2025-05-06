"""
Executor module for selecting and placing option spreads.
Handles option chain selection, strike filtering, and order placement.
"""

import logging
import time
import traceback

from ib_insync import ComboLeg, Option, Order, Stock

logger = logging.getLogger(__name__)


def select_and_place(ib, symbol, direction, bar, atr, config, spread_book):
    """
    Select and place a vertical spread for the given symbol and direction

    Args:
        ib: IB connection object
        symbol (str): Ticker symbol
        direction (str): Strategy direction ('bull', 'bear', 'high_base', 'low_base')
        bar (DataFrame row): Current price bar with technical data
        atr (float): Current ATR value
        config (dict): Configuration dictionary
        spread_book (dict): Dictionary to track open spreads

    Returns:
        bool: True if spread was placed successfully, False otherwise

    Notes:
        - Handles error cases gracefully
        - Places limit orders at mid-price
        - Records trades in spread_book for stop-loss monitoring
    """
    try:
        logger.info(f"Selecting {direction} spread for {symbol}")

        # Get option chain parameters with retry
        for retry in range(3):
            try:
                params = ib.reqSecDefOptParams(
                    symbol, "", "STK", Stock(symbol, "SMART", "USD").conId
                )
                if not params:
                    logger.warning(f"No option parameters for {symbol}")
                    return False

                exp = sorted(params[0].expirations)[config["TARGET_EXPIRY_INDEX"]]
                strikes = sorted(params[0].strikes)
                break

            except Exception as e:
                logger.error(
                    f"Error fetching option parameters for {symbol} (attempt {retry+1}): {e}"
                )
                if retry == 2:  # Last attempt failed
                    return False
                ib.sleep(1)  # Wait before retrying

        # Get live underlying price with retry
        for retry in range(3):
            try:
                stk = Stock(symbol, "SMART", "USD")
                tick = ib.reqMktData(stk, "", False, False)
                ib.sleep(config["API_SLEEP"])
                S = tick.marketPrice()
                if not S:
                    logger.warning(f"Could not get price for {symbol}")
                    if retry == 2:  # Last attempt failed
                        return False
                    continue
                break

            except Exception as e:
                logger.error(f"Error getting market data for {symbol} (attempt {retry+1}): {e}")
                if retry == 2:  # Last attempt failed
                    return False
                ib.sleep(1)  # Wait before retrying

        for k1 in strikes:
            # pick OTM long leg
            if direction in ["bull", "high_base"] and k1 < S:
                continue
            if direction in ["bear", "low_base"] and k1 > S:
                continue

            # wing one strike away
            idx = strikes.index(k1) + (1 if direction in ["bull", "high_base"] else -1)
            if idx < 0 or idx >= len(strikes):
                continue
            k2 = strikes[idx]

            width = abs(k2 - k1)

            optType = "C" if direction in ["bull", "high_base"] else "P"
            longOpt = Option(symbol, exp, k1, optType, "SMART")
            shortOpt = Option(symbol, exp, k2, optType, "SMART")

            # fetch quotes & Greeks with retry
            for retry in range(3):
                try:
                    t1 = ib.reqMktData(longOpt, "", False, False)
                    t2 = ib.reqMktData(shortOpt, "", False, False)
                    ib.sleep(config["API_SLEEP"] * 3)  # Give more time for option data

                    if not (t1.modelGreeks and t2.modelGreeks):
                        logger.debug(f"Missing Greeks for {symbol} options")
                        if retry == 2:  # Last attempt failed
                            break
                        continue
                    break

                except Exception as e:
                    logger.error(f"Error getting option data for {symbol} (attempt {retry+1}): {e}")
                    if retry == 2:  # Last attempt failed
                        break
                    ib.sleep(1)  # Wait before retrying
                    continue

            # If we didn't get option data after retries, move to next strike
            if not (t1.modelGreeks and t2.modelGreeks):
                continue

            delta = t1.modelGreeks.delta
            mid1 = (t1.bid + t1.ask) / 2
            mid2 = (t2.bid + t2.ask) / 2

            # Liquidity check: bid-ask ≤ 15% mid
            if t1.bid <= 0 or t1.ask <= 0:
                logger.debug(f"Invalid bid/ask for {symbol} long option")
                continue

            spread_pct1 = (t1.ask - t1.bid) / ((t1.ask + t1.bid) / 2)
            if spread_pct1 > config["MAX_BID_ASK_PCT"]:
                logger.debug(f"Spread too wide for {symbol} long option: {spread_pct1:.1%}")
                continue

            if t2.bid <= 0 or t2.ask <= 0:
                logger.debug(f"Invalid bid/ask for {symbol} short option")
                continue

            spread_pct2 = (t2.ask - t2.bid) / ((t2.ask + t2.bid) / 2)
            if spread_pct2 > config["MAX_BID_ASK_PCT"]:
                logger.debug(f"Spread too wide for {symbol} short option: {spread_pct2:.1%}")
                continue

            debit = round((mid1 - mid2) * 100, 2)
            reward = width * 100 - debit

            # delta filter, cost, R≥1:1
            if direction in ["bull", "high_base"] and abs(delta) < config["MIN_DELTA"]:
                continue
            if direction in ["bear", "low_base"] and abs(delta) < config["MIN_DELTA"]:
                continue
            if debit > config["MAX_COST"]:
                continue
            if reward / debit < config["MIN_REWARD_RISK_RATIO"]:
                continue

            # place the spread
            try:
                combo = Order(
                    orderType="LMT",
                    action="BUY",
                    totalQuantity=1,
                    lmtPrice=debit / 100,
                    tif="GTC",
                    comboLegs=[
                        ComboLeg(longOpt.conId, 1, "BUY"),
                        ComboLeg(shortOpt.conId, 1, "SELL"),
                    ],
                )
                trade = ib.placeOrder(longOpt, combo)
                logger.info(
                    f"Placed {direction} spread for {symbol}: {k1}/{k2} {optType}, cost: ${debit:.2f}"
                )

                # record for stop-loss
                spread_book[symbol] = {
                    "type": direction,
                    "entryPrice": bar.close,
                    "ATR": atr,
                    "legs": [longOpt, shortOpt],
                    "order": trade,
                    "width": width,
                    "debit": debit,
                    "symbol": symbol,  # Add symbol to the info for convenience
                }

                # Add profit targets based on configuration
                if config.get("USE_FIBONACCI_TARGETS", False):
                    add_fibonacci_targets(ib, symbol, spread_book, config)
                elif config.get("USE_R_MULTIPLE_TARGETS", False):
                    add_r_multiple_target(spread_book[symbol], config.get("TARGET_R_MULTIPLE", 2.0))
                elif config.get("USE_ATR_TARGETS", False):
                    add_atr_target(spread_book[symbol], config.get("TARGET_ATR_MULTIPLE", 3.0))

                return True

            except Exception as e:
                logger.error(f"Error placing order for {symbol}: {e}")
                continue

    except Exception as e:
        logger.error(f"Error in select_and_place for {symbol}: {e}")
        traceback.print_exc()

    return False


def add_fibonacci_targets(ib, symbol, spread_book, config):
    """
    Add Fibonacci extension targets to a trade

    Args:
        ib: IB connection object
        symbol (str): Symbol to add targets for
        spread_book (dict): Dictionary of open positions
        config (dict): Configuration dictionary
    """
    try:
        from exits import add_fibonacci_target
        from scans import get_tech_df

        # Get historical data for Fibonacci calculations
        df = get_tech_df(ib, symbol, config)
        if df is None:
            logger.warning(
                f"Could not get historical data for {symbol} to calculate Fibonacci targets"
            )
            return

        # Add the Fibonacci target
        extension_level = config.get("FIBONACCI_EXTENSION", 1.618)
        spread_book[symbol] = add_fibonacci_target(spread_book[symbol], df, extension_level)

    except Exception as e:
        logger.error(f"Error adding Fibonacci targets for {symbol}: {e}")


def add_r_multiple_target(spread_info, r_multiple=2.0):
    """
    Add fixed R-multiple price target to spread info

    Args:
        spread_info: Dictionary with trade information
        r_multiple: Target as multiple of initial risk

    Returns:
        dict: Updated spread_info with R-multiple target
    """
    try:
        from exits import add_r_multiple_target

        return add_r_multiple_target(spread_info, r_multiple)
    except Exception as e:
        logger.error(f"Error adding R-multiple target: {e}")
        return spread_info


def add_atr_target(spread_info, atr_multiple=3.0):
    """
    Add ATR-based price target to spread info

    Args:
        spread_info: Dictionary with trade information
        atr_multiple: Target as multiple of ATR

    Returns:
        dict: Updated spread_info with ATR-multiple target
    """
    try:
        from exits import add_atr_target

        return add_atr_target(spread_info, atr_multiple)
    except Exception as e:
        logger.error(f"Error adding ATR target: {e}")
        return spread_info


def retry_api_call(func, max_retries=3, sleep_time=1, ib=None):
    """
    Retry an API call function multiple times

    Args:
        func (callable): Function to retry
        max_retries (int): Maximum number of retry attempts
        sleep_time (float): Time to sleep between retries
        ib: IB connection object (optional)

    Returns:
        The return value of the function or None if all retries fail
    """
    for attempt in range(max_retries):
        try:
            result = func()
            return result
        except Exception as e:
            logger.error(f"API call failed (attempt {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1 and ib is not None:
                ib.sleep(sleep_time)
            elif attempt < max_retries - 1:
                time.sleep(sleep_time)

    return None
