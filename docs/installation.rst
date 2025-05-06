============
Installation
============

This page will help you get started with the Auto Vertical Spread Trader.

Prerequisites
-------------

Before installing, ensure you have:

* Python 3.7 or higher
* Interactive Brokers account with TWS or IB Gateway
* TA-Lib library

Installing from PyPI
-------------------

The easiest way to install is via pip:

.. code-block:: bash

    pip install auto-vertical-spread-trader

This will install the library and all its dependencies (except TA-Lib, which requires special installation).

Installing from Source
--------------------

To install from source:

.. code-block:: bash

    git clone https://github.com/yourusername/auto-vertical-spread-trader.git
    cd auto-vertical-spread-trader
    pip install -e .

For development, install with extra tools:

.. code-block:: bash

    pip install -e ".[dev]"

Installing TA-Lib
----------------

TA-Lib requires special installation steps depending on your operating system.

Windows
~~~~~~~

For Windows, the easiest approach is to use pre-built wheels:

.. code-block:: bash

    pip install --no-cache-dir ta-lib

If that fails, download and install a prebuilt Windows binary from the unofficial builds:
https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib

macOS
~~~~~

For macOS, use Homebrew:

.. code-block:: bash

    brew install ta-lib
    pip install ta-lib

Linux
~~~~~

For Linux systems, compile from source:

.. code-block:: bash

    wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
    tar -xzf ta-lib-0.4.0-src.tar.gz
    cd ta-lib/
    ./configure --prefix=/usr
    make
    sudo make install
    pip install ta-lib

Verifying Installation
---------------------

After installation, verify everything is working:

.. code-block:: bash

    python -c "from auto_vertical_spread_trader import AutoVerticalSpreadTrader; print('Installation successful!')"

If no errors appear, the installation was successful.

Next Steps
---------

Proceed to :doc:`quickstart` to begin using Auto Vertical Spread Trader. 