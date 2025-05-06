"""
Configure pytest test environment for the project.
This file is loaded automatically by pytest at the start of testing.
"""

import sys
import os
import pytest

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
    os.environ['CI'] = 'true'
    
    # Add any other test environment setup here
    print("Test environment setup complete") 