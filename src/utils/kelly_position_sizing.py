import numpy as np
import pandas as pd

def calculate_kelly_fraction(recent_trades, min_fraction=0.30, max_fraction=0.90):
    """
    Calculate Kelly Criterion position sizing based on recent performance
    
    Formula: Kelly% = (Win_Rate * Avg_Win - Loss_Rate * Avg_Loss) / Avg_Win
    
    Use fractional Kelly (50%) for safety
    """
    if len(recent_trades) == 0:
        return 0.50  # Default: 50% allocation
    
    trades_df = pd.DataFrame(recent_trades)
    
    if 'pnl' not in trades_df.columns:
         return 0.50

    wins = trades_df[trades_df['pnl'] > 0]
    losses = trades_df[trades_df['pnl'] <= 0]
    
    win_rate = len(wins) / len(trades_df) if len(trades_df) > 0 else 0.5
    
    avg_win = wins['pnl'].mean() if len(wins) > 0 else 0
    avg_loss = abs(losses['pnl'].mean()) if len(losses) > 0 else avg_win
    
    if avg_win > 0:
        kelly = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
    else:
        kelly = 0.5
    
    # Use fractional Kelly (50% of full Kelly)
    fractional_kelly = kelly * 0.5
    
    # Bound between min and max
    position_fraction = max(min_fraction, min(fractional_kelly, max_fraction))
    
    return position_fraction


# MODIFIED BACKTEST WITH KELLY SIZING
def backtest_with_kelly(strategy_class, df, params, initial_capital=100000, rolling_window=20):
    """
    Run backtest with Kelly Criterion position sizing
    Args:
        strategy_class: Strategy class (must have generate_signals method)
        df: Price data
        params: Strategy parameters
        initial_capital: Starting capital
        rolling_window: Number of recent trades to use for Kelly calculation
    """
    strategy = strategy_class(params)
    df_signals = strategy.generate_signals(df)
    
    # Calculate RSI for exits (if not already done)
    if 'RSI' not in df_signals.columns:
        df_signals['RSI'] = calculate_rsi(df_signals['close'], period=params.get('rsi_period', 2))
    
    trades = []
    capital = initial_capital
    in_position = False
    
    entry_price = 0
    entry_time = None
    entry_qty = 0
    bars_held = 0
     kelly_fraction = 0.5
    
    fee_per_order = 24
    max_hold = params.get('max_hold_bars', 10)
    rsi_exit_threshold = params.get('rsi_exit', 70)
    max_return_cap = params.get('max_return_cap', 5.0)
    
    for i in range(50, len(df_signals)):
        current_time = df_signals['datetime'].iloc[i]
        current_hour = pd.to_datetime(current_time).hour
        current_minute = pd.to_datetime(current_time).minute
        current_close = df_signals['close'].iloc[i]
        current_rsi = df_signals['RSI'].iloc[i]
        
        # ENTRY with Kelly sizing
        if not in_position:
            if df_signals['signal_long'].iloc[i]:
                # Calculate Kelly fraction based on recent performance
                recent_trades = trades[-rolling_window:] if len(trades) >= rolling_window else trades
                kelly_fraction = calculate_kelly_fraction(recent_trades)
                
                # Position size using Kelly
                position_value = (capital - fee_per_order) * kelly_fraction
                entry_qty = int(position_value / current_close)
                
                if entry_qty > 0:
                    entry_price = current_close
                    entry_time = current_time
                    capital -= fee_per_order
                    in_position = True
                    bars_held = 0
        
        # EXIT
        else:
            bars_held += 1
            current_return_pct = ((current_close - entry_price) / entry_price) * 100
            
            rsi_target = current_rsi > rsi_exit_threshold
            time_exit = bars_held >= max_hold
            outlier_cap = current_return_pct >= max_return_cap
            # Fix 15:15 exit using proper comparison
            eod_exit = (current_hour >= 15 and current_minute >= 15)
            # Make sure eod_exit is bool
            
            if rsi_target or time_exit or outlier_cap or eod_exit:
                exit_price = current_close
                gross_pnl = entry_qty * (exit_price - entry_price)
                net_pnl = gross_pnl - (2 * fee_per_order)
                capital += (entry_qty * exit_price) - fee_per_order
                
                trades.append({
                    'entry_time': entry_time,
                    'exit_time': current_time,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'qty': entry_qty,
                    'pnl': net_pnl,
                    'capital': capital,
                    'bars_held': bars_held,
                    'return_pct': current_return_pct,
                    'kelly_fraction': kelly_fraction,
                })
                
                in_position = False
    
    # Calculate metrics
    metrics = calculate_metrics(trades, initial_capital, capital)
    return trades, metrics


def calculate_rsi(close, period=2):
    """Calculate RSI"""
    delta = close.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)


def calculate_metrics(trades, initial_capital, final_capital):
    """Calculate metrics"""
    if len(trades) == 0:
        return {
            'total_trades': 0,
            'sharpe_ratio': 0,
            'total_return_pct': 0,
            'win_rate': 0,
            'max_drawdown_pct': 0,
            'final_capital': final_capital
        }
    
    trades_df = pd.DataFrame(trades)
    
    total_trades = len(trades_df)
    total_return_pct = (final_capital - initial_capital) / initial_capital * 100
    
    wins = (trades_df['pnl'] > 0).sum()
    win_rate = (wins / total_trades) * 100
    
    returns = (trades_df['pnl'] / initial_capital) * 100
    if returns.std() > 0:
        trades_per_year = 1500 / (len(trades_df) / 250) if len(trades_df) > 0 else 1
        sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(min(trades_per_year, 252))
    else:
        sharpe_ratio = 0
    
    capital_curve = trades_df['capital'].values
    running_max = np.maximum.accumulate(capital_curve)
    drawdown = (capital_curve - running_max) / running_max * 100
    max_drawdown_pct = drawdown.min()
    
    return {
        'total_trades': total_trades,
        'sharpe_ratio': sharpe_ratio,
        'total_return_pct': total_return_pct,
        'win_rate': win_rate,
        'max_drawdown_pct': max_drawdown_pct,
        'final_capital': final_capital,
        'avg_trade_pnl': trades_df['pnl'].mean(),
    }
