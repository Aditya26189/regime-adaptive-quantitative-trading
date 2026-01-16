"""
RSI(2) Strategy Optimizer V2 - Entry Quality Focus
====================================================
Focus on improving ENTRY QUALITY rather than exit management.

Key insight: Stop losses and profit targets made returns WORSE.
New approach: Better entries = more winning trades

New Filters to Test:
1. RSI Divergence (RSI rising while price falling)
2. Price above short-term MA (SMA50 instead of EMA200)
3. Momentum filter (ROC positive)
4. Time-of-day optimization
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class BacktestResult:
    trades: int
    total_return: float
    sharpe: float
    win_rate: float
    max_dd: float
    avg_trade_pnl: float


# ============================================
# NEW VARIANTS - ENTRY QUALITY FOCUSED
# ============================================

VARIANT_RSI_DIVERGENCE = {
    "name": "RSI_Divergence",
    "RSI_ENTRY": 20,
    "RSI_EXIT": 90,
    "REQUIRE_RSI_RISING": True,  # RSI must be rising (divergence)
    "USE_SMA_50": False,
    "VOLATILITY_MIN": 0.002,
    "MAX_HOLD_BARS": 12,
}

VARIANT_SMA50_FILTER = {
    "name": "SMA50_Filter",
    "RSI_ENTRY": 20,
    "RSI_EXIT": 90,
    "REQUIRE_RSI_RISING": False,
    "USE_SMA_50": True,  # Price must be > SMA50
    "VOLATILITY_MIN": 0.002,
    "MAX_HOLD_BARS": 12,
}

VARIANT_MOMENTUM_FILTER = {
    "name": "Momentum_Filter",
    "RSI_ENTRY": 20,
    "RSI_EXIT": 90,
    "REQUIRE_RSI_RISING": False,
    "USE_SMA_50": False,
    "REQUIRE_ROC_POSITIVE": True,  # 5-bar ROC must be > 0
    "VOLATILITY_MIN": 0.002,
    "MAX_HOLD_BARS": 12,
}

VARIANT_COMBINED = {
    "name": "Combined_Filters",
    "RSI_ENTRY": 22,  # Slightly looser
    "RSI_EXIT": 85,
    "REQUIRE_RSI_RISING": True,
    "USE_SMA_50": True,
    "REQUIRE_ROC_POSITIVE": False,
    "VOLATILITY_MIN": 0.003,
    "MAX_HOLD_BARS": 10,
}

VARIANT_LOOSER_ENTRY = {
    "name": "Looser_Entry_Better_Exit",
    "RSI_ENTRY": 25,  # More entries
    "RSI_EXIT": 80,  # Earlier exit
    "REQUIRE_RSI_RISING": False,
    "USE_SMA_50": False,
    "VOLATILITY_MIN": 0.002,
    "MAX_HOLD_BARS": 8,
}

VARIANT_STRICT_ENTRY = {
    "name": "Strict_Entry_Hold_Longer",
    "RSI_ENTRY": 15,  # Stricter
    "RSI_EXIT": 95,  # Hold longer
    "REQUIRE_RSI_RISING": True,
    "USE_SMA_50": False,
    "VOLATILITY_MIN": 0.004,
    "MAX_HOLD_BARS": 15,
}


# ============================================
# HELPER FUNCTIONS
# ============================================

def calculate_rsi(close: pd.Series, period: int = 2) -> pd.Series:
    delta = close.diff()
    gains = delta.where(delta > 0, 0.0)
    losses = (-delta).where(delta < 0, 0.0)
    alpha = 1.0 / period
    avg_gain = gains.ewm(alpha=alpha, min_periods=period, adjust=False).mean()
    avg_loss = losses.ewm(alpha=alpha, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-10)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi.where(avg_loss > 0, 100.0)


def calculate_sma(close: pd.Series, period: int = 50) -> pd.Series:
    return close.rolling(window=period, min_periods=period).mean()


def calculate_roc(close: pd.Series, period: int = 5) -> pd.Series:
    return (close - close.shift(period)) / close.shift(period)


def calculate_volatility(close: pd.Series, period: int = 14) -> pd.Series:
    rolling_max = close.rolling(window=period, min_periods=period).max()
    rolling_min = close.rolling(window=period, min_periods=period).min()
    return (rolling_max - rolling_min) / close


# ============================================
# ENHANCED BACKTEST 
# ============================================

def backtest_v2(df: pd.DataFrame, params: dict, 
                initial_capital: float = 100000) -> BacktestResult:
    """Enhanced backtest with entry quality filters."""
    
    df = df.copy()
    
    # Calculate indicators
    df['rsi2'] = calculate_rsi(df['close'], period=2)
    df['sma50'] = calculate_sma(df['close'], period=50)
    df['roc5'] = calculate_roc(df['close'], period=5)
    df['volatility'] = calculate_volatility(df['close'], period=14)
    
    # Parse datetime
    if df['datetime'].dtype == 'object':
        df['datetime_parsed'] = pd.to_datetime(df['datetime'])
    else:
        df['datetime_parsed'] = df['datetime']
    
    # Extract parameters
    rsi_entry = params['RSI_ENTRY']
    rsi_exit = params['RSI_EXIT']
    vol_min = params['VOLATILITY_MIN']
    max_hold = params['MAX_HOLD_BARS']
    
    require_rsi_rising = params.get('REQUIRE_RSI_RISING', False)
    use_sma50 = params.get('USE_SMA_50', False)
    require_roc_positive = params.get('REQUIRE_ROC_POSITIVE', False)
    
    # Trading state
    warmup = 50
    capital = initial_capital
    position = 0
    entry_price = 0
    bars_held = 0
    trades = []
    
    for i in range(warmup, len(df)):
        prev_close = df['close'].iloc[i-1]
        prev_rsi = df['rsi2'].iloc[i-1]
        prev_rsi_2back = df['rsi2'].iloc[i-2] if i >= 2 else prev_rsi
        prev_vol = df['volatility'].iloc[i-1]
        prev_sma50 = df['sma50'].iloc[i-1]
        prev_roc5 = df['roc5'].iloc[i-1]
        
        current_price = df['close'].iloc[i]
        current_time = df['datetime_parsed'].iloc[i]
        current_hour = current_time.hour
        current_minute = current_time.minute
        
        if pd.isna(prev_rsi) or pd.isna(prev_vol):
            continue
        
        # EXIT LOGIC
        if position > 0:
            bars_held += 1
            
            exit_rsi = prev_rsi > rsi_exit
            exit_time = bars_held >= max_hold
            exit_eod = (current_hour >= 15 and current_minute >= 15) or current_hour >= 16
            
            if exit_rsi or exit_time or exit_eod:
                pnl_pct = (current_price - entry_price) / entry_price
                gross_pnl = (current_price - entry_price) * position
                net_pnl = gross_pnl - 48
                capital += (position * current_price) - 24
                
                trades.append({
                    'entry_price': entry_price,
                    'exit_price': current_price,
                    'qty': position,
                    'pnl_pct': pnl_pct,
                    'net_pnl': net_pnl
                })
                
                position = 0
                entry_price = 0
                bars_held = 0
                continue
        
        # ENTRY LOGIC - Enhanced with quality filters
        if position == 0:
            # Basic conditions
            cond_rsi = prev_rsi < rsi_entry
            cond_vol = prev_vol > vol_min
            cond_time = not (current_hour >= 14 and current_minute >= 45)
            
            # Optional quality filters
            cond_rsi_rising = (prev_rsi > prev_rsi_2back) if require_rsi_rising else True
            cond_sma50 = (prev_close > prev_sma50) if use_sma50 else True
            cond_roc = (prev_roc5 > 0 if not pd.isna(prev_roc5) else False) if require_roc_positive else True
            
            # All conditions must be true
            if cond_rsi and cond_vol and cond_time and cond_rsi_rising and cond_sma50 and cond_roc:
                available = capital - 24
                qty = int(available / current_price)
                
                if qty > 0:
                    position = qty
                    entry_price = current_price
                    capital -= (qty * current_price) + 24
                    bars_held = 0
    
    # Calculate metrics
    if len(trades) == 0:
        return BacktestResult(trades=0, total_return=0, sharpe=0, 
                              win_rate=0, max_dd=0, avg_trade_pnl=0)
    
    returns = [t['pnl_pct'] for t in trades]
    returns_arr = np.array(returns)
    
    total_trades = len(trades)
    winning = sum(1 for r in returns if r > 0)
    win_rate = winning / total_trades * 100
    total_return = (capital - initial_capital) / initial_capital * 100
    
    if len(returns) > 1 and np.std(returns_arr) > 0:
        sharpe = np.mean(returns_arr) / np.std(returns_arr) * np.sqrt(250 * 7)
    else:
        sharpe = 0
    
    cumulative = [initial_capital]
    running = initial_capital
    for t in trades:
        running += t['net_pnl']
        cumulative.append(running)
    cumulative = np.array(cumulative)
    peak = np.maximum.accumulate(cumulative)
    drawdown = (cumulative - peak) / peak * 100
    max_dd = drawdown.min()
    
    avg_pnl = np.mean([t['net_pnl'] for t in trades])
    
    return BacktestResult(
        trades=total_trades,
        total_return=round(total_return, 2),
        sharpe=round(sharpe, 2),
        win_rate=round(win_rate, 2),
        max_dd=round(max_dd, 2),
        avg_trade_pnl=round(avg_pnl, 2)
    )


def test_all_variants():
    """Test all entry-focused variants on all symbols."""
    
    symbols = [
        ("NIFTY50", "fyers_data/NSE_NIFTY50_INDEX_1hour.csv"),
        ("RELIANCE", "fyers_data/NSE_RELIANCE_EQ_1hour.csv"),
        ("VBL", "fyers_data/NSE_VBL_EQ_1hour.csv"),
        ("YESBANK", "fyers_data/NSE_YESBANK_EQ_1hour.csv"),
        ("SUNPHARMA", "fyers_data/NSE_SUNPHARMA_EQ_1hour.csv"),
    ]
    
    variants = [
        VARIANT_RSI_DIVERGENCE,
        VARIANT_SMA50_FILTER,
        VARIANT_MOMENTUM_FILTER,
        VARIANT_COMBINED,
        VARIANT_LOOSER_ENTRY,
        VARIANT_STRICT_ENTRY,
    ]
    
    print("="*70)
    print("RSI(2) OPTIMIZER V2 - ENTRY QUALITY FOCUS")
    print("="*70)
    
    # Track results
    variant_totals = {v['name']: {'return': 0, 'trades': 0, 'passed': 0} for v in variants}
    
    for symbol, filepath in symbols:
        print(f"\n{'='*60}")
        print(f"SYMBOL: {symbol}")
        print(f"{'='*60}")
        
        df = pd.read_csv(filepath)
        
        for variant in variants:
            result = backtest_v2(df, variant)
            
            status = "✅" if result.trades >= 120 and result.total_return > 0 else \
                     "⚠️" if result.trades >= 120 else "❌"
            
            print(f"{status} {variant['name']:25} | Trades: {result.trades:3} | "
                  f"Return: {result.total_return:6.2f}% | Win: {result.win_rate:5.1f}%")
            
            variant_totals[variant['name']]['return'] += result.total_return
            variant_totals[variant['name']]['trades'] += result.trades
            if result.trades >= 120:
                variant_totals[variant['name']]['passed'] += 1
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY - AVERAGE ACROSS 5 SYMBOLS")
    print("="*70)
    
    for name, totals in sorted(variant_totals.items(), 
                               key=lambda x: x[1]['return'], reverse=True):
        avg_return = totals['return'] / 5
        avg_trades = totals['trades'] / 5
        print(f"{name:25} | Avg Return: {avg_return:6.2f}% | "
              f"Avg Trades: {avg_trades:5.0f} | Passed: {totals['passed']}/5")


if __name__ == "__main__":
    test_all_variants()
