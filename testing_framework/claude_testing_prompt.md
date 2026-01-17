# 🤖 CLAUDE TESTING PROMPT
## Copy/Paste this to an AI Assistant for Analysis

**Context:**
I am submitting a quantitative trading strategy (Strategy 4) for IIT Kharagpur Quant Games.
My portfolio Sharpe is 2.559 (Optimized), but I need to validte robustness.

**Task:**
Analyze the following strategy logic and trade logs for overfitting and structural flaws.

**Strategy Logic:**
[Paste content of STRATEGY_4_LOGIC.md here]

**Validation Data:**
[Paste content of output/test_results.json here]

**Questions:**
1. Does the huge gap between Train/Test Sharpe indicate fatal overfitting?
2. Are the returns for VBL/NIFTY50 technically impossible (Overflow)?
3. Is the 'Profit Ladder' mechanism statistically valid or just curve-fitting?
4. Recommend 3 immediate fixes I can implement in Python within 30 minutes.

**Constraints:**
- Do not suggest rewriting the whole engine.
- Focus on parameter tuning and safety checks.
- Prioritize passing the "120 trade minimum" constraint.
