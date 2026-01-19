# Installation Guide

## Prerequisites

### System Requirements

- **Operating System:** Windows 10/11, macOS 10.15+, or Linux (Ubuntu 20.04+)
- **Python:** 3.10 or higher
- **RAM:** Minimum 8GB (16GB recommended for optimization)
- **Disk Space:** At least 2GB free space
- **CPU:** Multi-core processor recommended for parallel optimization

### Required Software

1. **Python 3.10+**
   - Download from [python.org](https://www.python.org/downloads/)
   - Verify installation: `python --version`

2. **Git**
   - Download from [git-scm.com](https://git-scm.com/)
   - Verify installation: `git --version`

3. **pip** (Python package manager)
   - Usually comes with Python
   - Verify installation: `pip --version`

---

## Installation Methods

### Method 1: Clone from GitHub (Recommended)

```bash
# Clone the repository
git clone https://github.com/Aditya26189/LSTM.git

# Navigate to the project directory
cd LSTM

# Create a virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Method 2: Download ZIP

1. Go to [https://github.com/Aditya26189/LSTM](https://github.com/Aditya26189/LSTM)
2. Click the green "Code" button
3. Select "Download ZIP"
4. Extract the ZIP file
5. Follow steps 3-5 from Method 1

---

## Dependency Installation

### Core Dependencies

The `requirements.txt` file includes:

```txt
# Core scientific computing
numpy>=1.24.0
pandas>=2.0.0
scipy>=1.10.0

# Visualization
matplotlib>=3.7.0
seaborn>=0.12.0

# Optimization
optuna>=3.0.0

# API (if needed)
fyers-apiv3
requests
```

### Install All Dependencies

```bash
pip install -r requirements.txt
```

### Install Development Dependencies (Optional)

For development and testing:

```bash
# Testing
pip install pytest pytest-cov

# Code quality
pip install flake8 black isort

# Documentation
pip install sphinx sphinx-rtd-theme
```

---

## Configuration

### 1. Environment Variables

Create a `.env` file in the project root:

```bash
# .env
STUDENT_ROLL_NUMBER=23ME3EP03
DATA_DIR=data/raw
OUTPUT_DIR=output
```

### 2. Data Setup

```bash
# Create necessary directories
mkdir -p data/raw
mkdir -p output
mkdir -p optimization_results
mkdir -p reports
```

### 3. Download Market Data

Place your market data CSV files in `data/raw/`:

```
data/raw/
├── NSE_NIFTY50_INDEX_1hour.csv
├── NSE_RELIANCE_EQ_1hour.csv
├── NSE_SUNPHARMA_EQ_1hour.csv
├── NSE_VBL_EQ_1hour.csv
└── NSE_YESBANK_EQ_1hour.csv
```

**Data Format:**
```csv
date,close,volume
2020-01-01 09:00:00,100.50,1000000
2020-01-01 10:00:00,101.25,1200000
...
```

---

## Verification

### 1. Test Installation

```python
# test_installation.py
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats

print("✓ NumPy version:", np.__version__)
print("✓ Pandas version:", pd.__version__)
print("✓ Matplotlib version:", plt.matplotlib.__version__)
print("✓ All core packages installed successfully!")
```

Run the test:
```bash
python test_installation.py
```

### 2. Test Strategy Import

```python
# test_strategy.py
from src.strategies.hybrid_adaptive_v2 import HybridAdaptiveV2
from src.utils.data_loader import load_market_data

print("✓ Strategy modules imported successfully!")
```

### 3. Quick Smoke Test

```python
# smoke_test.py
import pandas as pd
from src.strategies.hybrid_adaptive_v2 import HybridAdaptiveV2

# Create sample data
data = pd.DataFrame({
    'date': pd.date_range('2020-01-01', periods=100, freq='H'),
    'close': [100 + i * 0.1 for i in range(100)],
    'volume': [1000000] * 100
})

# Initialize strategy
strategy = HybridAdaptiveV2(params={'rsi_period': 2})

# Run quick test
try:
    trades, metrics = strategy.backtest(data)
    print("✓ Smoke test passed!")
    print(f"  Generated {len(trades)} trades")
except Exception as e:
    print(f"✗ Smoke test failed: {e}")
```

---

## Troubleshooting

### Common Issues

#### 1. Python Version Error

**Problem:** `Python 3.10+ required`

**Solution:**
```bash
# Check Python version
python --version

# If version is lower, install Python 3.10+
# Download from python.org
```

#### 2. Module Not Found Error

**Problem:** `ModuleNotFoundError: No module named 'pandas'`

**Solution:**
```bash
# Ensure virtual environment is activated
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Reinstall dependencies
pip install -r requirements.txt
```

#### 3. Permission Denied Error

**Problem:** `Permission denied` when creating directories

**Solution:**
```bash
# On Linux/Mac, use sudo
sudo mkdir -p data/raw

# Or change ownership
sudo chown -R $USER:$USER /path/to/LSTM
```

#### 4. Git Clone Fails

**Problem:** `fatal: repository not found`

**Solution:**
```bash
# Use HTTPS instead of SSH
git clone https://github.com/Aditya26189/LSTM.git
```

#### 5. Import Errors

**Problem:** `ImportError: cannot import name 'HybridAdaptiveV2'`

**Solution:**
```bash
# Add project root to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:/path/to/LSTM"

# On Windows:
set PYTHONPATH=%PYTHONPATH%;C:\path\to\LSTM
```

---

## Platform-Specific Notes

### Windows

```powershell
# Use PowerShell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### macOS

```bash
# Install Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python 3.10
brew install python@3.10

# Follow standard installation
```

### Linux (Ubuntu/Debian)

```bash
# Install Python 3.10
sudo apt update
sudo apt install python3.10 python3.10-venv python3-pip

# Follow standard installation
```

---

## IDE Setup

### VS Code

1. Install Python extension
2. Open project folder
3. Select Python interpreter: `Ctrl+Shift+P` → "Python: Select Interpreter"
4. Choose the virtual environment (`./venv/bin/python`)

**Recommended Extensions:**
- Python (Microsoft)
- Pylance
- Python Test Explorer
- autoDocstring

### PyCharm

1. Open project
2. File → Settings → Project → Python Interpreter
3. Click gear icon → Add
4. Select "Existing environment"
5. Choose `venv/bin/python`

---

## Docker Setup (Optional)

### Dockerfile

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "generate_final_submission_files.py"]
```

### Build and Run

```bash
# Build image
docker build -t lstm-trading .

# Run container
docker run -v $(pwd)/data:/app/data -v $(pwd)/output:/app/output lstm-trading
```

---

## Next Steps

After successful installation:

1. **Read the [User Guide](USER_GUIDE.md)** - Learn how to use the framework
2. **Explore [Examples](../examples/)** - See sample implementations
3. **Run a [Quick Test](../README.md#quick-start)** - Verify everything works
4. **Check [API Reference](API_REFERENCE.md)** - Understand the API

---

## Getting Help

If you encounter issues:

1. Check [Troubleshooting](#troubleshooting) section above
2. Search [GitHub Issues](https://github.com/Aditya26189/LSTM/issues)
3. Open a new issue with:
   - OS and Python version
   - Error message and stack trace
   - Steps to reproduce

---

## Updating

### Update to Latest Version

```bash
# Navigate to project directory
cd LSTM

# Pull latest changes
git pull origin main

# Update dependencies
pip install -r requirements.txt --upgrade
```

---

*Last Updated: January 19, 2026*
