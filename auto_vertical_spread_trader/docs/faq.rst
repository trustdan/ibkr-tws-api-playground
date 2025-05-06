==========================
Frequently Asked Questions
==========================

This FAQ addresses common questions and troubleshooting issues with the Auto Vertical Spread Trader system.

General Questions
----------------

What is a vertical spread?
~~~~~~~~~~~~~~~~~~~~~~~~~

A vertical spread is an options strategy involving buying and selling options of the same type (calls or puts) 
with the same expiration date but different strike prices. This strategy limits both potential profit and potential loss.

How much capital do I need?
~~~~~~~~~~~~~~~~~~~~~~~~~~

The system is configured by default to trade spreads costing up to $500 each, with a maximum of 10 positions. 
You should have at least $5,000 in available capital, but can adjust these parameters for smaller accounts.

Can I use this with a paper trading account?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Yes! Use the ``--paper`` command line option or set ``IB_IS_PAPER_ACCOUNT = True`` in your configuration.

Interactive Brokers Setup
------------------------

How do I enable API connections in TWS?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Open TWS (Trader Workstation)
2. Go to Edit → Global Configuration → API → Settings
3. Check "Enable ActiveX and Socket Clients"
4. Set a socket port (default is 7496)
5. Optionally, check "Allow connections from localhost only" for security

Why can't the system connect to TWS?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Common reasons include:
- TWS is not running
- API connections aren't enabled
- Wrong port number in configuration
- TWS needs to be restarted

Check ``auto_trader.log`` for specific error messages.

Where do I find my IB Account ID?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Your account ID is visible in the top right corner of TWS, or under Account → Account Settings.

Technical Issues
--------------

ImportError with TA-Lib
~~~~~~~~~~~~~~~~~~~~~~

If you see ``ImportError: No module named 'talib'`` or similar, TA-Lib was not properly installed.

Refer to :doc:`installation` for detailed operating system-specific instructions.

For Windows, the most common solution is:

.. code-block:: bash

    pip install --no-cache-dir ta-lib

If that fails, download a pre-built wheel from https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib.

"Pacing violation" errors
~~~~~~~~~~~~~~~~~~~~~~~

Interactive Brokers has request rate limits. If you see "Pacing violation" errors:

1. Increase ``QUERY_DELAY`` in your config
2. Reduce the size of your universe
3. Avoid running multiple instances simultaneously

"No market data permissions" errors
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You need market data subscriptions for the symbols you're trading:

1. In TWS, go to Account → Market Data Subscriptions
2. Subscribe to the necessary data packages
3. Note that options data often requires separate subscriptions

Time zone issues
~~~~~~~~~~~~~~

The system uses your local time zone by default. If scans aren't running at the expected time, check:

1. Your system's time zone is correctly set
2. ``SCAN_END_HOUR`` and ``SCAN_END_MINUTE`` in config match your intended local time
3. For custom time zones, set ``IB_TIME_ZONE`` in your config

Trading Questions
---------------

Why didn't the system enter a trade?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Several checks must pass for a trade to execute:
- Within trading hours (after 3 PM ET by default)
- Under maximum daily trades limit
- Under maximum positions limit
- The scan found valid signals
- Suitable options within delta and cost parameters were found

Check your ``auto_trader.log`` for specific reasons.

How are stop losses calculated?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Stop losses are based on the underlying stock's Average True Range (ATR):

1. ATR is calculated using a 14-day period
2. The ATR is multiplied by ``STOP_LOSS_ATR_MULT`` (default 1.5)
3. For calls, stop = entry_price - (ATR * multiplier)
4. For puts, stop = entry_price + (ATR * multiplier)

You can adjust the multiplier in your config.

Performance Questions
-------------------

How can I measure performance?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The system logs all entries and exits to ``auto_trader.log``. For more detailed analysis:

1. Enable the ``TRACK_PERFORMANCE`` option in config
2. The system will write trade data to ``performance.csv``
3. You can use pandas to analyze this data and calculate metrics

.. code-block:: python

    import pandas as pd
    
    trades = pd.read_csv('performance.csv')
    win_rate = (trades['profit'] > 0).mean()
    avg_win = trades[trades['profit'] > 0]['profit'].mean()
    avg_loss = trades[trades['profit'] < 0]['profit'].mean()
    print(f"Win rate: {win_rate:.2%}")
    print(f"Average win: ${avg_win:.2f}")
    print(f"Average loss: ${avg_loss:.2f}")
    print(f"Win/loss ratio: {abs(avg_win/avg_loss):.2f}")

Can I run a backtest?
~~~~~~~~~~~~~~~~~~~

The system doesn't include a backtest feature, but you can:

1. Collect historical data for your universe
2. Implement the scan conditions on historical data
3. Simulate option prices for the resulting signals

Several third-party backtesters can also be used with the strategy logic. 