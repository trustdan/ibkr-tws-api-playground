"""
Configure pytest test environment for the project.
This file is loaded automatically by pytest at the start of testing.
"""

import sys
import os
import pytest
from unittest.mock import MagicMock
from pathlib import Path

# Add the parent directory to sys.path (if needed)
sys.path.insert(0, str(Path(__file__).parent.parent))


# Mock ib_insync before any imports can happen
class MockIB:
    def __init__(self, *args, **kwargs):
        pass

    def connect(self, *args, **kwargs):
        return True

    def disconnect(self):
        return True

    def isConnected(self):
        return True


# Create a system-wide mock for ib_insync
sys.modules["ib_insync"] = MagicMock()
sys.modules["ib_insync"].IB = MockIB
sys.modules["ib_insync"].Stock = MagicMock()
sys.modules["ib_insync"].Option = MagicMock()
sys.modules["ib_insync"].ComboLeg = MagicMock()
sys.modules["ib_insync"].Order = MagicMock()
sys.modules["ib_insync"].util = MagicMock()


@pytest.fixture(scope="session", autouse=True)
def setup_testing_environment():
    """
    Set up the testing environment, including verifying pandas-ta availability.
    This fixture runs automatically for all tests.
    """
    print("Setting up testing environment...")

    # Try to import pandas-ta
    try:
        import pandas_ta as ta

        print(f"pandas-ta is available. Categories: {list(ta.Category.keys())}")
    except ImportError:
        print("Warning: pandas-ta not available, some tests may fail")
        print("Install with: pip install pandas-ta>=0.3.0b0")

    # Set CI environment variable
    os.environ["CI"] = "true"

    # Add any other test environment setup here
    print("Test environment setup complete")


# Create sample test data
@pytest.fixture
def sample_price_data():
    """
    Create sample price dataframe for testing
    """
    import pandas as pd
    import numpy as np

    # Create sample data with 60 days
    dates = pd.date_range(end=pd.Timestamp.today(), periods=60)
    df = pd.DataFrame(
        {
            "open": np.random.rand(60) * 100 + 100,
            "high": np.random.rand(60) * 100 + 100,
            "low": np.random.rand(60) * 100 + 100,
            "close": np.random.rand(60) * 100 + 100,
            "volume": np.random.rand(60) * 1000000,
        },
        index=dates,
    )

    # Add indicators
    df["MA50"] = df["close"].rolling(50, min_periods=1).mean()
    df["ATR14"] = (
        df["high"].rolling(14, min_periods=1).mean() - df["low"].rolling(14, min_periods=1).mean()
    )

    return df
