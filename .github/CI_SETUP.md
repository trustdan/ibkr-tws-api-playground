# CI Setup and Troubleshooting

This document explains how dependencies are set up in our continuous integration (CI) environment, with special focus on TA-Lib installation which is the most complex dependency.

## TA-Lib Installation in CI

TA-Lib consists of two components:
1. A C library (`libta_lib.so`) that contains the core implementation
2. A Python wrapper that interfaces with the C library

The key challenge in CI environments is ensuring these components are installed correctly and can find each other at runtime.

### Installation Steps in Our Workflows

Our GitHub Actions workflows handle TA-Lib installation with the following approach:

1. **Install the C library from source**:
   ```bash
   # Install build dependencies
   sudo apt-get install -y build-essential wget autoconf libtool pkg-config

   # Download and install TA-Lib from source
   wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
   tar -xzf ta-lib-0.4.0-src.tar.gz
   cd ta-lib/
   ./configure --prefix=/usr
   make
   sudo make install
   ```

2. **Create symlinks to handle naming differences**:
   ```bash
   # Find the actual library path
   ACTUAL_LIB_PATH=$(sudo find /usr -name "libta_lib.so*" -type f | head -1)
   
   # Create symlinks with consistent naming
   sudo ln -sf ${ACTUAL_LIB_PATH} /usr/lib/libta-lib.so
   ```

3. **Update shared library cache**:
   ```bash
   sudo ldconfig
   ```

4. **Install Python wrapper with explicit flags**:
   ```bash
   # Environment variables to ensure correct linking
   export TA_LIBRARY_PATH=/usr/lib
   export TA_INCLUDE_PATH=/usr/include
   
   # Install with explicit compiler flags and no build isolation
   LDFLAGS="-L/usr/lib" CFLAGS="-I/usr/include" pip install --no-build-isolation TA-Lib
   ```

5. **Verify installation**:
   ```bash
   python -c "import talib; print(talib.get_functions()[:5])"
   ```

## Common Issues and Solutions

### 1. Undefined Symbol Errors

Example error:
```
ImportError: /opt/python/3.10/lib/python3.10/site-packages/talib/_ta_lib.cpython-310-x86_64-linux-gnu.so: undefined symbol: TA_AVGDEV_Lookback
```

**Causes**:
- The Python wrapper is looking for functions that don't exist in the installed C library
- The C library was installed in a location where the loader can't find it
- Symlinks are incorrect or missing

**Solutions**:
- Ensure both the C library and Python wrapper are the same version
- Check if the symbols exist: `nm -D /usr/lib/libta_lib.so | grep TA_AVGDEV_Lookback`
- Create proper symlinks from `libta_lib.so` to `libta-lib.so`
- Use `--no-build-isolation` when installing with pip

### 2. Library Not Found Errors

Example error:
```
ImportError: libta_lib.so.0: cannot open shared object file: No such file or directory
```

**Causes**:
- The C library is not in the loader's search path
- The library cache hasn't been updated

**Solutions**:
- Run `sudo ldconfig` after installation
- Verify the library is installed: `ldconfig -p | grep ta`
- Add the library path to LD_LIBRARY_PATH
- Try loading the library directly with ctypes to debug: 
  ```python
  import ctypes
  ctypes.CDLL("libta-lib.so")
  ```

### 3. Build Failures

**Causes**:
- Missing build dependencies
- Incorrect compiler flags

**Solutions**:
- Install required build tools: `sudo apt-get install build-essential autoconf libtool pkg-config`
- Set explicit environment variables: `LDFLAGS="-L/usr/lib" CFLAGS="-I/usr/include"`
- Use verbose pip installation: `pip install --verbose --no-build-isolation TA-Lib`

## Debugging Tools

When troubleshooting TA-Lib in CI, these commands are useful:

1. **Find installed libraries**:
   ```bash
   find /usr -name "libta_lib*"
   ldconfig -p | grep ta
   ```

2. **Check symbols in the library**:
   ```bash
   nm -D /usr/lib/libta_lib.so | grep -E "TA_AVGDEV_Lookback|TA_ATR|TA_SMA"
   ```

3. **Verify library loading**:
   ```bash
   python -c "import ctypes; ctypes.CDLL('libta-lib.so'); print('Library loaded')"
   ```

4. **Check symlinks**:
   ```bash
   ls -la /usr/lib/libta-lib.so*
   ls -la /usr/lib/libta_lib.so*
   ```

5. **Verbose pip installation**:
   ```bash
   pip install --verbose --no-build-isolation TA-Lib
   ```

## Best Practices

- Always use `--no-build-isolation` when installing TA-Lib with pip in CI
- Create explicit symlinks for both `libta-lib.so` and `libta-lib.so.0`
- Run `ldconfig` after installing the C library
- Verify installation with a simple function call, not just import
- Set explicit library paths via environment variables

By following these practices, TA-Lib should work reliably in CI environments. 