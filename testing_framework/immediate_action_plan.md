# 🚨 IMMEDIATE ACTION PLAN
## Critical Decision Framework (Countdown: 2h 30m)

**Status:** RED ALERT (Decision Required)  
**Time:** 6:28 PM IST  

---

## 🚦 DECISION MATRIX

### 1. SUBMIT NOW (The "Hail Mary")
**Use if:** You are exhausted and unwilling to touch code again.
**Risk:** High probability of latent bugs found by judges.
**Reward:** It's done.

### 2. QUICK TEST (The "Prudent Path")
**Use if:** You have 30 mins energy left.
**Steps:**
1. Run `python run_comprehensive_tests.py`
2. Check `output/COMPREHENSIVE_TESTING_RESULTS.md`
3. If Test 1 (Overfitting) passes: **SUBMIT**
4. If Test 6 (Overflows) fails: **FIX** then Submit

### 3. AGGRESSIVE FIX (The "Perfectionist")
**Use if:** You assume bugs exist and want 1st place.
**Steps:**
1. Run full suite.
2. Manually inspect every outlier trade.
3. Re-optimize parameters if needed.
4. Submit at 8:30 PM.

---

## 🛠️ COMMON BUG FIXES

### Bug 1: Capital Overflow (e+35 return)
**Symptom:** Return % is astronomical.
**Fix:**
```python
# In strategies/base_strategy.py
def _calculate_metrics(self):
    # Use simple return (sum of PnL / Initial Capital)
    # Instead of Compounding
    total_pnl = sum(t['pnl'] for t in trades)
    return_pct = (total_pnl / self.initial_capital) * 100
```

### Bug 2: Overfitting (Train >> Test)
**Symptom:** Train Sharpe 3.0, Test Sharpe 0.5.
**Fix:**
- Reduce `rsi_entry` optimization specificity.
- Remove `allowed_hours` filter if too specific.
- Switch to `RegimeSwitchingStrategy` (more robust).

---

## ✅ SUBMISSION CHECKLIST (The "Go" Signal)

- [ ] **Strategy Number:** 4 in all files?
- [ ] **Roll Number:** 23ME3EP03 in all files?
- [ ] **Sharpe:** > 1.5 in OOS Test?
- [ ] **Trades:** > 120 per symbol?
- [ ] **Files:** 5 CSVs + 1 Logic Doc?

**If all YES -> UPLOAD.**
