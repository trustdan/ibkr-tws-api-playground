from setuptools import find_packages, setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

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
    install_requires=[
        "ib_insync>=0.9.70",
        "pandas>=1.3.0",
        "numpy>=1.20.0,<2.0.0",
        "pytz>=2021.1",
        "requests>=2.25.0",
        "lxml>=4.6.3",
        "python-dotenv>=0.19.0",
        "pandas-ta>=0.3.0b0",  # Using pandas-ta instead of TA-Lib, matching version in requirements.txt
    ],
    extras_require={
        "dev": [
            "pytest>=6.2.5",
            "pytest-cov>=2.12.1",
            "black>=22.6.0",
            "flake8>=4.0.1",
            "mypy>=0.971",
        ],
    },
    entry_points={
        "console_scripts": [
            "auto-trader=auto_vertical_spread_trader.runner:main",
        ],
    },
)
