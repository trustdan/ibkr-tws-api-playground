"""
Performance monitoring utilities for tracking trading metrics.
"""

import os
import csv
import json
import time
import logging
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """Tracks and analyzes trading performance metrics"""

    def __init__(self, data_dir="performance_data"):
        """
        Initialize the performance monitor.

        Args:
            data_dir (str): Directory to store performance data
        """
        self.data_dir = data_dir
        self._ensure_data_dir()
        self.trades_file = os.path.join(data_dir, "trades.csv")
        self.metrics_file = os.path.join(data_dir, "metrics.json")
        self.scan_metrics_file = os.path.join(data_dir, "scan_metrics.csv")
        self.execution_metrics_file = os.path.join(data_dir, "execution_metrics.csv")

        # Initialize files if they don't exist
        self._init_trades_file()
        self._init_scan_metrics_file()
        self._init_execution_metrics_file()

    def _ensure_data_dir(self):
        """Ensure the data directory exists"""
        os.makedirs(self.data_dir, exist_ok=True)

    def _init_trades_file(self):
        """Initialize the trades CSV file with headers if it doesn't exist"""
        if not os.path.exists(self.trades_file):
            with open(self.trades_file, "w", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(
                    [
                        "trade_id",
                        "symbol",
                        "strategy",
                        "direction",
                        "entry_date",
                        "entry_price",
                        "exit_date",
                        "exit_price",
                        "stop_price",
                        "long_strike",
                        "short_strike",
                        "expiry",
                        "cost",
                        "profit",
                        "profit_pct",
                        "duration_days",
                        "exit_reason",
                    ]
                )

    def _init_scan_metrics_file(self):
        """Initialize the scan metrics CSV file with headers if it doesn't exist"""
        if not os.path.exists(self.scan_metrics_file):
            with open(self.scan_metrics_file, "w", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(
                    [
                        "date",
                        "scan_type",
                        "universe_size",
                        "signals_found",
                        "execution_time_ms",
                        "memory_usage_mb",
                    ]
                )

    def _init_execution_metrics_file(self):
        """Initialize the execution metrics CSV file with headers if it doesn't exist"""
        if not os.path.exists(self.execution_metrics_file):
            with open(self.execution_metrics_file, "w", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(
                    [
                        "date",
                        "symbol",
                        "action",
                        "order_type",
                        "submission_time",
                        "execution_time",
                        "latency_ms",
                        "requested_price",
                        "executed_price",
                        "slippage",
                    ]
                )

    def record_trade(self, trade_data):
        """
        Record a completed trade.

        Args:
            trade_data (dict): Trade information including entry/exit data
        """
        with open(self.trades_file, "a", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(
                [
                    trade_data.get("trade_id", ""),
                    trade_data.get("symbol", ""),
                    trade_data.get("strategy", ""),
                    trade_data.get("direction", ""),
                    trade_data.get("entry_date", ""),
                    trade_data.get("entry_price", 0),
                    trade_data.get("exit_date", ""),
                    trade_data.get("exit_price", 0),
                    trade_data.get("stop_price", 0),
                    trade_data.get("long_strike", 0),
                    trade_data.get("short_strike", 0),
                    trade_data.get("expiry", ""),
                    trade_data.get("cost", 0),
                    trade_data.get("profit", 0),
                    trade_data.get("profit_pct", 0),
                    trade_data.get("duration_days", 0),
                    trade_data.get("exit_reason", ""),
                ]
            )
        logger.info(
            f"Recorded trade for {trade_data.get('symbol')}: "
            f"P/L ${trade_data.get('profit', 0):.2f}"
        )

    def record_scan_metrics(
        self, scan_type, universe_size, signals_found, execution_time_ms, memory_usage_mb
    ):
        """
        Record metrics from a scan operation.

        Args:
            scan_type (str): Type of scan performed
            universe_size (int): Number of securities in the scan universe
            signals_found (int): Number of signals found
            execution_time_ms (float): Time taken for scan in milliseconds
            memory_usage_mb (float): Memory usage in MB
        """
        with open(self.scan_metrics_file, "a", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(
                [
                    datetime.now().isoformat(),
                    scan_type,
                    universe_size,
                    signals_found,
                    execution_time_ms,
                    memory_usage_mb,
                ]
            )
        logger.debug(
            f"Recorded scan metrics for {scan_type}: "
            f"{signals_found} signals in {execution_time_ms:.2f}ms"
        )

    def record_execution_metrics(self, execution_data):
        """
        Record metrics from an order execution.

        Args:
            execution_data (dict): Order execution information
        """
        with open(self.execution_metrics_file, "a", newline="") as file:
            writer = csv.writer(file)

            # Calculate latency in milliseconds
            submission_time = execution_data.get("submission_time")
            execution_time = execution_data.get("execution_time")

            if submission_time and execution_time:
                # Convert to datetime objects if they're strings
                if isinstance(submission_time, str):
                    submission_time = datetime.fromisoformat(submission_time)
                if isinstance(execution_time, str):
                    execution_time = datetime.fromisoformat(execution_time)

                latency_ms = (execution_time - submission_time).total_seconds() * 1000
            else:
                latency_ms = 0

            # Calculate slippage
            requested_price = execution_data.get("requested_price", 0)
            executed_price = execution_data.get("executed_price", 0)

            if requested_price and executed_price:
                if execution_data.get("action") == "BUY":
                    slippage = executed_price - requested_price
                else:  # 'SELL'
                    slippage = requested_price - executed_price
            else:
                slippage = 0

            writer.writerow(
                [
                    datetime.now().isoformat(),
                    execution_data.get("symbol", ""),
                    execution_data.get("action", ""),
                    execution_data.get("order_type", ""),
                    (
                        submission_time.isoformat()
                        if isinstance(submission_time, datetime)
                        else submission_time
                    ),
                    (
                        execution_time.isoformat()
                        if isinstance(execution_time, datetime)
                        else execution_time
                    ),
                    latency_ms,
                    requested_price,
                    executed_price,
                    slippage,
                ]
            )

        logger.debug(
            f"Recorded execution metrics for {execution_data.get('symbol')}: "
            f"Latency {latency_ms:.2f}ms, Slippage ${slippage:.2f}"
        )

    def generate_performance_report(self, lookback_days=30, save_plots=True):
        """
        Generate a comprehensive performance report.

        Args:
            lookback_days (int): Number of days to look back for analysis
            save_plots (bool): Whether to save plots to disk

        Returns:
            dict: Performance metrics
        """
        # Load trade data
        if not os.path.exists(self.trades_file) or os.path.getsize(self.trades_file) == 0:
            logger.warning("No trade data available for performance report")
            return {}

        trades_df = pd.read_csv(self.trades_file)

        # Filter for the lookback period
        cutoff_date = (datetime.now() - timedelta(days=lookback_days)).isoformat()
        recent_trades = trades_df[trades_df["exit_date"] >= cutoff_date]

        if len(recent_trades) == 0:
            logger.warning(f"No trades in the last {lookback_days} days")
            return {}

        # Calculate performance metrics
        metrics = {
            "total_trades": len(recent_trades),
            "winning_trades": len(recent_trades[recent_trades["profit"] > 0]),
            "losing_trades": len(recent_trades[recent_trades["profit"] <= 0]),
            "win_rate": len(recent_trades[recent_trades["profit"] > 0]) / len(recent_trades),
            "total_profit": recent_trades["profit"].sum(),
            "avg_profit": recent_trades["profit"].mean(),
            "avg_win": (
                recent_trades[recent_trades["profit"] > 0]["profit"].mean()
                if len(recent_trades[recent_trades["profit"] > 0]) > 0
                else 0
            ),
            "avg_loss": (
                recent_trades[recent_trades["profit"] <= 0]["profit"].mean()
                if len(recent_trades[recent_trades["profit"] <= 0]) > 0
                else 0
            ),
            "max_win": recent_trades["profit"].max(),
            "max_loss": recent_trades["profit"].min(),
            "profit_factor": (
                abs(
                    recent_trades[recent_trades["profit"] > 0]["profit"].sum()
                    / recent_trades[recent_trades["profit"] <= 0]["profit"].sum()
                )
                if recent_trades[recent_trades["profit"] <= 0]["profit"].sum() != 0
                else float("inf")
            ),
            "avg_duration": recent_trades["duration_days"].mean(),
            "strategies": {},
            "report_date": datetime.now().isoformat(),
            "lookback_days": lookback_days,
        }

        # Calculate strategy-specific metrics
        for strategy in recent_trades["strategy"].unique():
            strategy_trades = recent_trades[recent_trades["strategy"] == strategy]
            metrics["strategies"][strategy] = {
                "total_trades": len(strategy_trades),
                "win_rate": (
                    len(strategy_trades[strategy_trades["profit"] > 0]) / len(strategy_trades)
                    if len(strategy_trades) > 0
                    else 0
                ),
                "total_profit": strategy_trades["profit"].sum(),
                "avg_profit": strategy_trades["profit"].mean() if len(strategy_trades) > 0 else 0,
            }

        # Save metrics to JSON
        with open(self.metrics_file, "w") as f:
            json.dump(metrics, f, indent=4)

        # Generate plots if requested
        if save_plots:
            self._generate_plots(recent_trades)

        logger.info(
            f"Generated performance report: Win rate {metrics['win_rate']:.2%}, "
            f"Total profit ${metrics['total_profit']:.2f}"
        )

        return metrics

    def _generate_plots(self, trades_df):
        """
        Generate and save performance visualization plots.

        Args:
            trades_df (DataFrame): DataFrame containing trade data
        """
        plots_dir = os.path.join(self.data_dir, "plots")
        os.makedirs(plots_dir, exist_ok=True)

        # Convert dates to datetime
        trades_df["entry_date"] = pd.to_datetime(trades_df["entry_date"])
        trades_df["exit_date"] = pd.to_datetime(trades_df["exit_date"])

        # Sort by exit date
        trades_df = trades_df.sort_values("exit_date")

        # 1. Cumulative P&L over time
        plt.figure(figsize=(12, 6))
        cumulative_pnl = trades_df["profit"].cumsum()
        plt.plot(trades_df["exit_date"], cumulative_pnl)
        plt.title("Cumulative P&L Over Time")
        plt.xlabel("Date")
        plt.ylabel("Profit/Loss ($)")
        plt.grid(True)
        plt.savefig(os.path.join(plots_dir, "cumulative_pnl.png"))
        plt.close()

        # 2. P&L by strategy
        plt.figure(figsize=(10, 6))
        strategy_profit = trades_df.groupby("strategy")["profit"].sum()
        strategy_profit.plot(kind="bar")
        plt.title("P&L by Strategy")
        plt.xlabel("Strategy")
        plt.ylabel("Profit/Loss ($)")
        plt.grid(True, axis="y")
        plt.tight_layout()
        plt.savefig(os.path.join(plots_dir, "strategy_pnl.png"))
        plt.close()

        # 3. Win rate by strategy
        plt.figure(figsize=(10, 6))
        win_rates = trades_df.groupby("strategy").apply(lambda x: (x["profit"] > 0).mean())
        win_rates.plot(kind="bar")
        plt.title("Win Rate by Strategy")
        plt.xlabel("Strategy")
        plt.ylabel("Win Rate")
        plt.grid(True, axis="y")
        plt.ylim(0, 1)
        plt.tight_layout()
        plt.savefig(os.path.join(plots_dir, "strategy_win_rate.png"))
        plt.close()

        # 4. Trade duration histogram
        plt.figure(figsize=(10, 6))
        plt.hist(trades_df["duration_days"], bins=10)
        plt.title("Trade Duration Distribution")
        plt.xlabel("Duration (Days)")
        plt.ylabel("Number of Trades")
        plt.grid(True)
        plt.savefig(os.path.join(plots_dir, "duration_histogram.png"))
        plt.close()

        logger.debug(f"Generated performance plots in {plots_dir}")

    def monitor_execution_latency(self, lookback_days=7):
        """
        Monitor and alert on unusual execution latency.

        Args:
            lookback_days (int): Number of days to look back for analysis

        Returns:
            tuple: (average_latency, alert_triggered)
        """
        if not os.path.exists(self.execution_metrics_file):
            return 0, False

        # Load execution metrics
        exec_df = pd.read_csv(self.execution_metrics_file)
        if len(exec_df) == 0:
            return 0, False

        # Convert date to datetime
        exec_df["date"] = pd.to_datetime(exec_df["date"])

        # Filter for recent executions
        cutoff_date = datetime.now() - timedelta(days=lookback_days)
        recent_execs = exec_df[exec_df["date"] >= cutoff_date]

        if len(recent_execs) == 0:
            return 0, False

        # Calculate average latency
        avg_latency = recent_execs["latency_ms"].mean()

        # Check if recent latency is significantly higher than historical
        latest_execs = recent_execs.sort_values("date").tail(5)
        recent_avg = latest_execs["latency_ms"].mean()

        # Alert if recent latency is 50% higher than the lookback period average
        alert_triggered = recent_avg > avg_latency * 1.5

        if alert_triggered:
            logger.warning(
                f"Execution latency alert: Recent average {recent_avg:.2f}ms "
                f"exceeds historical average {avg_latency:.2f}ms by "
                f"{((recent_avg/avg_latency)-1)*100:.1f}%"
            )

        return avg_latency, alert_triggered

    def track_scan_performance(self, lookback_days=30):
        """
        Track scan performance trends over time.

        Args:
            lookback_days (int): Number of days to look back for analysis

        Returns:
            dict: Scan performance metrics
        """
        if not os.path.exists(self.scan_metrics_file):
            return {}

        # Load scan metrics
        scan_df = pd.read_csv(self.scan_metrics_file)
        if len(scan_df) == 0:
            return {}

        # Convert date to datetime
        scan_df["date"] = pd.to_datetime(scan_df["date"])

        # Filter for recent scans
        cutoff_date = datetime.now() - timedelta(days=lookback_days)
        recent_scans = scan_df[scan_df["date"] >= cutoff_date]

        if len(recent_scans) == 0:
            return {}

        # Calculate metrics by scan type
        metrics = {}
        for scan_type in recent_scans["scan_type"].unique():
            type_scans = recent_scans[recent_scans["scan_type"] == scan_type]
            metrics[scan_type] = {
                "avg_execution_time": type_scans["execution_time_ms"].mean(),
                "max_execution_time": type_scans["execution_time_ms"].max(),
                "avg_signals": type_scans["signals_found"].mean(),
                "max_signals": type_scans["signals_found"].max(),
                "avg_memory": type_scans["memory_usage_mb"].mean(),
                "total_scans": len(type_scans),
            }

            # Look for trends
            if len(type_scans) >= 10:
                # Calculate trend in execution time
                type_scans = type_scans.sort_values("date")
                early_execs = type_scans.head(len(type_scans) // 2)["execution_time_ms"].mean()
                recent_execs = type_scans.tail(len(type_scans) // 2)["execution_time_ms"].mean()
                metrics[scan_type]["execution_time_trend"] = (recent_execs / early_execs) - 1
            else:
                metrics[scan_type]["execution_time_trend"] = 0

        return metrics


# Helper for measuring execution time
def time_function_call(func, *args, **kwargs):
    """
    Measure execution time of a function call.

    Args:
        func: Function to call
        *args, **kwargs: Arguments to pass to the function

    Returns:
        tuple: (result, execution_time_ms)
    """
    start_time = time.time()
    result = func(*args, **kwargs)
    end_time = time.time()
    execution_time_ms = (end_time - start_time) * 1000
    return result, execution_time_ms
