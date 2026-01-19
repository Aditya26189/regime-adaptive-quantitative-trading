# CLAUDE AI TESTING FRAMEWORK
## IIT Kharagpur Quant Games 2026 - Aditya Singh Submission

**CRITICAL TASK:** Run comprehensive overfitting, robustness, and stress testing on trading strategy  
**DEADLINE:** Generate complete report by 7:00 PM IST (32 minutes)  
**SUBMISSION DEADLINE:** 9:00 PM IST (92 minutes)

---

## EXECUTIVE BRIEF

**Current Submission Status:**
- Portfolio Sharpe: 2.559
- Total Trades: 757
- Submission Status: PENDING VALIDATION

**Critical Questions to Answer:**
1. Is the 2.559 Sharpe real or overfitted?
2. How stable are the parameters across different time periods?
3. What's the realistic out-of-sample (OOS) performance?
4. Are there bugs in the backtest code causing false results?

---

## YOUR MISSION

Execute 7 comprehensive tests on the trading strategy and generate a detailed validation report.

### Test 1: Train/Test Split Validation
### Test 2: Rolling Window Walk-Forward Analysis
### Test 3: Parameter Stability Analysis
### Test 4: Sensitivity/Stress Testing
### Test 5: Monte Carlo Simulation
### Test 6: Regime-Based Performance
### Test 7: Code Quality & Bug Detection

---

## DETAILED TEST SPECIFICATIONS

### TEST 1: TRAIN/TEST SPLIT VALIDATION

**Objective:** Detect overfitting by comparing in-sample vs out-of-sample performance

**Methodology:**
- Split 2025 data into:
  - TRAIN: Jan 1 - Sep 30 (9 months)
  - TEST: Oct 1 - Dec 31 (3 months)
- Use SAME parameters for both periods
- Compare Sharpe ratios
- Calculate degradation percentage

**Success Criteria:**
- Degradation < 15%: ✅ Excellent
- Degradation 15-30%: ⚠️ Acceptable
- Degradation 30-50%: ⚠️ Concerning
- Degradation > 50%: 🚨 Severe overfitting

**Expected Output:**
```
Symbol          Train Sharpe  Test Sharpe  Degradation  Status
NIFTY50         1.667         X.XXX        Y%           ?
RELIANCE        2.985         X.XXX        Y%           ?
VBL             2.092         X.XXX        Y%           ?
YESBANK         1.759         X.XXX        Y%           ?
SUNPHARMA       4.292         X.XXX        Y%           ?
─────────────────────────────────────────────────────
Portfolio       2.559         X.XXX        Y%           ?
```

**Aditya's Current Parameters:**
```
- RSI period: 2
- RSI entry: 30
- RSI exit: 70
- Hold bars: 10
- Vol min: 0.5%
- KER period: 10
- KER threshold meanrev: 0.30
- KER threshold trend: 0.50
- EMA fast: 8
- EMA slow: 21
- Trend pulse mult: 0.4
```

---

### TEST 2: ROLLING WINDOW WALK-FORWARD ANALYSIS

**Objective:** Simulate realistic trading by testing parameters on progressively newer data

**Methodology:**
- Use 3-month rolling windows
- Window 1: Jan-Mar (train) → Apr-Jun (test)
- Window 2: Apr-Jun (train) → Jul-Sep (test)
- Window 3: Jul-Sep (train) → Oct-Dec (test)
- Calculate Sharpe for each window
- Plot rolling performance

**Success Criteria:**
- All windows > 1.5 Sharpe: ✅ Robust
- All windows > 1.0 Sharpe: ⚠️ Acceptable
- Any window < 1.0: 🚨 Strategy failing

**Expected Output:**
```
Window  Period              Train Sharpe  Test Sharpe  Status
1       Jan-Mar / Apr-Jun   X.XXX         X.XXX        ✅/⚠️/🚨
2       Apr-Jun / Jul-Sep   X.XXX         X.XXX        ✅/⚠️/🚨
3       Jul-Sep / Oct-Dec   X.XXX         X.XXX        ✅/⚠️/🚨
─────────────────────────────────────────────────────
Average                     X.XXX         X.XXX        ?
Std Dev                     X.XXX         X.XXX        ?
Min                         X.XXX         X.XXX        ?
```

---

### TEST 3: PARAMETER STABILITY ANALYSIS

**Objective:** Test if small parameter changes drastically affect performance

**Methodology:**
For each symbol, test:
- RSI entry: 28, 29, 30, 31, 32 (±2 from current 30)
- RSI exit: 68, 69, 70, 71, 72 (±2 from current 70)
- Hold bars: 8, 9, 10, 11, 12 (±2 from current 10)

Calculate Sharpe for each combination.

**Success Criteria:**
- Sharpe changes <10% for ±2 change: ✅ Stable
- Sharpe changes 10-20%: ⚠️ Moderate sensitivity
- Sharpe changes >20%: 🚨 Unstable (overfitted)

**Expected Output (for SUNPHARMA):**
```
RSI Entry  Sharpe   Change%
28         4.100    -4.5%
29         4.180    -2.6%
30         4.292    0.0% (baseline)
31         4.210    -1.9%
32         4.050    -5.6%

Sensitivity: Relatively stable (-5.6% to +0%)

─────

RSI Exit   Sharpe   Change%
68         4.150    -3.3%
69         4.220    -1.7%
70         4.292    0.0% (baseline)
71         4.180    -2.6%
72         4.020    -6.3%

Sensitivity: Relatively stable (-6.3% to +0%)
```

**Red Flag:** If SUNPHARMA Sharpe is 4.292 but drops to 2.0 with RSI 32 → OVERFITTED

---

### TEST 4: SENSITIVITY/STRESS TESTING

**Objective:** Test strategy robustness under extreme market conditions

**Methodology:**
- High volatility period (Oct-Dec, after Diwali)
- Low volatility period (Feb-Mar)
- Trending period (strong directional bias)
- Mean-reverting period (no clear trend)

Calculate Sharpe for each regime.

**Success Criteria:**
- Positive Sharpe in all regimes: ✅ Robust
- Positive Sharpe in 3/4 regimes: ⚠️ Acceptable
- Positive Sharpe in <3/4 regimes: 🚨 Fragile

**Expected Output:**
```
Regime              Dates           Sharpe  Win%   Trades  Status
High Volatility     Oct-Dec 2025    X.XXX   Y%     Z       ✅/⚠️/🚨
Low Volatility      Feb-Mar 2025    X.XXX   Y%     Z       ✅/⚠️/🚨
Strong Trend        Jul-Sep 2025    X.XXX   Y%     Z       ✅/⚠️/🚨
Mean Reverting      Apr-Jun 2025    X.XXX   Y%     Z       ✅/⚠️/🚨
────────────────────────────────────────────────────────────
Average             Full 2025       X.XXX   Y%     Z       ?
```

---

### TEST 5: MONTE CARLO SIMULATION

**Objective:** Test strategy on randomly shuffled historical returns

**Methodology:**
- Extract actual trades from backtest
- Randomly reshuffle order of trades 1000 times
- Calculate Sharpe for each shuffle
- Create distribution of outcomes

**Success Criteria:**
- 90%+ of shuffled runs > 1.5 Sharpe: ✅ Strategy not lucky
- 70-90% of shuffled runs > 1.5 Sharpe: ⚠️ Some luck involved
- <70% of shuffled runs > 1.5 Sharpe: 🚨 Strategy is lucky

**Expected Output:**
```
Monte Carlo Results (1000 simulations):
Mean Sharpe:        X.XXX
Median Sharpe:      X.XXX
Std Dev:            X.XXX
Min Sharpe:         X.XXX
Max Sharpe:         X.XXX
% > 1.5 Sharpe:     Y%

Interpretation: 
- If 90%+ > 1.5: ✅ Strategy skill is real
- If 70-90%: ⚠️ Some edge exists but luck involved
- If <70%: 🚨 Mostly luck
```

---

### TEST 6: REGIME-BASED PERFORMANCE BREAKDOWN

**Objective:** Understand which market conditions strategy thrives in

**Methodology:**
- Calculate daily returns
- Sort into quantiles by:
  - Daily volatility (high/medium/low vol days)
  - Price movement (trending/mean-reverting)
  - Time of day (morning/midday/afternoon)
- Calculate Sharpe for each regime

**Success Criteria:**
- Consistent performance across regimes: ✅ Robust
- Performs well in 2-3 regimes: ⚠️ Niche strategy
- Performs well in only 1 regime: 🚨 Curve-fitted to that regime

**Expected Output:**
```
Volatility Regime
─────────────────
High Vol Days     Sharpe: X.XXX   Trades: Z   Win%: Y%
Medium Vol Days   Sharpe: X.XXX   Trades: Z   Win%: Y%
Low Vol Days      Sharpe: X.XXX   Trades: Z   Win%: Y%

Directional Regime
──────────────────
Trending Days     Sharpe: X.XXX   Trades: Z   Win%: Y%
Mean-Rev Days     Sharpe: X.XXX   Trades: Z   Win%: Y%

Time-of-Day Regime
──────────────────
Morning (9-11)    Sharpe: X.XXX   Trades: Z   Win%: Y%
Midday (11-14)    Sharpe: X.XXX   Trades: Z   Win%: Y%
Afternoon (14-15) Sharpe: X.XXX   Trades: Z   Win%: Y%
```

---

### TEST 7: CODE QUALITY & BUG DETECTION

**Objective:** Identify bugs causing false results (like overflow)

**Methodology:**
- Check for capital compounding errors
- Verify position sizing calculations
- Validate transaction cost implementation
- Check for data leakage
- Verify Rule 12 compliance (only close prices)

**Checks:**
```
✓ Capital calculation: final = initial + sum(pnl) - costs
  (NOT: final = initial * (1 + r1) * (1 + r2)...)

✓ Position sizing: qty = capital * frac / close_price
  (NOT: qty = previous_qty * multiplier)

✓ Transaction costs: ₹48 per round-trip
  (NOT: ₹24 or forgotten)

✓ Data leakage: Only using close prices, not future data
  (NOT: Using tomorrow's close to decide today)

✓ Overflow check: Returns < 1000% per trade (sanity check)
  (NOT: Returns like 3.52e+35)

✓ Rule 12: No high/low/open usage
  GREP: grep -r "high\|low\|open" strategies/
```

**Red Flags to Check:**
- "VBL return: 2.17e+65%" → 🚨 OVERFLOW BUG
- "NIFTY50 return: 3.52e+35%" → 🚨 OVERFLOW BUG
- SUNPHARMA 4.292 with overflow → 🚨 FALSE RESULT

**Expected Output:**
```
Code Quality Audit
──────────────────
Capital Calculation:    ✅ CORRECT / ⚠️ WARNING / 🚨 BUG
Position Sizing:        ✅ CORRECT / ⚠️ WARNING / 🚨 BUG
Transaction Costs:      ✅ CORRECT / ⚠️ WARNING / 🚨 BUG
Data Leakage Check:     ✅ CORRECT / ⚠️ WARNING / 🚨 BUG
Overflow Check:         ✅ CORRECT / ⚠️ WARNING / 🚨 BUG
Rule 12 Compliance:     ✅ CORRECT / ⚠️ WARNING / 🚨 BUG

Overall Code Quality: EXCELLENT / ACCEPTABLE / CONCERNING / BROKEN
```

---

## REPORT GENERATION REQUIREMENTS

After running all 7 tests, generate a comprehensive document:

### Report Structure:

```
1. EXECUTIVE SUMMARY
   - Overall assessment: Safe to submit / Risk / Do not submit
   - Realistic portfolio Sharpe estimate
   - Key findings summary

2. TEST RESULTS (Detailed)
   - Test 1-7 full results
   - Tables and statistics
   - Interpretation for each test

3. OVERFITTING ASSESSMENT
   - Confidence in 2.559 Sharpe (High/Medium/Low)
   - Expected real-world Sharpe
   - Risk factors

4. ROBUSTNESS ANALYSIS
   - Parameter sensitivity summary
   - Regime performance breakdown
   - Monte Carlo findings

5. CODE QUALITY AUDIT
   - Bugs found (if any)
   - Fixes recommended
   - Overall code health

6. SUBMISSION RECOMMENDATIONS
   - Proceed with current submission? YES/NO
   - Alternative strategies if needed
   - Expected competition ranking

7. APPENDIX
   - All detailed tables
   - Visualizations (text-based)
   - Raw test output
```

---

## SPECIFIC INSTRUCTIONS FOR EACH TEST

### Running Test 1: Train/Test Split

```python
# PSEUDO-CODE
for symbol in ['NIFTY50', 'RELIANCE', 'VBL', 'YESBANK', 'SUNPHARMA']:
    # Load 2025 data
    df = load_data(symbol)
    
    # Split
    train = df[df.date < '2025-10-01']
    test = df[df.date >= '2025-10-01']
    
    # Backtest with SAME parameters
    train_trades = backtest(train, params)
    test_trades = backtest(test, params)
    
    # Compare
    train_sharpe = calculate_sharpe(train_trades)
    test_sharpe = calculate_sharpe(test_trades)
    degradation = (train_sharpe - test_sharpe) / train_sharpe * 100
    
    # Report
    print(f"{symbol}: Train {train_sharpe:.3f} → Test {test_sharpe:.3f} ({degradation:+.1f}%)")
```

### Running Test 2: Rolling Window

```python
# PSEUDO-CODE
windows = [
    ('2025-01-01', '2025-03-31', '2025-04-01', '2025-06-30'),  # Q1/Q2
    ('2025-04-01', '2025-06-30', '2025-07-01', '2025-09-30'),  # Q2/Q3
    ('2025-07-01', '2025-09-30', '2025-10-01', '2025-12-31'),  # Q3/Q4
]

for train_start, train_end, test_start, test_end in windows:
    train = df[(df.date >= train_start) & (df.date <= train_end)]
    test = df[(df.date >= test_start) & (df.date <= test_end)]
    
    train_sharpe = backtest(train, params).sharpe
    test_sharpe = backtest(test, params).sharpe
    
    print(f"Window: {train_sharpe:.3f} → {test_sharpe:.3f}")
```

### Running Test 3: Parameter Sensitivity

```python
# PSEUDO-CODE
for rsi_entry in [28, 29, 30, 31, 32]:
    for rsi_exit in [68, 69, 70, 71, 72]:
        params['rsi_entry'] = rsi_entry
        params['rsi_exit'] = rsi_exit
        
        trades = backtest(df, params)
        sharpe = calculate_sharpe(trades)
        
        print(f"RSI {rsi_entry}/{rsi_exit}: Sharpe {sharpe:.3f}")
```

---

## CRITICAL QUESTIONS TO ANSWER IN REPORT

1. **Is 2.559 Sharpe realistic?**
   - YES: Train/test degradation < 20% AND no obvious bugs
   - NO: Train/test degradation > 40% OR overflow detected

2. **What's the expected real-world Sharpe?**
   - Conservative estimate: Test Sharpe from Test 1
   - If Test 1 shows degradation, multiply by (1 - degradation%)

3. **Should Aditya submit this?**
   - If realistic Sharpe ≥ 1.8: ✅ YES
   - If realistic Sharpe 1.5-1.8: ⚠️ YES (as backup)
   - If realistic Sharpe < 1.5: 🚨 NO (fix first)

4. **What's the expected competition rank?**
   - Sharpe 2.5+: Top 1-3
   - Sharpe 2.0-2.5: Top 1-5
   - Sharpe 1.8-2.0: Top 5-10
   - Sharpe 1.5-1.8: Top 10-20
   - Sharpe < 1.5: Top 20+

5. **What bugs did you find?**
   - Document each bug
   - Recommend fixes
   - Estimate impact on Sharpe

---

## FORMATTING REQUIREMENTS

Generate report as:
- **Format:** Markdown (.md)
- **Title:** `COMPREHENSIVE_TESTING_RESULTS.md`
- **Length:** 3000-5000 words
- **Tables:** Use markdown tables with ✅/⚠️/🚨 indicators
- **Colors:** Use emoji for visual hierarchy
- **Sections:** Clear H2/H3 headings
- **Data:** Include all raw numbers
- **Conclusion:** Clear recommendation at end

---

## TIMELINE

- **6:28 PM:** Start testing (current time)
- **6:43 PM:** Complete Tests 1-3 (15 min)
- **6:53 PM:** Complete Tests 4-5 (10 min)
- **7:00 PM:** Complete Tests 6-7 + draft report (7 min)
- **7:05 PM:** Finalize and polish report (5 min)
- **7:10 PM:** DONE - Submit to Aditya

**Total time budget: 42 minutes**

---

## SUCCESS CRITERIA FOR THIS PROMPT

✅ All 7 tests executed with quantitative results  
✅ Clear overfitting assessment (YES/NO/MAYBE)  
✅ Realistic Sharpe estimate provided  
✅ Concrete submission recommendation (SUBMIT/FIX/BACKUP)  
✅ Competitive ranking estimate given  
✅ All bugs identified and documented  
✅ Professional report generated  

---

## WHAT HAPPENS AFTER REPORT

**If Report Says "SUBMIT":**
→ Aditya submits immediately with confidence

**If Report Says "FIX FIRST":**
→ Switch to conservative parameters
→ Rerun backtest
→ Submit as backup

**If Report Says "DO NOT SUBMIT":**
→ Emergency rework needed
→ Use 2nd submission slot for fixed version

---

## TONE & DELIVERY

- **Be brutally honest:** Don't sugarcoat bad news
- **Be specific:** Numbers, not vague statements
- **Be actionable:** Give concrete next steps
- **Be clear:** Use ✅/⚠️/🚨 to make severity obvious
- **Be thorough:** Leave no questions unanswered

---

## DOCUMENT OUTPUT

Save final report as: `COMPREHENSIVE_TESTING_RESULTS.md`

Include:
1. All test results (tables)
2. Statistical analysis
3. Clear conclusions
4. Specific recommendations
5. Expected outcomes
6. Risk assessment
7. Appendix with raw data

---

**NOW EXECUTE ALL TESTS AND GENERATE REPORT. ADITYA IS WAITING.**

Time is critical. Results needed by 7:05 PM IST.