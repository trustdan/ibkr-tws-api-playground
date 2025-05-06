#!/usr/bin/env pwsh
# Windows-specific TA-Lib installation fix
# This script fixes TA-Lib installation issues on Windows by forcing the use of pre-built binaries

# Stop on errors
$ErrorActionPreference = "Stop"

Write-Host "Windows TA-Lib Installation Fix Script" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Green

# Ensure conda is initialized
if (Get-Command conda -ErrorAction SilentlyContinue) {
    Write-Host "Conda detected, proceeding with fix..." -ForegroundColor Green
} else {
    Write-Host "Conda not found. Please install Miniconda or Anaconda first." -ForegroundColor Red
    exit 1
}

# Get environment name
$ENV_NAME = if ($env:CONDA_DEFAULT_ENV) { 
    $env:CONDA_DEFAULT_ENV 
} else { 
    "talib-env-ci" 
}

Write-Host "Target conda environment: $ENV_NAME" -ForegroundColor Yellow

# Make sure environment exists
$envExists = conda env list | Select-String -Pattern $ENV_NAME
if (-not $envExists) {
    Write-Host "Creating conda environment: $ENV_NAME with Python 3.10..." -ForegroundColor Yellow
    conda create -y -n $ENV_NAME python=3.10
}

# Activate environment
Write-Host "Activating conda environment..." -ForegroundColor Yellow
conda activate $ENV_NAME

# Configure conda settings
Write-Host "Configuring conda for binary installations..." -ForegroundColor Yellow
conda config --add channels conda-forge
conda config --set channel_priority strict
conda config --set allow_conda_downgrades true

# Ensure Windows treats conda as a binary install source
Write-Host "Installing TA-Lib 0.4.0 from conda-forge as binary package..." -ForegroundColor Green
conda install -y -c conda-forge ta-lib=0.4.0 numpy --no-deps

# If that fails, try alternative approaches
if ($LASTEXITCODE -ne 0) {
    Write-Host "First attempt failed. Trying alternative TA-Lib version..." -ForegroundColor Yellow
    conda install -y -c conda-forge ta-lib=0.4.19 numpy --no-deps
    
    # If still failing, try installing from wheel
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Conda installation failed. Trying wheel-based installation..." -ForegroundColor Yellow
        
        # Install numpy first
        pip install numpy
        
        # Get Python version for wheel URL
        $PY_VER = python -c "import sys; print(f'{sys.version_info.major}{sys.version_info.minor}')"
        
        # Try to download and install wheel
        $WHEEL_URL = "https://github.com/conda-forge/ta-lib-feedstock/files/7028548/ta_lib-0.4.24-cp${PY_VER}-cp${PY_VER}-win_amd64.whl"
        Write-Host "Downloading wheel from: $WHEEL_URL" -ForegroundColor Yellow
        pip install --no-cache-dir $WHEEL_URL
    }
}

# Verify installation
Write-Host "Verifying TA-Lib installation..." -ForegroundColor Green
python -c "import numpy as np; import talib; print(f'TA-Lib version: {talib.__version__}'); print(f'Functions available: {len(talib.get_functions())}')"

if ($LASTEXITCODE -eq 0) {
    Write-Host "TA-Lib installation successful! ✓" -ForegroundColor Green
} else {
    Write-Host "TA-Lib installation verification failed. Please check error messages above." -ForegroundColor Red
}

# Set environment variables for pip installs
$CONDA_PREFIX = if ($env:CONDA_PREFIX) { $env:CONDA_PREFIX } else { (Join-Path (conda info --base) "envs\$ENV_NAME") }
$TA_LIBRARY_PATH = Join-Path $CONDA_PREFIX "Library\lib"
$TA_INCLUDE_PATH = Join-Path $CONDA_PREFIX "Library\include"

$env:TA_LIBRARY_PATH = $TA_LIBRARY_PATH
$env:TA_INCLUDE_PATH = $TA_INCLUDE_PATH

Write-Host "Setting TA_LIBRARY_PATH=$TA_LIBRARY_PATH"
Write-Host "Setting TA_INCLUDE_PATH=$TA_INCLUDE_PATH"

Write-Host "TA-Lib fix script completed!" -ForegroundColor Green 