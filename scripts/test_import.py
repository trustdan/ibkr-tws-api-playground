#!/usr/bin/env python
"""
Simple script to test pandas_ta import
"""

import importlib.util
import os
import sys


def print_module_location(module_name):
    """Print location of a module if it can be found"""
    try:
        spec = importlib.util.find_spec(module_name)
        if spec:
            print(f"{module_name} found at: {spec.origin}")
        else:
            print(f"{module_name} not found in sys.path")
    except Exception as e:
        print(f"Error finding {module_name}: {e}")


# Print debug info
print(f"Python version: {sys.version}")
print(f"Python executable: {sys.executable}")
print(f"Current working directory: {os.getcwd()}")
print("\nSite packages directories in sys.path:")
for path in sys.path:
    if "site-packages" in path:
        print(f"  {path}")
        if os.path.exists(path):
            try:
                contents = os.listdir(path)
                pandas_related = [f for f in contents if "pandas" in f.lower()]
                if pandas_related:
                    print(f"    Pandas related: {pandas_related}")
            except Exception as e:
                print(f"    Error listing directory: {e}")

# Try importing directly
print("\nTrying direct import...")
try:
    import pandas_ta

    print(f"SUCCESS: pandas_ta version: {pandas_ta.__version__}")
    print(f"pandas_ta location: {pandas_ta.__file__}")
except ImportError as e:
    print(f"FAILED to import pandas_ta: {e}")

# Try finding the module
print("\nTrying to locate pandas_ta module:")
print_module_location("pandas_ta")

# Check for any misnamed packages
print("\nChecking for any misnamed pandas_ta directories:")
for path in sys.path:
    if "site-packages" in path and os.path.exists(path):
        try:
            items = os.listdir(path)
            for item in items:
                if "pandas" in item.lower() and "ta" in item.lower():
                    full_path = os.path.join(path, item)
                    print(f"Found: {full_path}")
                    if os.path.isdir(full_path):
                        sub_items = os.listdir(full_path)
                        print(
                            f"  Contains: {sub_items[:10]}{' ...' if len(sub_items) > 10 else ''}"
                        )
        except Exception as e:
            print(f"Error checking {path}: {e}")

print("\nDone.")
