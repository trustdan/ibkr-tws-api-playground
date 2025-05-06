==============================
Auto Vertical Spread Trader
==============================

A modular, production-ready system for automated vertical spread trading with Interactive Brokers.

.. image:: https://img.shields.io/badge/python-3.7+-blue.svg
   :target: https://www.python.org/downloads/
   :alt: Python 3.7+

.. image:: https://img.shields.io/badge/License-MIT-yellow.svg
   :target: https://opensource.org/licenses/MIT
   :alt: License: MIT

.. image:: https://github.com/yourusername/auto-vertical-spread-trader/actions/workflows/python-tests.yml/badge.svg
   :target: https://github.com/yourusername/auto-vertical-spread-trader/actions/workflows/python-tests.yml
   :alt: Tests

.. image:: https://codecov.io/gh/yourusername/auto-vertical-spread-trader/branch/main/graph/badge.svg
   :target: https://codecov.io/gh/yourusername/auto-vertical-spread-trader
   :alt: Coverage

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
   :target: https://github.com/psf/black
   :alt: Code style: black


Features
--------

* **Fundamental Filtering**: Market cap ≥ $10B, price > $20, optionable stocks
* **Technical Analysis**: 50 DMA trend analysis, volume filtering, consolidation patterns
* **Option Selection**: Delta-based strike selection, cost limits, R:R ratio enforcement
* **Risk Management**: ATR-based stop losses, position limits, daily trade limits
* **Execution**: Late-day trade entries, clean reconnection handling, email alerts

Contents
--------

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   installation
   quickstart
   configuration
   usage
   strategies
   faq

.. toctree::
   :maxdepth: 2
   :caption: Technical Documentation

   api/modules
   development
   contributing
   security

.. toctree::
   :maxdepth: 1
   :caption: Project

   changelog
   governance
   license

Indices and tables
=================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search` 