"""
RSI(2) Optimizer V3 - Hybrid Approach
======================================
Combines quality filters with looser thresholds to meet 120 trade minimum.

Key insight from V2:
- RSI Divergence improved returns to -0.04% but only 21 trades
- Need to combine quality with quantity
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass


@dataclass
class BacktestResult:
    trades: int
    total_return: float
    sharpe: float
    win_rate: float
    max_dd: float
    avg_pnl: float


# Hybrid variants - quality + quantity
VARIANTS = [
    {
        "name": "Hybrid_RSI30_Div",
        "RSI_ENTRY": 30,  # Much looser to get more trades
        "RSI_EXIT": 80,
        "REQUIRE_RSI_RISING": True,  # Keep divergence filter
        "VOLATILITY_MIN": 0.001,
        "MAX_HOLD_BARS": 10,
    },
    {
        "name": "Hybrid_RSI35_Div", 
        "RSI_ENTRY": 35,  # Even looser
        "RSI_EXIT": 75,
        "REQUIRE_RSI_RISING": True,
        "VOLATILITY_MIN": 0.001,
        "MAX_HOLD_BARS": 8,
    },
    {
        "name": "Hybrid_RSI40_Div",
        "RSI_ENTRY": 40,  # Very loose entry but require divergence
        "RSI_EXIT": 70,
        "REQUIRE_RSI_RISING": True,
        "VOLATILITY_MIN": 0.001,
        "MAX_HOLD_BARS": 6,
    },
    {
        "name": "NoDiv_RSI25_EarlyExit",
        "RSI_ENTRY": 25,
        "RSI_EXIT": 70,  # Earlier exit (take profits)
        "REQUIRE_RSI_RISING": False,
        "VOLATILITY_MIN": 0.001,
        "MAX_HOLD_BARS": 8,
    },
    {
        "name": "NoDiv_RSI22_MedExit",
        "RSI_ENTRY": 22,
        "RSI_EXIT": 80,
        "REQUIRE_RSI_RISING": False,
        "VOLATILITY_MIN": 0.002,
        "MAX_HOLD_BARS": 10,
    },
    {
        "name": "Baseline_Current",
        "RSI_ENTRY": 20,
        "RSI_EXIT": 90,
        "REQUIRE_RSI_RISING": False,
        "VOLATILITY_MIN": 0.002,
        "MAX_HOLD_BARS": 12,
    },
]


def calculate_rsi(close, period=2):
    delta = close.diff()
    gains = delta.where(delta > 0, 0.0)
    losses = (-delta).where(delta < 0, 0.0)
    alpha = 1.0 / period
    avg_gain = gains.ewm(alpha=alpha, min_periods=period, adjust=False).mean()
    avg_loss = losses.ewm(alpha=alpha, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-10)
    return 100.0 - (100.0 / (1.0 + rs))


def calculate_volatility(close, period=14):
    rolling_max = close.rolling(window=period, min_periods=period).max()
    rolling_min = close.rolling(window=period, min_periods=period).min()
    return (rolling_max - rolling_min) / close


def backtest(df, params, initial_capital=100000):
    df = df.copy()
    df['rsi2'] = calculate_rsi(df['close'], period=2)
    df['volatility'] = calculate_volatility(df['close'], period=14)
    
    if df['datetime'].dtype == 'object':
        df['datetime_parsed'] = pd.to_datetime(df['datetime'])
    else:
        df['datetime_parsed'] = df['datetime']
    
    rsi_entry = params['RSI_ENTRY']
    rsi_exit = params['RSI_EXIT']
    vol_min = params['VOLATILITY_MIN']
    max_hold = params['MAX_HOLD_BARS']
    require_rising = params.get('REQUIRE_RSI_RISING', False)
    
    warmup = 50
    capital = initial_capital
    position = 0
    entry_price = 0
    bars_held = 0
    trades = []
    
    for i in range(warmup, len(df)):
        prev_close = df['close'].iloc[i-1]
        prev_rsi = df['rsi2'].iloc[i-1]
        prev_rsi_2 = df['rsi2'].iloc[i-2] if i >= 2 else prev_rsi
        prev_vol = df['volatility'].iloc[i-1]
        
        current_price = df['close'].iloc[i]
        current_time = df['datetime_parsed'].iloc[i]
        current_hour = current_time.hour
        current_minute = current_time.minute
        
        if pd.isna(prev_rsi) or pd.isna(prev_vol):
            continue
        
        # EXIT
        if position > 0:
            bars_held += 1
            exit_rsi = prev_rsi > rsi_exit
            exit_time = bars_held >= max_hold
            exit_eod = (current_hour >= 15 and current_minute >= 15) or current_hour >= 16
            
            if exit_rsi or exit_time or exit_eod:
                pnl_pct = (current_price - entry_price) / entry_price
                net_pnl = (current_price - entry_price) * position - 48
                capital += (position * current_price) - 24
                trades.append({'pnl_pct': pnl_pct, 'net_pnl': net_pnl})
                position = 0
                entry_price = 0
                bars_held = 0
                continue
        
        # ENTRY
        if position == 0:
            cond_rsi = prev_rsi < rsi_entry
            cond_vol = prev_vol > vol_min
            cond_time = not (current_hour >= 14 and current_minute >= 45)
            cond_rising = (prev_rsi > prev_rsi_2) if require_rising else True
            
            if cond_rsi and cond_vol and cond_time and cond_rising:
                available = capital - 24
                qty = int(available / current_price)
                if qty > 0:
                    position = qty
                    entry_price = current_price
                    capital -= (qty * current_price) + 24
                    bars_held = 0
    
    if len(trades) == 0:
        return BacktestResult(0, 0, 0, 0, 0, 0)
    
    returns = np.array([t['pnl_pct'] for t in trades])
    total_trades = len(trades)
    winning = sum(1 for r in returns if r > 0)
    win_rate = winning / total_trades * 100
    total_return = (capital - initial_capital) / initial_capital * 100
    
    if len(returns) > 1 and np.std(returns) > 0:
        sharpe = np.mean(returns) / np.std(returns) * np.sqrt(250 * 7)
    else:
        sharpe = 0
    
    cumulative = [initial_capital]
    running = initial_capital
    for t in trades:
        running += t['net_pnl']
        cumulative.append(running)
    peak = np.maximum.accumulate(cumulative)
    drawdown = (np.array(cumulative) - peak) / peak * 100
    max_dd = drawdown.min()
    avg_pnl = np.mean([t['net_pnl'] for t in trades])
    
    return BacktestResult(total_trades, round(total_return,2), round(sharpe,2),
                          round(win_rate,2), round(max_dd,2), round(avg_pnl,2))


def main():
    symbols = [
        ("NIFTY50", "fyers_data/NSE_NIFTY50_INDEX_1hour.csv"),
        ("RELIANCE", "fyers_data/NSE_RELIANCE_EQ_1hour.csv"),
        ("VBL", "fyers_data/NSE_VBL_EQ_1hour.csv"),
        ("YESBANK", "fyers_data/NSE_YESBANK_EQ_1hour.csv"),
        ("SUNPHARMA", "fyers_data/NSE_SUNPHARMA_EQ_1hour.csv"),
    ]
    
    print("="*80)
    print("RSI(2) OPTIMIZER V3 - HYBRID QUALITY + QUANTITY")
    print("="*80)
    
    totals = {v['name']: {'return': 0, 'trades': 0, 'passed': 0, 'positive': 0} 
              for v in VARIANTS}
    
    for symbol, fp in symbols:
        print(f"\n{'='*60}")
        print(f"SYMBOL: {symbol}")
        print(f"{'='*60}")
        df = pd.read_csv(fp)
        
        for v in VARIANTS:
            r = backtest(df, v)
            status = "✅" if r.trades >= 120 and r.total_return > 0 else \
                     "⚠️" if r.trades >= 120 else "❌"
            print(f"{status} {v['name']:25} | T:{r.trades:3} | Ret:{r.total_return:7.2f}% | "
                  f"Win:{r.win_rate:5.1f}% | DD:{r.max_dd:6.1f}%")
            
            totals[v['name']]['return'] += r.total_return
            totals[v['name']]['trades'] += r.trades
            if r.trades >= 120:
                totals[v['name']]['passed'] += 1
            if r.total_return > 0:
                totals[v['name']]['positive'] += 1
    
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"{'Variant':<30} {'Avg Ret':>10} {'Avg Trade':>10} {'Pass120':>8} {'Positive':>10}")
    print("-"*80)
    
    for name, t in sorted(totals.items(), key=lambda x: x[1]['return'], reverse=True):
        avg_ret = t['return'] / 5
        avg_trades = t['trades'] / 5
        print(f"{name:<30} {avg_ret:>9.2f}% {avg_trades:>10.0f} {t['passed']}/5{' '*5} {t['positive']}/5")
    
    # Find best
    best = max(totals.items(), key=lambda x: (x[1]['passed'], x[1]['return']))
    print("\n" + "="*80)
    print(f"BEST: {best[0]} (Passed: {best[1]['passed']}/5, Avg Return: {best[1]['return']/5:.2f}%)")
    print("="*80)


if __name__ == "__main__":
    main()
