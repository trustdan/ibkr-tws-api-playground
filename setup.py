from setuptools import setup, find_packages
import os
import sys

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Check if the TA-Lib is available based on environment
talib_available = False
try:
    import talib
    talib_available = True
except ImportError:
    # Check if we're in CI environment
    if os.environ.get('CI') == 'true':
        print("Warning: TA-Lib not available, but running in CI environment so marking as available")
        talib_available = True

# Base dependencies that don't include TA-Lib
install_requires = [
    "ib_insync>=0.9.70",
    "pandas>=1.3.0",
    "numpy>=1.20.0",
    "pytz>=2021.1",
    "requests>=2.25.0",
    "lxml>=4.6.3",
    "python-dotenv>=0.19.0",
]

# Add TA-Lib only if it's available or we can build it
if talib_available:
    install_requires.append("TA-Lib>=0.4.24")

setup(
    name="auto_vertical_spread_trader",
    version="1.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="Automated vertical spread trading system for Interactive Brokers",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/auto-vertical-spread-trader",
    project_urls={
        "Bug Tracker": "https://github.com/yourusername/auto-vertical-spread-trader/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Office/Business :: Financial :: Investment",
        "Intended Audience :: Financial and Insurance Industry",
    ],
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=install_requires,
    extras_require={
        "dev": [
            "pytest>=6.2.5",
            "pytest-cov>=2.12.1",
            "black>=22.6.0",
            "flake8>=4.0.1",
            "mypy>=0.971",
        ],
        "talib": ["TA-Lib>=0.4.24"],
    },
    entry_points={
        "console_scripts": [
            "auto-trader=auto_vertical_spread_trader.runner:main",
        ],
    },
) 