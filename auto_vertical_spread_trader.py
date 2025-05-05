from ib_insync import IB, Stock, Option, ComboLeg, Order, util
import pandas as pd
import talib
import time
from datetime import datetime, date
import pytz
import threading

ib = IB()
ib.connect('127.0.0.1', 7497, clientId=99)

# --- 1. Define & filter universe ---
universe = load_sp500_tickers()   # your list of S&P500 tickers

def filter_universe(symbols):
    large = []
    for sym in symbols:
        stk = Stock(sym, 'SMART', 'USD')
        # 1a) market cap
        snap = ib.reqFundamentalData(stk, reportType='ReportSnapshot')
        kv = dict(item.split('=') for item in snap.split(';') if '=' in item)
        cap = float(kv.get('MarketCap', 0))
        if cap < 10e9:
            continue
        # 1b) price > 20
        tick = ib.reqMktData(stk, '', False, False)
        ib.sleep(0.1)
        price = tick.marketPrice()
        if not price or price <= 20:
            continue
        large.append(sym)
    return large

large_caps = filter_universe(universe)


# --- 2. Fetch bars & indicators ---
def get_tech_df(symbol):
    bars = ib.reqHistoricalData(
        Stock(symbol, 'SMART', 'USD'),
        endDateTime='',
        durationStr='60 D',
        barSizeSetting='1 day',
        whatToShow='TRADES',
        useRTH=True)
    df = util.df(bars)
    df['MA50'] = df['close'].rolling(50).mean()
    df['ATR14'] = talib.ATR(df['high'], df['low'], df['close'], timeperiod=14)
    return df


# --- 3. Scan functions with volume filter ---
def scan_bull_pullbacks(symbols):
    sig = []
    for sym in symbols:
        df = get_tech_df(sym)
        if len(df) < 52: 
            continue
        today, y1, y2 = df.iloc[-1], df.iloc[-2], df.iloc[-3]
        # 3a) two bullish candles
        if not (y2.close > y2.open and y1.close > y1.open):
            continue
        # 3b) pullback to rising 50MA
        if not (today.low <= today.MA50 and df.MA50.iloc[-1] > df.MA50.iloc[-2]):
            continue
        # 3c) volume ≥ 1 000 000
        if today.volume < 1_000_000:
            continue
        sig.append((sym, today, df.ATR14.iloc[-1]))
    return sig

def scan_bear_rallies(symbols):
    sig = []
    for sym in symbols:
        df = get_tech_df(sym)
        if len(df) < 52: 
            continue
        today, y1, y2 = df.iloc[-1], df.iloc[-2], df.iloc[-3]
        # 3a) two bearish candles
        if not (y2.close < y2.open and y1.close < y1.open):
            continue
        # 3b) rally into falling 50MA
        if not (today.high >= today.MA50 and df.MA50.iloc[-1] < df.MA50.iloc[-2]):
            continue
        # 3c) volume ≥ 1 000 000
        if today.volume < 1_000_000:
            continue
        sig.append((sym, today, df.ATR14.iloc[-1]))
    return sig

def scan_high_base(symbols):
    sig = []
    for sym in symbols:
        df = get_tech_df(sym)
        if len(df) < 52: 
            continue
        
        # Calculate additional indicators
        df['52w_high'] = df['close'].rolling(252).max()
        df['ATR_ratio'] = df['ATR14'] / df['ATR14'].rolling(20).mean()
        df['range_pct'] = (df['high'] - df['low']) / df['close'] * 100
        
        today = df.iloc[-1]
        
        # High-base criteria:
        # 1. Near 52-week highs (within 5%)
        near_highs = today.close >= 0.95 * today['52w_high']
        
        # 2. Low volatility (ATR below historical average)
        low_volatility = today.ATR_ratio < 0.8
        
        # 3. Narrow price range recently (tight consolidation)
        tight_range = today.range_pct < df.range_pct.rolling(20).mean().iloc[-1] * 0.8
        
        # 4. Volume filter
        high_volume = today.volume >= 1_000_000
        
        if near_highs and low_volatility and tight_range and high_volume:
            sig.append((sym, today, df.ATR14.iloc[-1]))
            
    return sig

def scan_low_base(symbols):
    sig = []
    for sym in symbols:
        df = get_tech_df(sym)
        if len(df) < 52: 
            continue
        
        # Calculate additional indicators
        df['52w_low'] = df['close'].rolling(252).min()
        df['ATR_ratio'] = df['ATR14'] / df['ATR14'].rolling(20).mean()
        df['range_pct'] = (df['high'] - df['low']) / df['close'] * 100
        
        today = df.iloc[-1]
        
        # Low-base criteria:
        # 1. Near 52-week lows (within 5%)
        near_lows = today.close <= 1.05 * today['52w_low']
        
        # 2. Low volatility (ATR below historical average)
        low_volatility = today.ATR_ratio < 0.8
        
        # 3. Narrow price range recently (tight consolidation)
        tight_range = today.range_pct < df.range_pct.rolling(20).mean().iloc[-1] * 0.8
        
        # 4. Volume filter
        high_volume = today.volume >= 1_000_000
        
        if near_lows and low_volatility and tight_range and high_volume:
            sig.append((sym, today, df.ATR14.iloc[-1]))
            
    return sig


# --- 4. Spread selector & placer with width ≤15% filter ---
def select_and_place(symbol, direction, bar, atr):
    params = ib.reqSecDefOptParams(symbol, '', 'STK',
                                   Stock(symbol,'SMART','USD').conId)
    if not params:
        return
    exp = sorted(params[0].expirations)[1]  # ~2–3 weeks out
    strikes = sorted(params[0].strikes)

    # live underlying price
    stk = Stock(symbol, 'SMART', 'USD')
    tick = ib.reqMktData(stk, '', False, False)
    ib.sleep(0.2)
    S = tick.marketPrice()
    if not S:
        return

    for k1 in strikes:
        # pick OTM long leg
        if direction in ['bull', 'high_base_call'] and k1 < S: continue
        if direction in ['bear', 'low_base_put'] and k1 > S: continue

        # wing one strike away
        idx = strikes.index(k1) + (1 if direction in ['bull', 'high_base_call'] else -1)
        if idx < 0 or idx >= len(strikes): 
            continue
        k2 = strikes[idx]

        width = abs(k2 - k1)
        # 4a) width ≤ 15% of S
        if width > 0.15 * S:
            continue

        optType = 'C' if direction in ['bull', 'high_base_call'] else 'P'
        longOpt  = Option(symbol, exp, k1, optType, 'SMART')
        shortOpt = Option(symbol, exp, k2, optType, 'SMART')

        # fetch quotes & Greeks
        t1 = ib.reqMktData(longOpt,  '', False, False)
        t2 = ib.reqMktData(shortOpt, '', False, False)
        ib.sleep(0.3)
        if not (t1.modelGreeks and t2.modelGreeks):
            continue

        delta = t1.modelGreeks.delta
        mid1  = (t1.bid + t1.ask) / 2
        mid2  = (t2.bid + t2.ask) / 2
        
        # Liquidity check: bid-ask ≤ 15% mid
        if t1.bid > 0 and t1.ask > 0:
            spread_pct1 = (t1.ask - t1.bid) / ((t1.ask + t1.bid) / 2)
            if spread_pct1 > 0.15:
                continue
        else:
            continue  # Skip if no valid bid/ask
            
        if t2.bid > 0 and t2.ask > 0:
            spread_pct2 = (t2.ask - t2.bid) / ((t2.ask + t2.bid) / 2)
            if spread_pct2 > 0.15:
                continue
        else:
            continue  # Skip if no valid bid/ask
        
        debit = round((mid1 - mid2) * 100, 2)
        reward = width * 100 - debit

        # 4b) delta filter, cost, R≥1:1
        if direction in ['bull', 'high_base_call'] and delta < 0.3: continue
        if direction in ['bear', 'low_base_put'] and delta > -0.3: continue
        if debit > 500:          continue
        if reward / debit < 1:   continue

        # place the spread
        combo = Order(
          orderType='LMT', action='BUY',
          totalQuantity=1, lmtPrice=debit/100,
          tif='GTC',
          comboLegs=[
            ComboLeg(longOpt.conId,  1, 'BUY'),
            ComboLeg(shortOpt.conId, 1, 'SELL')
          ])
        ib.placeOrder(longOpt, combo)

        # record for stop-loss
        spreadBook[symbol] = {
          'type':      direction,
          'entryPrice': bar.close,
          'ATR':        atr,
          'legs':      [longOpt, shortOpt]
        }
        break


# --- 5. Stop-loss monitor (unchanged) ---
def monitor_stops():
    while True:
        for sym, info in list(spreadBook.items()):
            stk  = Stock(sym, 'SMART', 'USD')
            tick = ib.reqMktData(stk, '', False, False)
            ib.sleep(0.1)
            cur = tick.marketPrice()
            if info['type'] in ['bull', 'high_base_call'] and cur <= info['entryPrice'] - 2*info['ATR']:
                side = 'SELL'
            elif info['type'] in ['bear', 'low_base_put'] and cur >= info['entryPrice'] + 2*info['ATR']:
                side = 'SELL'
            else:
                continue
            for opt in info['legs']:
                pos = ib.position(opt)
                if pos and pos.position != 0:
                    close_ord = Order(orderType='MKT', action=side,
                                      totalQuantity=abs(pos.position))
                    ib.placeOrder(opt, close_ord)
            spreadBook.pop(sym)
        time.sleep(60)

threading.Thread(target=monitor_stops, daemon=True).start()


# --- 6. Schedule your entry scan at 3 PM ET every trading day ---
spreadBook = {}
tz = pytz.timezone('US/Eastern')
lastRunDate = None

def run_entries_if_time():
    global lastRunDate
    now = datetime.now(tz)
    # only once per day, after 3pm ET
    if now.hour >= 15 and lastRunDate != now.date():
        lastRunDate = now.date()
        bulls = scan_bull_pullbacks(large_caps)
        bears = scan_bear_rallies(large_caps)
        high_bases = scan_high_base(large_caps)
        low_bases = scan_low_base(large_caps)
        
        for sym, bar, atr in bulls:
            select_and_place(sym, 'bull', bar, atr)
        for sym, bar, atr in bears:
            select_and_place(sym, 'bear', bar, atr)
        for sym, bar, atr in high_bases:
            select_and_place(sym, 'high_base_call', bar, atr)
        for sym, bar, atr in low_bases:
            select_and_place(sym, 'low_base_put', bar, atr)
            
        print(f"{now.date()}: placed {len(bulls)} bull, {len(bears)} bear, {len(high_bases)} high-base call, and {len(low_bases)} low-base put spreads.")

# main loop: check every minute
print("Scheduler started; will enter trades after 3 PM ET each trading day.")
try:
    while True:
        run_entries_if_time()
        time.sleep(60)
except KeyboardInterrupt:
    ib.disconnect()
    print("Stopped by user.")
