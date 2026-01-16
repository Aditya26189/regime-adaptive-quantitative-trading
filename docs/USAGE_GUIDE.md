# RSI(2) Strategy - Detailed Usage Guide

This guide provides step-by-step instructions for running the strategy and preparing submissions for the Quant Games Hackathon.

---

## 📋 Table of Contents

1. [Initial Setup](#initial-setup)
2. [Running the Strategy](#running-the-strategy)
3. [Generating Submissions for All Symbols](#generating-submissions-for-all-symbols)
4. [Understanding the Output](#understanding-the-output)
5. [Validation Checklist](#validation-checklist)
6. [Advanced Usage](#advanced-usage)

---

## 🔧 Initial Setup

### Step 1: Verify Environment

```powershell
# Navigate to project directory
cd C:\Users\LawLight\OneDrive\Desktop\fyers

# Activate virtual environment
.\venv\Scripts\activate

# Verify Python version (should be 3.8+)
python --version

# Verify required packages
pip list | findstr "pandas numpy"
```

### Step 2: Configure Your Roll Number

**Edit `strategy1_rsi2_meanrev.py`** (Line ~230):

```python
class Config:
    STUDENT_ROLL_NUMBER = "21CS10XXX"  # ← Replace with YOUR roll number
    STRATEGY_SUBMISSION_NUMBER = 1
    SYMBOL = "NSE:NIFTY50-INDEX"
    TIMEFRAME = "60"
    DATA_FILE = "fyers_data/NSE_NIFTY50_INDEX_1hour.csv"
    INITIAL_CAPITAL = 100000
    FEE_PER_ORDER = 24
```

### Step 3: Verify Data Files

```powershell
# Check all required data files exist
dir fyers_data\*1hour.csv
```

**Expected output:**
```
NSE_NIFTY50_INDEX_1hour.csv
NSE_RELIANCE_EQ_1hour.csv
NSE_VBL_EQ_1hour.csv
NSE_YESBANK_EQ_1hour.csv
NSE_SUNPHARMA_EQ_1hour.csv
```

---

## 🚀 Running the Strategy

### Single Symbol Backtest

**For NIFTY50:**

```powershell
# Ensure Config is set to NIFTY50 (default)
python strategy1_rsi2_meanrev.py
```

**Expected Terminal Output:**

```
======================================================================
BACKTESTING: NSE:NIFTY50-INDEX @ 60
======================================================================
Loading data...
Data loaded: 1733 bars
Date range: 2025-01-01 09:15:00+05:30 to 2025-12-31 15:15:00+05:30

Generating signals...
Signals generated: 147 BUY, 147 SELL

Running backtest...

STRATEGY PERFORMANCE METRICS
======================================================================
Total Trades:       147
Winning Trades:     XX (XX.X%)
Losing Trades:      XX (XX.X%)

Total Return:       X.X%
Final Capital:      ₹XXX,XXX.XX

Sharpe Ratio:       X.XX
Max Drawdown:       -X.X%
======================================================================

✓ Trade count (147) meets minimum requirement (120)
✓ Positive returns - strategy profitable after costs
✓ Output file created successfully

Output saved: 21CS10XXX_strategy1_NSE_NIFTY50-INDEX_60.csv
======================================================================
```

**Output File Created:**
- `21CS10XXX_strategy1_NSE_NIFTY50-INDEX_60.csv` (147 trades)

---

## 📊 Generating Submissions for All Symbols

### Method 1: Manual (Recommended for Understanding)

Run the strategy for each symbol by editing `Config`:

**1. NIFTY50** (already done above)

**2. RELIANCE:**
```python
# Edit strategy1_rsi2_meanrev.py
SYMBOL = "NSE:RELIANCE-EQ"
DATA_FILE = "fyers_data/NSE_RELIANCE_EQ_1hour.csv"
```
```powershell
python strategy1_rsi2_meanrev.py
```

**3. VBL:**
```python
SYMBOL = "NSE:VBL-EQ"
DATA_FILE = "fyers_data/NSE_VBL_EQ_1hour.csv"
```
```powershell
python strategy1_rsi2_meanrev.py
```

**4. YESBANK:**
```python
SYMBOL = "NSE:YESBANK-EQ"
DATA_FILE = "fyers_data/NSE_YESBANK_EQ_1hour.csv"
```
```powershell
python strategy1_rsi2_meanrev.py
```

**5. SUNPHARMA:**
```python
SYMBOL = "NSE:SUNPHARMA-EQ"
DATA_FILE = "fyers_data/NSE_SUNPHARMA_EQ_1hour.csv"
```
```powershell
python strategy1_rsi2_meanrev.py
```

### Method 2: Automated Script

Create `run_all_symbols.py`:

```python
"""Generate submissions for all 5 required symbols."""
import pandas as pd
from strategy1_rsi2_meanrev import generate_signals, BacktestEngine

class Config:
    STUDENT_ROLL_NUMBER = "21CS10XXX"  # ← YOUR ROLL NUMBER
    STRATEGY_SUBMISSION_NUMBER = 1
    INITIAL_CAPITAL = 100000
    FEE_PER_ORDER = 24
    TIMEFRAME = "60"

symbols = [
    ("NSE:NIFTY50-INDEX", "fyers_data/NSE_NIFTY50_INDEX_1hour.csv"),
    ("NSE:RELIANCE-EQ", "fyers_data/NSE_RELIANCE_EQ_1hour.csv"),
    ("NSE:VBL-EQ", "fyers_data/NSE_VBL_EQ_1hour.csv"),
    ("NSE:YESBANK-EQ", "fyers_data/NSE_YESBANK_EQ_1hour.csv"),
    ("NSE:SUNPHARMA-EQ", "fyers_data/NSE_SUNPHARMA_EQ_1hour.csv"),
]

for symbol, data_file in symbols:
    print(f"\n{'='*60}")
    print(f"Processing: {symbol}")
    print('='*60)
    
    # Update config
    Config.SYMBOL = symbol
    Config.DATA_FILE = data_file
    
    # Load and process
    df = pd.read_csv(data_file)
    df_signals = generate_signals(df.copy(), Config)
    
    # Run backtest
    engine = BacktestEngine(Config)
    trades_df = engine.run(df_signals)
    metrics = engine.get_metrics()
    
    # Print summary
    print(f"Trades: {metrics['total_trades']}")
    print(f"Return: {metrics['total_return']}%")
    print(f"Status: {'✓ PASS' if metrics['total_trades'] >= 120 else '✗ FAIL'}")
    
    # Save output
    output_file = f"{Config.STUDENT_ROLL_NUMBER}_strategy{Config.STRATEGY_SUBMISSION_NUMBER}_{symbol.replace(':', '_')}_{Config.TIMEFRAME}.csv"
    trades_df.to_csv(output_file, index=False)
    print(f"Saved: {output_file}")

print("\n" + "="*60)
print("ALL SYMBOLS PROCESSED")
print("="*60)
```

Run:
```powershell
python run_all_symbols.py
```

---

## 📄 Understanding the Output

### Output File Format

Each CSV file contains one row per trade with 11 columns:

**Example Row:**
```csv
21CS10XXX,1,NSE:NIFTY50-INDEX,60,2025-02-07 13:15:00+05:30,2025-02-07 15:15:00+05:30,23461.05,23563.15,4,48,100360.4
```

**Column Breakdown:**

| Position | Column Name | Value | Meaning |
|----------|-------------|-------|---------|
| 1 | student_roll_number | 21CS10XXX | Your roll number |
| 2 | strategy_submission_number | 1 | Strategy version (1-5) |
| 3 | symbol | NSE:NIFTY50-INDEX | Trading symbol |
| 4 | timeframe | 60 | 1 hour = 60 minutes |
| 5 | entry_trade_time | 2025-02-07 13:15:00+05:30 | When entered |
| 6 | exit_trade_time | 2025-02-07 15:15:00+05:30 | When exited |
| 7 | entry_trade_price | 23461.05 | Entry price |
| 8 | exit_trade_price | 23563.15 | Exit price |
| 9 | qty | 4 | Quantity traded |
| 10 | fees | 48 | Total fees (₹24×2) |
| 11 | cumulative_capital_after_trade | 100360.4 | Capital after trade |

### Interpreting Results

**Trade Analysis:**
```python
# Load output file
trades = pd.read_csv('21CS10XXX_strategy1_NSE_NIFTY50-INDEX_60.csv')

# Calculate P&L per trade
trades['pnl'] = (trades['exit_trade_price'] - trades['entry_trade_price']) * trades['qty'] - trades['fees']

# Winners vs Losers
winners = trades[trades['pnl'] > 0]
losers = trades[trades['pnl'] <= 0]

print(f"Winning trades: {len(winners)} ({len(winners)/len(trades)*100:.1f}%)")
print(f"Average win: ₹{winners['pnl'].mean():.2f}")
print(f"Average loss: ₹{losers['pnl'].mean():.2f}")
```

**Capital Curve:**
```python
import matplotlib.pyplot as plt

plt.figure(figsize=(12, 6))
plt.plot(trades['cumulative_capital_after_trade'])
plt.axhline(y=100000, color='r', linestyle='--', label='Initial Capital')
plt.xlabel('Trade Number')
plt.ylabel('Capital (₹)')
plt.title('Equity Curve')
plt.legend()
plt.grid(True)
plt.savefig('equity_curve.png')
```

---

## ✅ Validation Checklist

Before submitting, verify:

### 1. Trade Count Validation

```powershell
python validate_all.py
```

**Must show:**
```
PASS: NIFTY50      - XXX trades  (≥120)
PASS: RELIANCE     - XXX trades  (≥120)
PASS: VBL          - XXX trades  (≥120)
PASS: YESBANK      - XXX trades  (≥120)
PASS: SUNPHARMA    - XXX trades  (≥120)
```

### 2. Output File Validation

```powershell
# Check all 5 files exist
dir *_strategy1_*.csv
```

**Expected:**
```
21CS10XXX_strategy1_NSE_NIFTY50-INDEX_60.csv
21CS10XXX_strategy1_NSE_RELIANCE-EQ_60.csv
21CS10XXX_strategy1_NSE_VBL-EQ_60.csv
21CS10XXX_strategy1_NSE_YESBANK-EQ_60.csv
21CS10XXX_strategy1_NSE_SUNPHARMA-EQ_60.csv
```

### 3. Column Format Validation

```python
import pandas as pd

# Check one file
df = pd.read_csv('21CS10XXX_strategy1_NSE_NIFTY50-INDEX_60.csv')

expected_cols = [
    'student_roll_number', 'strategy_submission_number',
    'symbol', 'timeframe', 'entry_trade_time', 'exit_trade_time',
    'entry_trade_price', 'exit_trade_price', 'qty', 'fees',
    'cumulative_capital_after_trade'
]

assert list(df.columns) == expected_cols, "Column mismatch!"
print("✓ Column format correct")
```

### 4. Fee Validation

```python
# All fees should be ₹48
assert (df['fees'] == 48).all(), "Fee error!"
print("✓ Fees correct (₹48 per trade)")
```

### 5. Timeframe Validation

```python
# All timeframes should be '60'
assert (df['timeframe'] == '60').all(), "Timeframe error!"
print("✓ Timeframe correct (60 minutes)")
```

---

## 🔬 Advanced Usage

### Debugging Signal Generation

```python
from strategy1_rsi2_meanrev import generate_signals
import pandas as pd

# Load data
df = pd.read_csv('fyers_data/NSE_NIFTY50_INDEX_1hour.csv')

# Generate signals with indicators
df_signals = generate_signals(df.copy(), None)

# Inspect signals
buy_signals = df_signals[df_signals['signal'] == 1]
print(f"\nFirst 5 BUY signals:")
print(buy_signals[['datetime', 'close', 'rsi2', 'volatility']].head())

# Check RSI distribution
print(f"\nRSI(2) statistics:")
print(df_signals['rsi2'].describe())

# Check how many times RSI < 25
print(f"\nRSI(2) < 25 count: {(df_signals['rsi2'] < 25).sum()}")
print(f"Actual BUY signals: {(df_signals['signal'] == 1).sum()}")
```

### Analyzing Trade Duration

```python
trades = pd.read_csv('21CS10XXX_strategy1_NSE_NIFTY50-INDEX_60.csv')

# Convert to datetime
trades['entry_time'] = pd.to_datetime(trades['entry_trade_time'])
trades['exit_time'] = pd.to_datetime(trades['exit_trade_time'])

# Calculate duration in hours
trades['duration_hours'] = (trades['exit_time'] - trades['entry_time']).dt.total_seconds() / 3600

print(f"Average hold time: {trades['duration_hours'].mean():.1f} hours")
print(f"Max hold time: {trades['duration_hours'].max():.1f} hours")
print(f"Min hold time: {trades['duration_hours'].min():.1f} hours")
```

### Parameter Sensitivity Analysis

```python
# Test different RSI thresholds
thresholds = [15, 20, 25, 30, 35]

for thresh in thresholds:
    # Modify RSI threshold in generate_signals
    # (You'd need to parameterize this)
    
    df_signals = generate_signals(df.copy(), None)
    buy_count = (df_signals['signal'] == 1).sum()
    
    print(f"RSI < {thresh}: {buy_count} trades")
```

---

## 📤 Submission Preparation

### Final Checklist

- [ ] Roll number updated in all files
- [ ] All 5 symbols processed
- [ ] All files have 120+ trades
- [ ] Column format validated
- [ ] Fees are ₹48 per trade
- [ ] Timeframe is '60' for all
- [ ] Files named correctly: `ROLL_strategy1_SYMBOL_60.csv`

### Submission Files

Submit these 5 CSV files:
1. `21CS10XXX_strategy1_NSE_NIFTY50-INDEX_60.csv`
2. `21CS10XXX_strategy1_NSE_RELIANCE-EQ_60.csv`
3. `21CS10XXX_strategy1_NSE_VBL-EQ_60.csv`
4. `21CS10XXX_strategy1_NSE_YESBANK-EQ_60.csv`
5. `21CS10XXX_strategy1_NSE_SUNPHARMA-EQ_60.csv`

---

## 🆘 Getting Help

If you encounter issues:

1. **Run full test suite:**
   ```powershell
   python test_strategy.py
   ```

2. **Check specific test:**
   ```python
   from test_strategy import test_signal_generation_nifty
   test_signal_generation_nifty()
   ```

3. **Enable debug mode:**
   ```python
   # Add to generate_signals() function
   print(f"Bar {i}: RSI={prev_rsi2:.2f}, Vol={prev_volatility:.4f}")
   ```

---

**Last Updated:** January 16, 2026  
**Version:** 1.0
