# TA-Lib Bootstrap Script for Windows (PowerShell)
# Installs TA-Lib using conda (conda-forge) for Windows
# Usage: .\scripts\bootstrap_talib.ps1

# Stop on errors
$ErrorActionPreference = "Stop"

Write-Host "TA-Lib Bootstrap Script for Windows (conda-based)"
Write-Host "=============================================" -ForegroundColor Green

# Detect CI environment
$CI_ENV = $false
if ($env:CI -or $env:GITHUB_ACTIONS) {
    Write-Host "CI environment detected" -ForegroundColor Yellow
    $CI_ENV = $true
}

# Check if conda is installed
$CONDA_ALREADY_INSTALLED = $false
try {
    $condaPath = (Get-Command conda -ErrorAction SilentlyContinue).Source
    if ($condaPath) {
        Write-Host "Conda is already installed at: $condaPath" -ForegroundColor Green
        $CONDA_ALREADY_INSTALLED = $true
    }
}
catch {
    Write-Host "Conda not found. Installing Miniconda..." -ForegroundColor Yellow
}

if (-not $CONDA_ALREADY_INSTALLED) {
    # Download and install Miniconda
    $MINICONDA_URL = "https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe"
    $INSTALLER_PATH = Join-Path $env:TEMP "miniconda_installer.exe"
    
    Write-Host "Downloading Miniconda from $MINICONDA_URL"
    
    # Download the installer
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest -Uri $MINICONDA_URL -OutFile $INSTALLER_PATH
    
    Write-Host "Installing Miniconda..."
    # Install Miniconda silently
    Start-Process -FilePath $INSTALLER_PATH -ArgumentList "/InstallationType=JustMe /RegisterPython=0 /S /D=$env:USERPROFILE\miniconda3" -Wait
    
    # Remove the installer
    Remove-Item $INSTALLER_PATH
    
    # Set up conda in current shell
    $env:PATH = "$env:USERPROFILE\miniconda3;$env:USERPROFILE\miniconda3\Scripts;$env:USERPROFILE\miniconda3\Library\bin;$env:PATH"
    
    Write-Host "Conda installed successfully!" -ForegroundColor Green
}

# Initialize conda for PowerShell
if ($CONDA_ALREADY_INSTALLED -or (Test-Path "$env:USERPROFILE\miniconda3\Scripts\conda.exe")) {
    # Ensure conda is available in this session
    if (-not (Get-Command conda -ErrorAction SilentlyContinue)) {
        if (Test-Path "$env:USERPROFILE\miniconda3\Scripts\conda.exe") {
            $env:PATH = "$env:USERPROFILE\miniconda3;$env:USERPROFILE\miniconda3\Scripts;$env:USERPROFILE\miniconda3\Library\bin;$env:PATH"
        }
    }
    
    Write-Host "Initializing conda for PowerShell..."
    # Run conda init powershell
    conda init powershell
    
    # Source the profile to enable conda for the current session
    try {
        & $PROFILE -ErrorAction SilentlyContinue
    } catch {
        Write-Host "Note: You may need to restart your PowerShell session after this script completes." -ForegroundColor Yellow
    }
}

# Add conda-forge channel
Write-Host "Adding conda-forge channel..."
conda config --add channels conda-forge
conda config --set channel_priority strict

# Environment name with CI-specific suffix if in CI
$ENV_NAME = "talib-env"
if ($CI_ENV) {
    $ENV_NAME = "talib-env-ci"
}

# Check if we're in a conda environment or create a new one
$CURRENT_ENV = $env:CONDA_DEFAULT_ENV
if (-not $CURRENT_ENV -or $CURRENT_ENV -eq "base") {
    Write-Host "Creating a new conda environment '$ENV_NAME'..." -ForegroundColor Green
    # Force "yes" for CI environments
    conda create -y -n $ENV_NAME python=3.10
    
    # Try to activate the environment
    try {
        Write-Host "Activating conda environment..."
        conda activate $ENV_NAME
    }
    catch {
        Write-Host "Could not automatically activate environment. Please run the following manually:" -ForegroundColor Yellow
        Write-Host "    conda activate $ENV_NAME" -ForegroundColor Yellow
        Write-Host "    conda install -y -c conda-forge ta-lib numpy" -ForegroundColor Yellow
        exit 0
    }
}
else {
    Write-Host "Using existing conda environment: $CURRENT_ENV" -ForegroundColor Green
    $ENV_NAME = $CURRENT_ENV
}

# Install TA-Lib and NumPy from conda-forge
Write-Host "Installing TA-Lib from conda-forge..."
# Add extra flags for CI environments
if ($CI_ENV) {
    conda install -y -c conda-forge ta-lib numpy --no-update-deps
}
else {
    conda install -y -c conda-forge ta-lib numpy
}

# Set environment variables for pip installs
$CONDA_PREFIX = if ($env:CONDA_PREFIX) { $env:CONDA_PREFIX } else { (Join-Path (conda info --base) "envs\$ENV_NAME") }
$TA_LIBRARY_PATH = Join-Path $CONDA_PREFIX "Library\lib"
$TA_INCLUDE_PATH = Join-Path $CONDA_PREFIX "Library\include"

$env:TA_LIBRARY_PATH = $TA_LIBRARY_PATH
$env:TA_INCLUDE_PATH = $TA_INCLUDE_PATH

Write-Host "Setting TA_LIBRARY_PATH=$TA_LIBRARY_PATH"
Write-Host "Setting TA_INCLUDE_PATH=$TA_INCLUDE_PATH"

# For GitHub Actions, make these environment variables available to subsequent steps
if ($CI_ENV -and $env:GITHUB_ENV) {
    Add-Content -Path $env:GITHUB_ENV -Value "TA_LIBRARY_PATH=$TA_LIBRARY_PATH"
    Add-Content -Path $env:GITHUB_ENV -Value "TA_INCLUDE_PATH=$TA_INCLUDE_PATH"
    Add-Content -Path $env:GITHUB_ENV -Value "CONDA_PREFIX=$CONDA_PREFIX"
    
    # Add conda paths to PATH for subsequent steps
    Add-Content -Path $env:GITHUB_PATH -Value "$CONDA_PREFIX"
    Add-Content -Path $env:GITHUB_PATH -Value "$CONDA_PREFIX\Scripts"
    Add-Content -Path $env:GITHUB_PATH -Value "$CONDA_PREFIX\Library\bin"
}

# Windows-specific fallback installation method
function Install-TalibWindowsFallback {
    Write-Host "Attempting Windows fallback installation..." -ForegroundColor Yellow
    
    # Get Python version for the wheel URL
    $PY_VER = python -c "import sys; print(f'{sys.version_info.major}{sys.version_info.minor}')"
    $ARCH = "amd64"  # Assuming 64-bit
    
    # For GitHub Actions, try to install pre-compiled wheel from GitHub
    if ($CI_ENV) {
        Write-Host "Trying to download pre-compiled wheel for Windows CI..." -ForegroundColor Yellow
        
        # Alternative URLs for wheels
        $WHEEL_URLS = @(
            "https://github.com/conda-forge/ta-lib-feedstock/files/7028548/ta_lib-0.4.24-cp${PY_VER}-cp${PY_VER}-win_${ARCH}.whl",
            "https://github.com/TA-Lib/ta-lib-python/releases/download/TA_Lib-0.4.24/TA_Lib-0.4.24-cp${PY_VER}-cp${PY_VER}-win_${ARCH}.whl",
            "https://download.lfd.uci.edu/pythonlibs/archived/ta-lib-0.4.24-cp${PY_VER}-cp${PY_VER}-win_${ARCH}.whl"
        )
        
        $success = $false
        foreach ($URL in $WHEEL_URLS) {
            Write-Host "Trying to install from: $URL" -ForegroundColor Yellow
            try {
                pip install --no-cache-dir $URL
                Write-Host "Successfully installed TA-Lib from wheel!" -ForegroundColor Green
                $success = $true
                break
            }
            catch {
                Write-Host "Failed to install from $URL" -ForegroundColor Red
            }
        }
        
        if (-not $success) {
            Write-Host "Wheel installation failed. Trying conda as fallback." -ForegroundColor Yellow
            # We're already in a conda environment, so just install ta-lib
            conda install -y -c conda-forge ta-lib
        }
    }
    else {
        # Try installing from wheel for non-CI Windows
        try {
            pip install --no-cache-dir "https://download.lfd.uci.edu/pythonlibs/archived/ta-lib-0.4.24-cp${PY_VER}-cp${PY_VER}-win_${ARCH}.whl"
        }
        catch {
            try {
                pip install --no-cache-dir "https://github.com/conda-forge/ta-lib-feedstock/files/7028548/ta_lib-0.4.24-cp${PY_VER}-cp${PY_VER}-win_${ARCH}.whl"
            }
            catch {
                Write-Host "Wheel installation failed. Using conda as fallback." -ForegroundColor Yellow
            }
        }
    }
}

# Verify installation
Write-Host "Verifying TA-Lib installation..."

# Create a temp verification script
$VERIFY_SCRIPT = @"
import sys
try:
    import numpy as np
    import talib
    print(f'TA-Lib version: {talib.__version__}')
    print(f'Available functions: {len(talib.get_functions())}')
    
    # Test SMA function
    data = np.random.random(100)
    output = talib.SMA(data)
    print(f'SMA calculation successful: {output.shape}')
    print('TA-Lib installation successful! ✓')
    sys.exit(0)
except ImportError as e:
    print(f'Error importing talib: {e}')
    sys.exit(1)
except Exception as e:
    print(f'Error using talib: {e}')
    sys.exit(1)
"@

$VERIFY_SCRIPT_PATH = Join-Path $env:TEMP "verify_talib_temp.py"
Set-Content -Path $VERIFY_SCRIPT_PATH -Value $VERIFY_SCRIPT

# Run verification
$verification_success = $false
try {
    python $VERIFY_SCRIPT_PATH
    if ($LASTEXITCODE -eq 0) {
        $verification_success = $true
    }
}
catch {
    Write-Host "TA-Lib verification failed. Attempting fallback installation..." -ForegroundColor Red
    Install-TalibWindowsFallback
    
    # Verify again after fallback
    try {
        python $VERIFY_SCRIPT_PATH
        if ($LASTEXITCODE -eq 0) {
            $verification_success = $true
        }
    }
    catch {
        Write-Host "TA-Lib installation failed even after fallback attempt." -ForegroundColor Red
    }
}

# Clean up temporary script
Remove-Item $VERIFY_SCRIPT_PATH -ErrorAction SilentlyContinue

if ($verification_success) {
    Write-Host "TA-Lib bootstrap complete! ✓" -ForegroundColor Green
}
else {
    Write-Host "TA-Lib verification failed. Please check the errors above." -ForegroundColor Red
}

# If we're in CI, output information for subsequent steps
if ($CI_ENV) {
    Write-Host ""
    Write-Host "CI Environment Information:" -ForegroundColor Cyan
    Write-Host "Environment: $ENV_NAME"
    Write-Host "TA_LIBRARY_PATH: $TA_LIBRARY_PATH"
    Write-Host "TA_INCLUDE_PATH: $TA_INCLUDE_PATH"
    Write-Host "CONDA_PREFIX: $CONDA_PREFIX"
    Write-Host ""
}

# Display usage instructions
Write-Host ""
Write-Host "====================================" -ForegroundColor Green
Write-Host "TA-Lib Usage Instructions:" -ForegroundColor Green
Write-Host ""
Write-Host "1. Activate the conda environment:"
Write-Host "   conda activate $ENV_NAME" -ForegroundColor Yellow
Write-Host ""
Write-Host "2. Import in Python:"
Write-Host "   import talib" -ForegroundColor Yellow
Write-Host "   import numpy as np" -ForegroundColor Yellow
Write-Host ""
Write-Host "3. Example usage:"
Write-Host '   close_prices = np.array([44.55, 44.3, 44.36, 43.82, 44.46, 44.49, 44.7])' -ForegroundColor Yellow
Write-Host '   sma = talib.SMA(close_prices, timeperiod=3)' -ForegroundColor Yellow
Write-Host ""
Write-Host "4. List available functions:"
Write-Host '   print(talib.get_functions())' -ForegroundColor Yellow
Write-Host "====================================" -ForegroundColor Green
Write-Host ""
Write-Host "Installation Notes:"
Write-Host "* If you're using this in a CI environment, make sure to set TA_LIBRARY_PATH and TA_INCLUDE_PATH"
Write-Host "* For Windows, pip install may need specific wheel versions"
Write-Host "* Make sure to activate the conda environment before using TA-Lib"
Write-Host "=====================================" -ForegroundColor Green 