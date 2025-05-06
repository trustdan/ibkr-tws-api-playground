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
    Set up the testing environment, including handling TA-Lib imports.
    This fixture runs automatically for all tests.
    """
    print("Setting up testing environment...")
    
    # Try to import TA-Lib
    try:
        import talib
        print("Using real TA-Lib")
    except ImportError:
        # If TA-Lib is not available, use the mock
        print("TA-Lib not available, using mock")
        try:
            # First check if the mock is in auto_vertical_spread_trader
            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from auto_vertical_spread_trader.mock_talib import patch_talib
            patch_talib()
        except Exception as e:
            print(f"Failed to apply mock TA-Lib: {str(e)}")
            raise
    
    # Set CI environment variable
    os.environ['CI'] = 'true'
    
    # Add any other test environment setup here
    print("Test environment setup complete") 