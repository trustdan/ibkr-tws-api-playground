Below is a summary of every requirement your script now satisfies, framed as Gherkin scenarios (with a bit of pseudo-code where useful) so you can see at a glance all the goals we’ve built into auto_vertical_spread_trader.py.

Feature: Universe Filtering
  As a trader
  I want to restrict my universe to liquid, large-cap, optionable stocks
  So that I only trade in names that meet my fundamental and liquidity criteria

  Scenario: Filter by market cap and price
    Given a list of candidate tickers
    When I fetch fundamental “ReportSnapshot” data
    Then I only retain tickers with MarketCap ≥ $10 B
    And I only retain tickers whose last price > $20

  Scenario: Ensure optionability
    Given a filtered list of tickers
    When I request option chains (reqSecDefOptParams)
    Then I only keep symbols that actually have listed options


Feature: Bull Pullback and Bear Rally Scans
  As a directional trader
  I want to identify high-probability setups
  So that I enter spreads only after technical confirmation

  Scenario: Detect Bull Pullback
    Given 60 days of daily bars
    And the 50-day MA is rising
    When there are two consecutive bullish candles (Close > Open)
    And today’s low touches or crosses the 50-day MA
    And today’s volume ≥ 1 000 000
    Then signal a “bull pullback” candidate

  Scenario: Detect Bear Rally
    Given 60 days of daily bars
    And the 50-day MA is falling
    When there are two consecutive bearish candles (Close < Open)
    And today’s high touches or crosses the 50-day MA
    And today’s volume ≥ 1 000 000
    Then signal a “bear rally” candidate


Feature: Spread Selection & Risk/Reward
  As a defined-risk strategist
  I want to pick vertical spreads that meet strict cost, delta, and R:R rules
  So that I’m always in a 1:1 or better reward-to-risk trade under \$500

  Scenario: Choose expiration
    Given each candidate symbol
    When I look at available expirations
    Then pick the 2nd-nearest cycle (≈2–3 weeks out)

  Scenario: Select strikes based on delta
    Given the underlying price S
    When iterating OTM strikes
    Then pick the first strike with |delta| ≥ 0.30
    And choose the adjacent wing one strike away

  Scenario: Enforce cost & R:R
    Given mid-prices mid1 and mid2 of long/short legs
    Calculate debit = (mid1 – mid2) × 100
    And width = |strike2 – strike1| × 100
    Then require debit ≤ \$500
    And require (width – debit) / debit ≥ 1

  Scenario: Enforce liquidity
    Given bid and ask on each leg
    Calculate spread_pct = (ask – bid) / ((ask + bid)/2)
    Then require spread_pct ≤ 0.15 for both legs


Feature: Execution Scheduling
  As a vega-sensitive trader
  I want the scan—and only the scan—to run once per day after 3 PM ET
  So that spreads are entered in late-day conditions

  Scenario: Only run after market hours
    Given the Eastern-time clock
    When current_time ≥ 15:00 ET
    And lastRunDate ≠ today
    Then perform bull and bear scans
    And place qualifying vertical spreads
    And set lastRunDate = today


Feature: Stop-Loss Management
  As a disciplined trader
  I want to auto-exit if the underlying moves too far against me
  So that losses are capped by ATR-based stops

  Scenario: Monitor for adverse move
    Given each open spread with entryPrice and ATR
    When current_price ≤ entryPrice – 2×ATR for bulls
      Or current_price ≥ entryPrice + 2×ATR for bears
    Then submit market orders to close both legs immediately

―――
This Gherkin outline captures every goal:

    Fundamental filters (MarketCap, Price > 20, Optionable)

    Technical scans (50 DMA trend, 2 confirm candles, volume ≥ 1 M)

    Spread rules (2–3 wk expiry, |delta| ≥ 0.30, cost ≤ $500, R:R ≥ 1:1)

    Liquidity check (bid–ask ≤ 15 % mid)

    Late-day scheduling (once per day after 3 PM ET)

    Stop-losses (2×ATR against entry)