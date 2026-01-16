"""
RSI(2) Strategy Optimizer
==========================
Quant Games 2026 - Systematic Parameter Optimization

Goal: Achieve positive returns while maintaining 120+ trades per symbol

CRITICAL CONSTRAINTS:
- Trade count >= 120 per symbol (HARD)
- Use only close prices (Rule 12)
- Transaction cost: ₹48 per roundtrip
- Target: Positive returns with Sharpe > 1.5
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class BacktestResult:
    """Result of a single backtest run."""
    trades: int
    total_return: float
    sharpe: float
    win_rate: float
    max_dd: float
    avg_trade_pnl: float
    transaction_costs: float


# ============================================
# PARAMETER VARIANTS
# ============================================

VARIANT_A_CONSERVATIVE = {
    "name": "A_Conservative",
    "RSI_ENTRY": 10,
    "RSI_EXIT": 90,
    "USE_EMA_200": True,
    "VOLATILITY_MIN": 0.010,
    "USE_PROFIT_TARGET": True,
    "PROFIT_TARGET_PCT": 0.015,
    "USE_STOP_LOSS": True,
    "STOP_LOSS_PCT": 0.010,
    "MAX_HOLD_BARS": 10,
}

VARIANT_B_BALANCED = {
    "name": "B_Balanced",
    "RSI_ENTRY": 15,
    "RSI_EXIT": 85,
    "USE_EMA_200": False,
    "VOLATILITY_MIN": 0.005,
    "USE_PROFIT_TARGET": True,
    "PROFIT_TARGET_PCT": 0.012,
    "USE_STOP_LOSS": True,
    "STOP_LOSS_PCT": 0.008,
    "MAX_HOLD_BARS": 8,
}

VARIANT_C_AGGRESSIVE = {
    "name": "C_Aggressive",
    "RSI_ENTRY": 18,
    "RSI_EXIT": 75,
    "USE_EMA_200": False,
    "VOLATILITY_MIN": 0.003,
    "USE_PROFIT_TARGET": True,
    "PROFIT_TARGET_PCT": 0.010,
    "USE_STOP_LOSS": True,
    "STOP_LOSS_PCT": 0.006,
    "MAX_HOLD_BARS": 6,
}

VARIANT_D_BASELINE = {
    "name": "D_Baseline",
    "RSI_ENTRY": 20,
    "RSI_EXIT": 90,
    "USE_EMA_200": False,
    "VOLATILITY_MIN": 0.002,
    "USE_PROFIT_TARGET": False,
    "PROFIT_TARGET_PCT": 0.015,
    "USE_STOP_LOSS": False,
    "STOP_LOSS_PCT": 0.010,
    "MAX_HOLD_BARS": 12,
}

VARIANT_E_PROFIT_FOCUS = {
    "name": "E_ProfitFocus",
    "RSI_ENTRY": 18,
    "RSI_EXIT": 80,
    "USE_EMA_200": False,
    "VOLATILITY_MIN": 0.004,
    "USE_PROFIT_TARGET": True,
    "PROFIT_TARGET_PCT": 0.015,  # Higher profit target
    "USE_STOP_LOSS": True,
    "STOP_LOSS_PCT": 0.005,  # Tight stop
    "MAX_HOLD_BARS": 8,
}

VARIANT_F_QUICK_EXIT = {
    "name": "F_QuickExit",
    "RSI_ENTRY": 20,
    "RSI_EXIT": 70,  # Much earlier exit
    "USE_EMA_200": False,
    "VOLATILITY_MIN": 0.003,
    "USE_PROFIT_TARGET": True,
    "PROFIT_TARGET_PCT": 0.008,  # Lower target, more wins
    "USE_STOP_LOSS": True,
    "STOP_LOSS_PCT": 0.005,
    "MAX_HOLD_BARS": 5,
}


# ============================================
# HELPER FUNCTIONS
# ============================================

def calculate_rsi(close: pd.Series, period: int = 2) -> pd.Series:
    """Calculate RSI using Wilder's smoothing."""
    delta = close.diff()
    gains = delta.where(delta > 0, 0.0)
    losses = (-delta).where(delta < 0, 0.0)
    
    alpha = 1.0 / period
    avg_gain = gains.ewm(alpha=alpha, min_periods=period, adjust=False).mean()
    avg_loss = losses.ewm(alpha=alpha, min_periods=period, adjust=False).mean()
    
    rs = avg_gain / avg_loss.replace(0, 1e-10)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    rsi = rsi.where(avg_loss > 0, 100.0)
    
    return rsi


def calculate_volatility(close: pd.Series, period: int = 14) -> pd.Series:
    """Calculate close-range volatility (Rule 12 compliant)."""
    rolling_max = close.rolling(window=period, min_periods=period).max()
    rolling_min = close.rolling(window=period, min_periods=period).min()
    return (rolling_max - rolling_min) / close


def calculate_ema(close: pd.Series, period: int = 200) -> pd.Series:
    """Calculate Exponential Moving Average."""
    return close.ewm(span=period, adjust=False).mean()


# ============================================
# OPTIMIZED BACKTEST ENGINE
# ============================================

def backtest_with_params(df: pd.DataFrame, params: dict, 
                         initial_capital: float = 100000,
                         fee_per_order: float = 24) -> BacktestResult:
    """
    Run backtest with specified parameters.
    
    Supports:
    - Configurable RSI entry/exit thresholds
    - Optional EMA(200) regime filter
    - Optional profit target and stop loss
    - Configurable max hold bars
    """
    df = df.copy()
    
    # Calculate indicators
    df['rsi2'] = calculate_rsi(df['close'], period=2)
    df['volatility'] = calculate_volatility(df['close'], period=14)
    df['ema200'] = calculate_ema(df['close'], period=200)
    
    # Parse datetime
    if df['datetime'].dtype == 'object':
        df['datetime_parsed'] = pd.to_datetime(df['datetime'])
    else:
        df['datetime_parsed'] = df['datetime']
    
    # Extract parameters
    rsi_entry = params['RSI_ENTRY']
    rsi_exit = params['RSI_EXIT']
    use_ema = params.get('USE_EMA_200', False)
    vol_min = params['VOLATILITY_MIN']
    use_profit_target = params.get('USE_PROFIT_TARGET', False)
    profit_target = params.get('PROFIT_TARGET_PCT', 0.015)
    use_stop_loss = params.get('USE_STOP_LOSS', False)
    stop_loss = params.get('STOP_LOSS_PCT', 0.010)
    max_hold = params['MAX_HOLD_BARS']
    
    # Trading state
    warmup = 200
    capital = initial_capital
    position = 0
    entry_price = 0
    bars_held = 0
    trades = []
    
    for i in range(warmup, len(df)):
        prev_close = df['close'].iloc[i-1]
        prev_rsi = df['rsi2'].iloc[i-1]
        prev_vol = df['volatility'].iloc[i-1]
        prev_ema = df['ema200'].iloc[i-1]
        
        current_price = df['close'].iloc[i]
        current_time = df['datetime_parsed'].iloc[i]
        current_hour = current_time.hour
        current_minute = current_time.minute
        
        if pd.isna(prev_rsi) or pd.isna(prev_vol):
            continue
        
        # EXIT LOGIC
        if position > 0:
            bars_held += 1
            pnl_pct = (current_price - entry_price) / entry_price
            
            # Exit conditions
            exit_rsi = prev_rsi > rsi_exit
            exit_time = bars_held >= max_hold
            exit_eod = (current_hour >= 15 and current_minute >= 15) or current_hour >= 16
            exit_profit = use_profit_target and pnl_pct >= profit_target
            exit_stop = use_stop_loss and pnl_pct <= -stop_loss
            
            if exit_rsi or exit_time or exit_eod or exit_profit or exit_stop:
                # Calculate trade PnL
                gross_pnl = (current_price - entry_price) * position
                net_pnl = gross_pnl - 48  # Roundtrip fee
                capital += (position * current_price) - fee_per_order
                
                trades.append({
                    'entry_price': entry_price,
                    'exit_price': current_price,
                    'qty': position,
                    'gross_pnl': gross_pnl,
                    'net_pnl': net_pnl,
                    'pnl_pct': pnl_pct,
                    'bars_held': bars_held,
                    'exit_reason': 'RSI' if exit_rsi else 'TIME' if exit_time else 
                                   'EOD' if exit_eod else 'PROFIT' if exit_profit else 'STOP'
                })
                
                position = 0
                entry_price = 0
                bars_held = 0
                continue
        
        # ENTRY LOGIC
        if position == 0:
            # Entry conditions
            cond_rsi = prev_rsi < rsi_entry
            cond_vol = prev_vol > vol_min
            cond_ema = prev_close > prev_ema if use_ema else True
            cond_time = not (current_hour >= 14 and current_minute >= 45)
            
            if cond_rsi and cond_vol and cond_ema and cond_time:
                available = capital - fee_per_order
                qty = int(available / current_price)
                
                if qty > 0:
                    position = qty
                    entry_price = current_price
                    capital -= (qty * current_price) + fee_per_order
                    bars_held = 0
    
    # Calculate metrics
    if len(trades) == 0:
        return BacktestResult(
            trades=0, total_return=0, sharpe=0, win_rate=0,
            max_dd=0, avg_trade_pnl=0, transaction_costs=0
        )
    
    returns = [t['pnl_pct'] for t in trades]
    returns_arr = np.array(returns)
    
    total_trades = len(trades)
    winning = sum(1 for r in returns if r > 0)
    win_rate = winning / total_trades * 100
    total_return = (capital - initial_capital) / initial_capital * 100
    
    # Sharpe
    if len(returns) > 1 and np.std(returns_arr) > 0:
        sharpe = np.mean(returns_arr) / np.std(returns_arr) * np.sqrt(250 * 7)
    else:
        sharpe = 0
    
    # Max Drawdown
    cumulative = [initial_capital]
    running_capital = initial_capital
    for t in trades:
        running_capital += t['net_pnl']
        cumulative.append(running_capital)
    cumulative = np.array(cumulative)
    peak = np.maximum.accumulate(cumulative)
    drawdown = (cumulative - peak) / peak * 100
    max_dd = drawdown.min()
    
    # Average trade PnL
    avg_pnl = np.mean([t['net_pnl'] for t in trades])
    
    # Transaction costs
    total_costs = total_trades * 48
    
    return BacktestResult(
        trades=total_trades,
        total_return=round(total_return, 2),
        sharpe=round(sharpe, 2),
        win_rate=round(win_rate, 2),
        max_dd=round(max_dd, 2),
        avg_trade_pnl=round(avg_pnl, 2),
        transaction_costs=round(total_costs, 2)
    )


def score_result(result: BacktestResult) -> float:
    """
    Calculate composite score for ranking variants.
    Higher = better.
    """
    score = 0
    
    # Hard constraint violations = instant penalty
    if result.trades < 120:
        return -1000
    
    # Positive return bonus/penalty
    if result.total_return > 0:
        score += result.total_return * 20  # Big bonus for positive
    else:
        score += result.total_return * 50  # Heavy penalty for negative
    
    # Win rate contribution
    score += (result.win_rate - 40) * 3  # Bonus for >40%
    
    # Sharpe contribution
    score += result.sharpe * 30
    
    # Trade count sweet spot (140-180 ideal)
    if 140 <= result.trades <= 180:
        score += 50
    elif result.trades > 200:
        score -= (result.trades - 200) * 0.5  # Slight penalty
    
    # Average trade profitability
    if result.avg_trade_pnl > 0:
        score += 100  # Big bonus for profitable avg trade
    
    return score


# ============================================
# MAIN OPTIMIZATION
# ============================================

def optimize_on_symbol(symbol_name: str, filepath: str, variants: list) -> dict:
    """
    Test all variants on a single symbol.
    
    Returns ranked results.
    """
    df = pd.read_csv(filepath)
    
    print(f"\n{'='*60}")
    print(f"OPTIMIZING: {symbol_name}")
    print(f"Data: {len(df)} bars")
    print(f"{'='*60}")
    
    results = []
    
    for variant in variants:
        result = backtest_with_params(df, variant)
        score = score_result(result)
        
        results.append({
            'variant': variant['name'],
            'params': variant,
            'result': result,
            'score': score
        })
        
        status = "✅" if result.trades >= 120 and result.total_return > 0 else \
                 "⚠️" if result.trades >= 120 else "❌"
        
        print(f"\n{status} {variant['name']}:")
        print(f"   Trades: {result.trades}")
        print(f"   Return: {result.total_return}%")
        print(f"   Sharpe: {result.sharpe}")
        print(f"   Win Rate: {result.win_rate}%")
        print(f"   Avg Trade: ₹{result.avg_trade_pnl}")
        print(f"   Score: {score:.0f}")
    
    # Rank by score
    ranked = sorted(results, key=lambda x: x['score'], reverse=True)
    
    print(f"\n{'='*60}")
    print("RANKING:")
    for i, r in enumerate(ranked, 1):
        print(f"  {i}. {r['variant']}: Score={r['score']:.0f}, Return={r['result'].total_return}%")
    
    return ranked


def optimize_all_symbols(variants: list) -> dict:
    """
    Run optimization across all 5 symbols.
    """
    symbols = [
        ("NIFTY50", "fyers_data/NSE_NIFTY50_INDEX_1hour.csv"),
        ("RELIANCE", "fyers_data/NSE_RELIANCE_EQ_1hour.csv"),
        ("VBL", "fyers_data/NSE_VBL_EQ_1hour.csv"),
        ("YESBANK", "fyers_data/NSE_YESBANK_EQ_1hour.csv"),
        ("SUNPHARMA", "fyers_data/NSE_SUNPHARMA_EQ_1hour.csv"),
    ]
    
    all_results = {}
    
    for symbol, filepath in symbols:
        ranked = optimize_on_symbol(symbol, filepath, variants)
        all_results[symbol] = ranked
    
    return all_results


def find_best_variant(all_results: dict) -> str:
    """
    Find the variant that performs best across all symbols.
    """
    variant_scores = {}
    
    for symbol, ranked in all_results.items():
        for r in ranked:
            name = r['variant']
            if name not in variant_scores:
                variant_scores[name] = {'total_score': 0, 'symbols_passed': 0, 
                                        'total_return': 0, 'total_trades': 0}
            
            variant_scores[name]['total_score'] += r['score']
            variant_scores[name]['total_return'] += r['result'].total_return
            variant_scores[name]['total_trades'] += r['result'].trades
            
            if r['result'].trades >= 120:
                variant_scores[name]['symbols_passed'] += 1
    
    # Rank variants
    print("\n" + "="*70)
    print("CROSS-SYMBOL VARIANT PERFORMANCE")
    print("="*70)
    
    for name, scores in sorted(variant_scores.items(), key=lambda x: x[1]['total_score'], reverse=True):
        avg_return = scores['total_return'] / 5
        avg_trades = scores['total_trades'] / 5
        print(f"\n{name}:")
        print(f"  Total Score: {scores['total_score']:.0f}")
        print(f"  Symbols Passed: {scores['symbols_passed']}/5")
        print(f"  Avg Return: {avg_return:.2f}%")
        print(f"  Avg Trades: {avg_trades:.0f}")
    
    # Find best
    best = max(variant_scores.items(), key=lambda x: x[1]['total_score'])
    return best[0]


# ============================================
# MAIN
# ============================================

if __name__ == "__main__":
    print("="*70)
    print("RSI(2) STRATEGY OPTIMIZATION")
    print("="*70)
    print("Goal: Positive returns with 120+ trades")
    print("Constraint: Close prices only (Rule 12)")
    print()
    
    # Define variants to test
    variants = [
        VARIANT_A_CONSERVATIVE,
        VARIANT_B_BALANCED,
        VARIANT_C_AGGRESSIVE,
        VARIANT_D_BASELINE,
        VARIANT_E_PROFIT_FOCUS,
        VARIANT_F_QUICK_EXIT,
    ]
    
    print(f"Testing {len(variants)} variants...")
    
    # Phase 1: Test all variants on all symbols
    all_results = optimize_all_symbols(variants)
    
    # Phase 2: Find best overall variant
    best_variant = find_best_variant(all_results)
    
    print("\n" + "="*70)
    print(f"BEST VARIANT: {best_variant}")
    print("="*70)
    
    # Save results
    with open("optimization_results.txt", "w") as f:
        f.write("OPTIMIZATION RESULTS\n")
        f.write("="*60 + "\n\n")
        
        for symbol, ranked in all_results.items():
            f.write(f"\n{symbol}:\n")
            for r in ranked:
                f.write(f"  {r['variant']}: {r['result'].trades} trades, "
                       f"{r['result'].total_return}% return, Score={r['score']:.0f}\n")
        
        f.write(f"\n\nBEST OVERALL: {best_variant}\n")
    
    print("\nResults saved to optimization_results.txt")
