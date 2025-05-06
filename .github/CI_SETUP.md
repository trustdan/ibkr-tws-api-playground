# CI Setup and Troubleshooting

This document explains how dependencies are set up in our continuous integration (CI) environment, with special focus on TA-Lib installation which is the most complex dependency.

## TA-Lib Installation in CI

TA-Lib consists of two components:
1. A C library (`libta-lib.so`) that contains the core implementation
2. A Python wrapper that interfaces with the C library

### Recommended Installation Method (Ubuntu/Debian)

On Ubuntu 22.04-based CI runners (like GitHub Actions), we use the system package for TA-Lib which is the most reliable approach:

```bash
# Specify Ubuntu 22.04 in your workflow
runs-on: ubuntu-22.04

# Install the development package that includes headers and the shared library
sudo apt-get update
sudo apt-get install -y libta-lib-dev

# Install the Python wrapper
pip install TA-Lib
```

> **Note:** Ubuntu 24.04 (Noble Numbat) and newer versions do not include the `libta-lib-dev` package. For these environments, use the source installation method below.

This approach ensures that:
1. The C library and its headers are properly installed in standard system locations
2. All required symbols are available in the library
3. The Python wrapper will build against the correct headers and link to the system library

### Verification

To verify the installation is working correctly:

```bash
python - << 'EOF'
import ctypes, talib
# Ensure the C library loads
ctypes.CDLL('libta-lib.so')
# Ensure the wrapper finds its symbols
funcs = talib.get_functions()
print('TA-Lib functions sample:', funcs[:5])
EOF
```

## Alternative Installation Methods

For CI environments where the system package is not available, you can build from source as described below, but this is more complex and error-prone.

### Building from Source

If you must build from source (e.g., on non-Debian systems), follow these steps:

1. **Install build dependencies**:
   ```bash
   sudo apt-get install -y build-essential wget autoconf libtool pkg-config
   ```

2. **Build and install the C library**:
   ```bash
   wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
   tar -xzf ta-lib-0.4.0-src.tar.gz
   cd ta-lib/
   ./configure --prefix=/usr
   make
   sudo make install
   cd ..
   ```

3. **Create symlinks if needed**:
   ```bash
   # The C library is named libta_lib.so but Python looks for libta-lib.so
   sudo ln -sf /usr/lib/libta_lib.so /usr/lib/libta-lib.so
   sudo ln -sf /usr/lib/libta_lib.so.0 /usr/lib/libta-lib.so.0
   sudo ldconfig
   ```

4. **Install the Python wrapper with explicit flags**:
   ```bash
   LDFLAGS="-L/usr/lib" CFLAGS="-I/usr/include" pip install --no-build-isolation TA-Lib
   ```

## Common Issues and Solutions

### 1. Undefined Symbol Errors

Example error:
```
ImportError: /opt/python/3.10/lib/python3.10/site-packages/talib/_ta_lib.cpython-310-x86_64-linux-gnu.so: undefined symbol: TA_AVGDEV_Lookback
```

**Solution**: Use the system package instead of building from source:
```bash
sudo apt-get install -y libta-lib-dev
pip install TA-Lib
```

### 2. Library Not Found Errors

Example error:
```
ImportError: libta_lib.so.0: cannot open shared object file: No such file or directory
```

**Solution**: 
- Ensure the library is installed in a standard location
- Run `sudo ldconfig` after installation
- Use the system package which properly registers the library

### 3. Build Failures

**Solution**:
- Use the system package (`libta-lib-dev`) when available
- Set explicit environment variables only if you must build from source

## Best Practices

1. **Always prefer system packages when available**:
   ```bash
   sudo apt-get install -y libta-lib-dev
   ```

2. **Verify installation with both direct loading and imports**:
   ```python
   import ctypes, talib
   ctypes.CDLL('libta-lib.so')  # Direct library loading
   talib.get_functions()[:5]    # Function availability
   ```

3. **Test an actual function call, not just imports**:
   ```python
   import numpy as np
   close = np.random.random(100)
   output = talib.SMA(close)    # Test a calculation
   ```

By following these practices, TA-Lib should work reliably in CI environments. 