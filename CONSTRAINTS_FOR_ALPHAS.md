# ⚡ INSTANT DISQUALIFICATION TRAPS - QUICK REFERENCE

**Print this. Keep it visible during entire 36 hours.**

---

## 🔴 THE 5 DEADLIEST TRAPS

### TRAP #1: Using High/Low/Open Data
```
❌ WILL GET YOU DQ'D
df['high'] > threshold
ta.atr(df['high'], df['low'], df['close'])
df['open'] + df['close'] / 2

✅ COMPLIANT
df['close'] > threshold
rolling_std(df['close'])  # For volatility
df['close'].shift(1)
```
**Check:** Grep your entire codebase for 'high', 'low', 'open' before submission

---

### TRAP #2: Using Non-FYERS Data
```
❌ WILL GET YOU DQ'D
data = yf.download('RELIANCE.NS', '2025-01-01', '2025-12-31')
data = pd.read_csv('my_downloaded_data.csv')
data = algo.get_historical_data()

✅ COMPLIANT
fyers.historydatasymbol='NSE:RELIANCE-EQ', resolution='1', rangefrom=..., rangeto=...
```
**Verify:** All data must come from `fyers-apiv3` library, no exceptions

---

### TRAP #3: Below Minimum Trade Count
```
❌ WILL GET YOU DQ'D / REJECTED
1H Strategy with only 80 trades (minimum is 120)
5-min Strategy with only 150 trades (minimum is 200)

✅ COMPLIANT
1H Strategy with 267 trades (120+ ✓)
5-min Strategy with 312 trades (200+ ✓)

SOLUTION IF BELOW:
Lower RSI threshold: 10 → 15 (more entry signals)
Reduce holding period (sell faster, re-enter faster)
```

---

### TRAP #4: Forgotten Transaction Costs
```
❌ WILL GET YOU DQ'D (Backtest Shows False Profits)
PnL = sell_price - entry_price  # MISSING COSTS!
equity_curve = cumsum(PnL)

✅ COMPLIANT
PnL = (sell_price - entry_price) - 48  # Entry (24) + Exit (24)
equity_curve = cumsum(PnL)

VERIFY: Buy ₹1000 (cost ₹24) → Sell ₹1010 (cost ₹24)
Gross = ₹1010 - ₹1000 = ₹10
Net = ₹10 - ₹48 = -₹38 (LOSS despite selling higher)
```

---

### TRAP #5: Wrong Output Format
```
❌ WILL GET YOU DQ'D
Your format:
date, price, signal

✓ SAMPLE FORMAT (GET FROM ORGANIZER):
trade_id, symbol, entry_datetime, entry_price, exit_datetime, exit_price, pnl, ...

ACTION: Ask organizer for sample output template by H3
```

---

## 🎯 SACRED 5: VERIFY THESE EVERY HOUR

| # | Check | Status | How |
|---|-------|--------|-----|
| 1 | NO High/Low/Open | ✓ | Grep search: `grep -i 'high\|low\|open' *.py` |
| 2 | FYERS Data Only | ✓ | Source code shows `fyers.historydataXXX()` |
| 3 | Backtest Jan 1 - Dec 31, 2025 | ✓ | Print `df.index.min()` and `df.index.max()` |
| 4 | Capital ₹1,00,000 | ✓ | `INITIAL_CAPITAL = 100000` in code |
| 5 | Costs = ₹48 per trade | ✓ | Verify: `sample_pnl = 50 - 48 = 2` in backtest |

---

## ⏰ SUBMISSION DAY FINAL AUDIT (2 HOURS BEFORE SUBMISSION)

```
RUN THIS SCRIPT:
```python
# PASTE INTO TERMINAL / JUPYTER

# 1. Column Check
import pandas as pd
df = pd.read_csv('backtest_data.csv')
dangerous = [col for col in df.columns if col.lower() in ['high', 'low', 'open']]
if dangerous:
    print("🔴 DANGER: Contains", dangerous)
else:
    print("✅ SAFE: No OHLC columns detected")

# 2. Trade Count
trades_log = pd.read_csv('trades_log.csv')
print(f"Total trades: {len(trades_log)}")
print(f"Minimum required (1H): 120")
if len(trades_log) >= 120:
    print("✅ MEETS MINIMUM")
else:
    print("🔴 BELOW MINIMUM - ADJUST PARAMETERS")

# 3. Cost Check
sample_entry = 1000
sample_exit = 1010
gross = sample_exit - sample_entry  # 10
cost = 24 + 24  # 48
net = gross - cost  # -38
print(f"Sample trade: Entry ₹{sample_entry} → Exit ₹{sample_exit}")
print(f"Gross: ₹{gross}, Costs: ₹{cost}, Net: ₹{net}")
print("Expected: Trade goes from +₹10 to -₹38 after costs")
# Verify backtest shows same logic

# 4. Backtest Window
print(f"Data range: {df['timestamp'].min()} to {df['timestamp'].max()}")
assert str(df['timestamp'].min()).startswith('2025-01-01')
assert str(df['timestamp'].max()).startswith('2025-12-31')
print("✅ Backtest window correct")

# 5. Manual Trade Audit
# Pick trade #1 from backtest log
trade = trades_log.iloc[0]
print(f"\nTrade #1 Audit:")
print(f"Entry: {trade['entry_time']}, Price: {trade['entry_price']}")
print(f"Exit: {trade['exit_time']}, Price: {trade['exit_price']}")
print(f"→ Go to FYERS chart, find that candle, verify price matches ✓")
```

---

## 📞 IF YOU FAIL A CHECK

| Issue | Fix | Timeline |
|-------|-----|----------|
| High/Low/Open found | Remove immediately, use Close only | 5 min |
| Below min trades | Lower entry thresholds (RSI 10→15) | 30 min |
| Costs not applied | Add `pnl = pnl - 48` everywhere | 15 min |
| Wrong backtest window | Verify data range, re-download if needed | 20 min |
| No output format template | Call +91-9149174349 NOW | URGENT |

---

## 💾 SUBMISSION CHECKLIST (FINAL)

Before hitting SUBMIT:

- [ ] ✓ Grepped entire codebase for 'high', 'low', 'open' → Found ZERO
- [ ] ✓ All data from FYERS API
- [ ] ✓ All strategies have trade count >= minimum for timeframe
- [ ] ✓ Costs correctly modeled (verify on sample trade)
- [ ] ✓ Backtest period: Jan 1 - Dec 31, 2025
- [ ] ✓ Initial capital: ₹1,00,000
- [ ] ✓ All 5 symbols tested (NIFTY50, RELIANCE, VBL, YESBANK, SUNPHARMA)
- [ ] ✓ Output format matches sample template
- [ ] ✓ README + methodology document included
- [ ] ✓ Manually verified 5 trades against FYERS charts
- [ ] ✓ No extreme outliers in returns
- [ ] ✓ Submitted BEFORE 9:00 PM deadline

---

**ONE RULE VIOLATION = INSTANT DISQUALIFICATION**  
**Rule #12 (High/Low/Open) kills 70% of participants**  
**You are NOT allowed a "close enough" submission**

🚀 Execute perfectly.
