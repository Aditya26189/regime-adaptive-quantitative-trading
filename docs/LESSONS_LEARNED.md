# Lessons Learned - Key Takeaways from Quant Games 2026

**Author:** Aditya Singh (Roll: 23ME3EP03)  
**Competition:** IIT Kharagpur Quant Games 2026  
**Final Result:** 2.276 Portfolio Sharpe (Top 3-5)

---

## Introduction

Six weeks of intensive algorithmic trading development taught me invaluable lessons about quantitative finance, software engineering, optimization, and myself. This document captures the key learnings for future reference.

---

## Technical Lessons

### 1. Simplicity Beats Complexity

**What I Learned:**

My winning RSI(2) mean reversion strategy is simpler than 90% of approaches I tried (and abandoned).

**Failed Complex Approaches:**
- Random Forest price prediction (52% accuracy, 0.35 Sharpe)
- LSTM neural networks (didn't converge)
- Complex multi-indicator systems (over-fitted)
- Reinforcement learning DQN (agent learned to do nothing)

**Winning Simple Approach:**
- RSI(2) < 30 → BUY
- RSI(2) > 70 → SELL
- Volatility-adjusted position sizing
- **Result:** 2.276 Sharpe ✅

**Why Simplicity Won:**
- Fewer parameters → less over-fitting risk
- Easier to understand and debug
- More robust to market changes
- Lower computational cost

**Lesson:** Start simple, add complexity only if it significantly improves validated performance.

---

### 2. Fast Indicators > Slow Indicators for Intraday

**Discovery:**

RSI(2) dramatically outperformed RSI(14):

| Indicator | Trades | Sharpe | Win Rate |
|-----------|--------|--------|----------|
| RSI(14) | 89 | 0.65 | 58.4% |
| RSI(2) | 187 | 1.85 | 69.7% |

**Why?**

Intraday mean reversion happens in hours, not days. RSI(14) is too slow to capture these moves before they exhaust.

**Lesson:** Match indicator speed to trading timeframe. For intraday, fast indicators (2-5 periods) work best.

---

### 3. Transaction Costs Can Kill Strategies

**Eye-Opening Experience:**

A high-frequency strategy looked amazing in backtest:
- Sharpe: 2.8
- Trades: 3,500 per symbol
- Win rate: 63%

After adding realistic transaction costs (0.08% per trade):
- Sharpe: 0.15 (terrible!)
- Strategy completely destroyed

**Lesson:** ALWAYS model transaction costs early. Never trust backtest results without costs.

**Formula:**
```
Net Profit = Gross Profit - (Trades × Trade Size × Cost %)
```

For 3,500 trades on ₹15,000 positions at 0.08% cost:
```
Cost = 3,500 × 15,000 × 0.0008 = ₹42,000
```

This wiped out most profits!

---

### 4. Walk-Forward Validation is Non-Negotiable

**Mistake I Made:**

Early in competition, I optimized on full dataset (2024-2026), achieving 3.2 Sharpe. I was thrilled!

Then I ran walk-forward validation:
- Training (2024-Q3 2025): 3.2 Sharpe
- Test (Q4 2025 - Q1 2026): 0.9 Sharpe

**Reality:** Strategy was massively over-fitted.

**Lesson:** Always split data BEFORE optimization. Never touch test set until final validation.

**Proper Workflow:**
1. Split data: 60% train, 20% validation, 20% test
2. Optimize on training ONLY
3. Check validation (if bad, try different approach)
4. Final test on test set (accept results, no re-optimization)

---

### 5. Different Assets Need Different Strategies

**Initial Mistake:**

I tried using the same RSI mean reversion strategy for all 5 symbols. Results were mediocre:

| Symbol | Universal Strategy Sharpe |
|--------|--------------------------|
| NIFTY50 | 0.65 |
| RELIANCE | 1.12 |
| SUNPHARMA | 1.38 |
| VBL | 0.34 |
| YESBANK | 0.21 |

**Portfolio Sharpe:** 0.94 (poor)

**After Symbol-Specific Optimization:**

| Symbol | Tailored Strategy Sharpe |
|--------|-------------------------|
| NIFTY50 | 1.04 (trend-following) |
| RELIANCE | 3.23 (mean reversion boosted) |
| SUNPHARMA | 4.29 (mean reversion boosted) |
| VBL | 0.66 (regime switching) |
| YESBANK | 0.82 (conservative) |

**Portfolio Sharpe:** 2.276 (+142%!)

**Lesson:** Analyze each asset's characteristics (volatility, correlation, trending vs mean-reverting) and tailor strategies accordingly.

---

## Optimization Lessons

### 6. Bayesian Optimization Saves Time

**Experience:**

**Grid Search Approach (abandoned):**
- Parameters: 6 dimensions, 10 values each = 1,000,000 combinations
- Time per trial: 3 seconds
- Total time: 3,000,000 seconds = 833 hours (impractical!)

**Optuna (Bayesian) Approach:**
- Trials: 500 (not 1,000,000!)
- Time: 500 × 3 = 1,500 seconds = 25 minutes
- **Result:** Found near-optimal parameters (2.87 Sharpe)

**How It Works:**

Optuna learns which parameter regions are promising and focuses search there.

**Lesson:** Use Bayesian optimization (Optuna, scikit-optimize) for hyperparameter tuning. Never use exhaustive grid search unless parameter space is tiny (<1,000 combinations).

---

### 7. Parameter Sensitivity Varies Wildly

**Discovery:**

Not all parameters are equally important:

| Parameter | Change | Sharpe Impact |
|-----------|--------|---------------|
| RSI Period | ±1 | ±15% |
| RSI Boost | ±1 | ±8% |
| Position Size | ±0.1 | ±10% |
| Max Hold Time | ±2 hours | ±2% |
| Volatility Window | ±5 periods | ±1% |

**Lesson:** Focus optimization efforts on sensitive parameters (RSI period, boost, position size). Don't waste time fine-tuning insensitive parameters.

---

### 8. Local Optima Are Everywhere

**Problem:**

Optimization can get stuck in local optima:

```
Parameter Set A: Sharpe 2.1 (local optimum)
Parameter Set B: Sharpe 2.9 (global optimum)
```

If optimizer starts near A, it may never find B.

**Solution:**

Run multiple optimization studies with different random seeds:

```python
for seed in range(5):
    study = optuna.create_study(sampler=TPESampler(seed=seed))
    study.optimize(objective, n_trials=200)
    print(f"Seed {seed}: Best Sharpe = {study.best_value}")

# Pick best across all seeds
```

**My Results:**
- Seed 0: 2.67
- Seed 1: 2.89 ← Best
- Seed 2: 2.71
- Seed 3: 2.58
- Seed 4: 2.75

**Lesson:** Run optimization multiple times with different initializations to escape local optima.

---

## Strategy Development Lessons

### 9. Innovation Matters More Than Sophistication

**My Breakthrough:** RSI Boosting

**Idea:** Add 3-4 points to RSI before checking thresholds

```python
rsi_boosted = rsi + 4
entry = rsi_boosted < 30  # Effectively RSI < 26
```

**Impact:** +20-30% Sharpe improvement

**Why It's Innovation:**
- Simple modification (one line of code!)
- Not in academic literature
- Not used by competitors
- Massive performance boost

**Lesson:** Sometimes a small creative insight beats complex algorithms. Don't overlook simple modifications to existing techniques.

---

### 10. Risk Management is Non-Negotiable

**Scenario:**

Without volatility-based position sizing:
- VBL max drawdown: -28.7%
- YESBANK max drawdown: -22.4%
- Portfolio max drawdown: -18.3%

With volatility-based position sizing:
- VBL max drawdown: -13.4%
- YESBANK max drawdown: -10.3%
- Portfolio max drawdown: -8.2%

**Formula:**
```python
position_size = base_size / (1 + 2 * current_volatility)
```

**Lesson:** Risk management isn't optional. Even with perfect entry signals, poor risk management will destroy your account.

---

### 11. Holding Time Matters

**Data Analysis:**

| Hold Time | Count | Win Rate | Avg Return |
|-----------|-------|----------|------------|
| 0-2 hours | 127 | 64% | +0.31% |
| 2-4 hours | 189 | 68% | +0.48% |
| 4-6 hours | 245 | 71% | +0.52% ← Best |
| 6-8 hours | 143 | 69% | +0.39% |
| 8-10 hours | 42 | 62% | +0.21% |
| 10+ hours | 11 | 45% | -0.15% ← Worst |

**Lesson:** Optimal hold time exists. Exiting too early leaves money on table. Holding too long lets profits erode. My optimal: 4-6 hours for mean reversion.

---

## Process Lessons

### 12. Documentation is Crucial

**What I Did:**

Logged every experiment, optimization result, and decision in markdown files.

**Benefits:**
1. Could trace back why I made decisions months later
2. Avoided repeating failed experiments
3. Easy to write final report (just compile notes)
4. Helpful for debugging ("What parameters did I use in version 2.3?")

**Lesson:** Document as you go. Future you will thank present you.

---

### 13. Fail Fast, Fail Often

**Failed Experiments (abandoned quickly):**

1. Machine Learning prediction (2 days, failed)
2. High-frequency mean reversion (1 day, transaction costs killed it)
3. Options hedging (2 days, then realized options not allowed!)
4. News sentiment (3 days, data unavailable)
5. Pair trading (1 day, didn't fit competition rules)
6. Reinforcement Learning (2 days, didn't converge)

**Total time wasted:** 11 days

**If I hadn't abandoned quickly:** Could have been 50+ days

**Lesson:** Validate feasibility early. If approach isn't working after 1-2 days, cut losses and try something else.

---

### 14. Sleep on Big Decisions

**Example:**

January 12: Discovered RSI boosting. Got 4.5 Sharpe on SUNPHARMA. Was so excited I almost submitted immediately.

**What I Did:**

Slept on it. Next morning, ran walk-forward validation. Sharpe dropped to 4.1 (still great!). Found small bug that would have caused submission failure.

**Lesson:** Don't make major decisions (like final submission) when excited. Sleep on it, validate thoroughly next day.

---

## Competition-Specific Lessons

### 15. Read Rules THOROUGHLY

**Mistake:**

Spent 2 days building options hedging strategy. Then read rules carefully: "Only equity intraday trading allowed."

**Lesson:** Read rules multiple times. Highlight key constraints. Check feasibility BEFORE coding.

---

### 16. Minimum Requirements are Traps

**Rule:** Minimum 120 trades per symbol

**My Initial Approach:** Aim for exactly 120 (efficient!)

**Problem:** Some days had no good signals. Final count: 108 trades (failed!)

**Solution:** Target 150+ trades, buffer protects against unlucky periods.

**Lesson:** Always exceed minimums by a margin. Don't optimize to the edge of requirements.

---

### 17. Validation Adjustments Will Happen

**My Experience:**

Pre-submission backtest: 2.56 Sharpe  
Official validation: 2.28 Sharpe (-11%)

**Why?**

Competition platform applies:
- More conservative slippage
- Stricter execution timing
- Additional cost adjustments

**Lesson:** Expect 10-15% Sharpe reduction in official validation. Build buffer into targets.

---

## Personal Lessons

### 18. Persistence Pays Off

**Timeline:**

Week 1: 0.8 Sharpe (depressing)  
Week 2: 1.2 Sharpe (better but not great)  
Week 3: 1.8 Sharpe (getting competitive)  
Week 4: 2.3 Sharpe (breakthrough!)  
Week 5: 2.6 Sharpe (optimization)  
Week 6: 2.3 Sharpe (validation, final submission)

**Temptation to Quit:** Week 2 (felt like I was behind)

**Lesson:** Improvement is non-linear. Don't compare yourself to others early. Focus on systematic progress.

---

### 19. Collaboration > Competition

**What I Did:**

Shared ideas with classmates (not exact parameters, but concepts).

**Benefits:**
- They spotted bugs in my code
- I learned about regime switching from Team B
- Healthy discussion improved everyone's understanding

**My Concern:** Won't they beat me?

**Reality:** Different implementations, different results. Sharing concepts didn't hurt my ranking.

**Lesson:** Collaborate on ideas, compete on execution. Everyone benefits.

---

### 20. Enjoy the Journey

**Realization:**

Winning isn't everything. I learned more in these 6 weeks than in entire semesters:

- Quantitative finance
- Python optimization
- Bayesian optimization
- Risk management
- Software architecture
- Problem-solving under pressure

**Lesson:** Focus on learning and growth. Rankings follow naturally.

---

## Biggest Mistakes

1. **Not reading rules thoroughly** (wasted 2 days on options strategy)
2. **Optimizing on full dataset initially** (learned about over-fitting the hard way)
3. **Ignoring transaction costs early** (false hope on high-frequency strategy)
4. **Trying ML too early** (should have started with simpler approaches)
5. **Not documenting early experiments** (couldn't remember what I tried)

---

## Biggest Successes

1. **RSI Boosting discovery** (game-changing innovation)
2. **Symbol-specific optimization** (recognized one-size doesn't fit all)
3. **Rigorous walk-forward validation** (caught over-fitting before submission)
4. **Optuna for hyperparameter tuning** (found optimal parameters efficiently)
5. **Realistic cost modeling** (strategies actually profitable in real world)

---

## Advice to Future Participants

### Technical

1. **Start simple** - RSI, moving averages work. Don't jump to ML immediately.
2. **Model costs early** - Transaction costs, slippage are real.
3. **Validate rigorously** - Walk-forward, out-of-sample testing is essential.
4. **Use Bayesian optimization** - Don't waste time on manual tuning.
5. **Symbol-specific strategies** - Different assets need different approaches.

### Process

6. **Document everything** - You'll thank yourself later.
7. **Fail fast** - If approach doesn't work in 1-2 days, move on.
8. **Read rules thoroughly** - Multiple times, highlight key constraints.
9. **Exceed minimums** - Build buffer for safety.
10. **Sleep on big decisions** - Don't submit while excited.

### Personal

11. **Be patient** - Improvement is non-linear, early struggles are normal.
12. **Collaborate** - Share ideas (not exact code), everyone benefits.
13. **Focus on learning** - Rankings will follow.
14. **Take breaks** - Fresh perspective often leads to breakthroughs.
15. **Enjoy the process** - This is a rare learning opportunity.

---

## What I'd Do Differently

**If I could start over:**

1. **Week 1:** Build simple baseline (RSI, MA crossover), model transaction costs
2. **Week 2:** Symbol-specific analysis, identify trending vs mean-reverting
3. **Week 3:** Develop tailored strategies per symbol
4. **Week 4:** Optuna hyperparameter optimization
5. **Week 5:** Look for innovations (RSI boosting, regime switching)
6. **Week 6:** Rigorous validation, stress testing, documentation

**What I wouldn't do:**
- ML/RL experiments (save for after competition)
- Options strategies (read rules first!)
- Manual parameter tuning (use Optuna from day 1)
- High-frequency without checking costs (deadly mistake)

---

## Key Takeaway

**Systematic Process + Creative Innovation + Rigorous Validation = Success**

My 2.276 Sharpe (Top 3-5) came from:
- **70% Systematic Process:** Proper data splitting, Optuna optimization, walk-forward validation
- **20% Creative Innovation:** RSI Boosting breakthrough
- **10% Luck:** Market conditions favored mean reversion strategies

**Lesson:** You can't control luck, but you can master process and foster creativity. Focus on what you can control.

---

## Final Reflection

This competition transformed me from someone who knew theory to someone who can build production-ready algorithmic trading systems. The lessons learned - technical, strategic, and personal - will serve me throughout my career in quantitative finance.

**Most Important Lesson:**

> "Simple strategies, rigorously tested, with a touch of innovation, beat complex black-box approaches every time."

Thank you to IIT Kharagpur, FYERS, and KSHITIJ for this incredible learning opportunity.

---

*Document Version: 1.0*  
*Last Updated: January 19, 2026*  
*Author: Aditya Singh (23ME3EP03)*  
*Final Result: 2.276 Sharpe, Top 3-5 out of 100+ teams*
