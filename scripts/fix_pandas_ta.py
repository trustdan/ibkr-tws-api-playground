#!/usr/bin/env python
"""
Fix pandas-ta NaN Import Issue
-----------------------------
This script fixes compatibility issues with newer NumPy versions in pandas-ta.
It replaces 'from numpy import NaN' with 'from numpy import nan'.

Usage: python scripts/fix_pandas_ta.py
"""

import os
import re
import site
import sys


def find_pandas_ta_path():
    """Find the pandas_ta installation path"""
    try:
        import pandas_ta

        return os.path.dirname(pandas_ta.__file__)
    except ImportError:
        # If pandas_ta isn't importable, search in site-packages
        site_packages = site.getsitepackages()
        user_site = site.getusersitepackages()

        all_paths = site_packages + [user_site]

        for path in all_paths:
            pandas_ta_path = os.path.join(path, "pandas_ta")
            if os.path.exists(pandas_ta_path):
                return pandas_ta_path

    return None


def fix_nan_imports(file_path):
    """Fix NaN imports in a single file"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Replace variations of NaN imports
    patterns = [
        (r"from numpy import NaN as npNaN", "from numpy import nan as npNaN"),
        (r"from numpy import NaN", "from numpy import nan"),
    ]

    fixed_content = content
    for pattern, replacement in patterns:
        fixed_content = re.sub(pattern, replacement, fixed_content)

    if fixed_content != content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(fixed_content)
        return True

    return False


def fix_all_nan_imports(pandas_ta_path):
    """Fix all NaN imports in the pandas_ta package"""
    files_fixed = []

    # Process main directory python files
    for file in os.listdir(pandas_ta_path):
        if file.endswith(".py"):
            file_path = os.path.join(pandas_ta_path, file)
            if fix_nan_imports(file_path):
                files_fixed.append(file_path)

    # Process subdirectories
    for dirpath, dirnames, filenames in os.walk(pandas_ta_path):
        for file in filenames:
            if file.endswith(".py"):
                file_path = os.path.join(dirpath, file)
                if fix_nan_imports(file_path):
                    files_fixed.append(file_path)

    return files_fixed


def main():
    """Main function to fix pandas_ta package"""
    print("Fixing pandas-ta NaN import compatibility...")

    pandas_ta_path = find_pandas_ta_path()
    if not pandas_ta_path:
        print("Error: Could not find pandas_ta installation.")
        return 1

    print(f"Found pandas_ta at: {pandas_ta_path}")

    # Add debug info - check for squeeze_pro.py specifically
    squeeze_pro_path = os.path.join(pandas_ta_path, "momentum", "squeeze_pro.py")
    if os.path.exists(squeeze_pro_path):
        print(f"Found squeeze_pro.py at: {squeeze_pro_path}")
        with open(squeeze_pro_path, "r", encoding="utf-8") as f:
            content = f.read(200)  # Read first 200 bytes
            print(f"First few lines of squeeze_pro.py:\n{content}")

    files_fixed = fix_all_nan_imports(pandas_ta_path)

    if files_fixed:
        print(f"Fixed {len(files_fixed)} files:")
        for file in files_fixed:
            print(f"  - {os.path.basename(file)}")
        print("\nFix completed successfully!")
    else:
        print(
            "No files needed fixing. This could indicate the files are already fixed or using correct syntax."
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
