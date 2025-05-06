# PowerShell script for installing TA-Lib on Windows
# Usage: .\scripts\bootstrap_talib.ps1

Write-Host "TA-Lib Bootstrap Script for Windows" -ForegroundColor Cyan
Write-Host "===================================="

# Check if Conda is installed
$condaExists = $null -ne (Get-Command conda -ErrorAction SilentlyContinue)

if (-not $condaExists) {
    Write-Host "Conda not found. Installing Miniconda..." -ForegroundColor Yellow
    
    # Download Miniconda
    $minicondaUrl = "https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe"
    $installerPath = "$env:TEMP\miniconda_installer.exe"
    
    Write-Host "Downloading Miniconda from $minicondaUrl" -ForegroundColor Yellow
    Invoke-WebRequest -Uri $minicondaUrl -OutFile $installerPath
    
    # Install Miniconda
    Write-Host "Installing Miniconda... This may take a few minutes." -ForegroundColor Yellow
    Start-Process -FilePath $installerPath -ArgumentList "/S /RegisterPython=1 /AddToPath=1 /D=$env:USERPROFILE\miniconda3" -Wait
    
    # Remove installer
    Remove-Item $installerPath
    
    Write-Host "Miniconda installed. Please restart PowerShell and run this script again." -ForegroundColor Green
    exit 0
} else {
    Write-Host "Conda is already installed." -ForegroundColor Green
}

# Add conda-forge channel
Write-Host "Adding conda-forge channel..." -ForegroundColor Yellow
conda config --add channels conda-forge
conda config --set channel_priority strict

# Check if we're in a conda environment
$inCondaEnv = $env:CONDA_DEFAULT_ENV -ne $null -and $env:CONDA_DEFAULT_ENV -ne ""

if (-not $inCondaEnv) {
    Write-Host "Creating a new conda environment 'talib-env'..." -ForegroundColor Yellow
    conda create -y -n talib-env python=3.9
    
    # Provide instructions to activate the environment
    Write-Host "Please activate the conda environment by running:" -ForegroundColor Yellow
    Write-Host "conda activate talib-env" -ForegroundColor Cyan
    Write-Host "Then run this script again."
    exit 0
} else {
    Write-Host "Using existing conda environment: $env:CONDA_DEFAULT_ENV" -ForegroundColor Green
}

# Install TA-Lib from conda-forge
Write-Host "Installing TA-Lib from conda-forge..." -ForegroundColor Yellow
conda install -y -c conda-forge ta-lib=0.4.24 numpy

# Set environment variables for pip installs if needed
$condaPrefix = if ($env:CONDA_PREFIX) { $env:CONDA_PREFIX } else { "$env:USERPROFILE\miniconda3\envs\talib-env" }
$env:TA_LIBRARY_PATH = "$condaPrefix\Library\lib"
$env:TA_INCLUDE_PATH = "$condaPrefix\Library\include"
Write-Host "Setting TA_LIBRARY_PATH=$env:TA_LIBRARY_PATH" -ForegroundColor Green
Write-Host "Setting TA_INCLUDE_PATH=$env:TA_INCLUDE_PATH" -ForegroundColor Green

# Function for wheel-based fallback installation
function Install-Talib-Wheel-Fallback {
    Write-Host "Attempting wheel-based installation fallback..." -ForegroundColor Yellow
    
    # Get Python version info
    $pyVersionInfo = python -c "import sys; print(f'{sys.version_info.major}{sys.version_info.minor}')"
    $arch = "amd64"  # Assuming 64-bit
    
    # Try installing wheels from different sources
    Write-Host "Trying to install from wheel..." -ForegroundColor Yellow
    
    $result = $false
    try {
        pip install --no-cache-dir "https://download.lfd.uci.edu/pythonlibs/archived/ta-lib-0.4.24-cp$pyVersionInfo-cp$pyVersionInfo-win_$arch.whl"
        $result = $true
    } catch {
        Write-Host "First wheel source failed, trying alternative source..." -ForegroundColor Yellow
        try {
            pip install --no-cache-dir "https://github.com/conda-forge/ta-lib-feedstock/files/7028548/ta_lib-0.4.24-cp$pyVersionInfo-cp$pyVersionInfo-win_$arch.whl"
            $result = $true
        } catch {
            Write-Host "Wheel installation failed." -ForegroundColor Red
        }
    }
    
    return $result
}

# Verify installation
Write-Host "Verifying TA-Lib installation..." -ForegroundColor Yellow

# Create a temporary Python script for verification
$verificationScript = @"
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

$verificationScriptPath = "$env:TEMP\verify_talib.py"
$verificationScript | Out-File -FilePath $verificationScriptPath -Encoding utf8

# Run verification script
$verificationResult = python $verificationScriptPath
if ($LASTEXITCODE -ne 0) {
    Write-Host "TA-Lib verification failed. Attempting fallback installation..." -ForegroundColor Red
    
    $fallbackSuccess = Install-Talib-Wheel-Fallback
    
    if ($fallbackSuccess) {
        # Verify again after fallback
        $verificationResult = python $verificationScriptPath
        if ($LASTEXITCODE -eq 0) {
            Write-Host "TA-Lib installed successfully after fallback!" -ForegroundColor Green
        } else {
            Write-Host "TA-Lib installation failed even after fallback attempt." -ForegroundColor Red
        }
    } else {
        Write-Host "All fallback methods failed. Please try manual installation." -ForegroundColor Red
    }
} else {
    Write-Host "TA-Lib installed and verified successfully!" -ForegroundColor Green
}

# Clean up verification script
Remove-Item $verificationScriptPath

Write-Host "TA-Lib bootstrap complete!" -ForegroundColor Cyan

# Display usage instructions
Write-Host ""
Write-Host "====================================" -ForegroundColor Cyan
Write-Host "TA-Lib Usage Instructions:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Activate the conda environment:" -ForegroundColor White
Write-Host "   conda activate talib-env" -ForegroundColor Cyan
Write-Host ""
Write-Host "2. Import in Python:" -ForegroundColor White
Write-Host "   import talib" -ForegroundColor Cyan
Write-Host "   import numpy as np" -ForegroundColor Cyan
Write-Host ""
Write-Host "3. Example usage:" -ForegroundColor White
Write-Host "   close_prices = np.array([44.55, 44.3, 44.36, 43.82, 44.46, 44.49, 44.7])" -ForegroundColor Cyan
Write-Host "   sma = talib.SMA(close_prices, timeperiod=3)" -ForegroundColor Cyan
Write-Host ""
Write-Host "4. List available functions:" -ForegroundColor White
Write-Host "   print(talib.get_functions())" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Installation Notes:" -ForegroundColor Yellow
Write-Host "* For CI environments, make sure TA_LIBRARY_PATH and TA_INCLUDE_PATH are set correctly" -ForegroundColor White
Write-Host "* If you still face issues, try using specific wheels for your Python version" -ForegroundColor White
Write-Host "====================================" -ForegroundColor Cyan 