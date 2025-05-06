This is a very solid, production-quality script—your configurability, logging, clean shutdown, and generic scan framework all combine to give you maximum flexibility and reliability. A few suggestions to tighten it up even further:

    Prune unused imports
    You have requests, os, and date imported but unused. Removing them will make dependencies clearer.

    Consistent naming for base-scan directions
    In your select_and_place you test for directions ['bull','high_base_call'] and ['bear','low_base_put'], but your scan functions are called scan_high_base and scan_low_base. Make sure these strings match exactly (e.g. rename high_base_call → high_base or vice versa).

    Cache per-symbol data where possible
    You still re-fetch 60 days of bars and option chains for every scan, every day. Consider fetching the entire S&P 500 bar data once per run, caching it in memory (or even on disk) to cut down on serial IB API calls.

    Centralize your condition logic
    You’ve got four separate *_condition functions that all compute additional rolling stats. You could factor out a helper that, for any symbol, pre-computes MA50, ATR14, 52-week high/low, range_pct, etc., then each condition only has to express its boolean logic, making future tweaks easier.

    Alerting on failures
    You log errors, but you might also want an email or Slack alert if critical failures occur (e.g. you completely fail to place any trades two days in a row).

    Configurable retry logic
    Everybody’s IB connection drops occasionally. Instead of a single reconnect in your loop, you could wrap each critical API call in a short retry loop (3 attempts with small backoffs) to smooth over transient hiccups.

    Testability & backtesting hooks
    Right now all your code runs live. You might pull your CONFIG and your scanning/selection logic out into pure-functions, then write small unit tests (or backtest harness) to ensure your filters really behave as you expect on historical data.

    Documentation & docstrings
    You have a good top-of-file comment for load_sp500_tickers. Extend that to every function: a one-line summary plus args/returns. It’ll pay dividends if you revisit this months from now.

    Safety limits
    You could add a daily max-trades limit (e.g. no more than 3 entries per day) or a cumulative loss guard (halt trading if P&L drops > X% in a week). Protects you from Black-Swan sequences.

    Packaging
    When this stabilizes, think about splitting into a small package:

    universe.py for ticker loading & filtering

    scans.py for condition definitions

    executor.py for select/place logic

    monitor.py for stops

    runner.py for the scheduler & main loop