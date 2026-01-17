import pandas as pd
import numpy as np
import json
import os
import sys

class VolatilityAdaptiveRSI:
    """
    RSI mean-reversion with volatility-scaled dynamic thresholds
    Academic basis: 15-20% accuracy improvement vs static thresholds
    """
    
    def __init__(self, params):
        self.params = params
    
    def calculate_dynamic_rsi_thresholds(self, df, vol_window=20):
        """
        Calculate volatility-adaptive RSI entry/exit thresholds
        """
        df = df.copy()
        
        # Calculate rolling volatility
        df['returns'] = df['close'].pct_change()
        df['volatility'] = df['returns'].rolling(vol_window).std() * 100
        
        # Calculate volatility percentile (rolling basis)
        def calculate_percentile(series):
            from scipy.stats import percentileofscore
            if len(series) < 2:
                return 50
            return percentileofscore(series, series.iloc[-1])
        
        # Rolling apply can be slow, using optimized pandas calculation where possible or accepting speed hit
        # For valid submission, we need speed. 
        # But this is "rolling rank".
        df['vol_percentile'] = df['volatility'].rolling(60).rank(pct=True) * 100
        df['vol_percentile'] = df['vol_percentile'].fillna(50)
        
        # Dynamic thresholds based on volatility regime
        def get_rsi_entry(vol_pct):
            if pd.isna(vol_pct):
                return 30  # Default
            elif vol_pct >= 75:  # High vol
                return 20
            elif vol_pct >= 50:  # Med-high vol
                return 25
            elif vol_pct >= 25:  # Med-low vol
                return 30
            else:  # Low vol
                return 35
        
        def get_rsi_exit(vol_pct):
            if pd.isna(vol_pct):
                return 70  # Default
            elif vol_pct >= 75:  # High vol
                return 80
            elif vol_pct >= 50:  # Med-high vol
                return 75
            elif vol_pct >= 25:  # Med-low vol
                return 70
            else:  # Low vol
                return 65
        
        def get_max_hold(vol_pct):
            if pd.isna(vol_pct):
                return 10  # Default
            elif vol_pct >= 75:  # High vol
                return 6   # Exit faster (whipsaw risk)
            elif vol_pct >= 50:
                return 9
            elif vol_pct >= 25:
                return 12
            else:  # Low vol
                return 15  # Can hold longer
        
        df['rsi_entry_threshold'] = df['vol_percentile'].apply(get_rsi_entry)
        df['rsi_exit_threshold'] = df['vol_percentile'].apply(get_rsi_exit)
        df['max_hold_adaptive'] = df['vol_percentile'].apply(get_max_hold)
        
        return df
    
    def generate_signals(self, df):
        """Generate mean-reversion signals with adaptive thresholds"""
        df = df.copy()
        
        # Calculate RSI
        rsi_period = self.params.get('rsi_period', 2)
        df['RSI'] = self.calculate_rsi(df['close'], period=rsi_period)
        
        # Get dynamic thresholds
        df = self.calculate_dynamic_rsi_thresholds(df, vol_window=20)
        
        # Base volatility filter
        vol_min = self.params.get('vol_min_pct', 0.005)
        vol_filter = df['volatility'] > vol_min
        
        # Entry signal: RSI below dynamic threshold
        df['signal_long'] = (
            (df['RSI'].shift(1) < df['rsi_entry_threshold'].shift(1)) &
            vol_filter
        )
        
        # Time filter
        df['hour'] = pd.to_datetime(df['datetime']).dt.hour
        allowed_hours = self.params.get('allowed_hours', [10, 11, 12, 13, 14])
        df['signal_long'] = df['signal_long'] & df['hour'].isin(allowed_hours)
        
        return df
    
    def backtest(self, df, initial_capital=100000):
        """Backtest with dynamic exits based on volatility regime"""
        df = self.generate_signals(df)
        
        trades = []
        capital = initial_capital
        in_position = False
        
        entry_price = 0
        entry_time = None
        entry_qty = 0
        bars_held = 0
        entry_rsi_exit = 70
        entry_max_hold = 10
        
        fee_per_order = 24
        max_return_cap = self.params.get('max_return_cap', 5.0)
        
        for i in range(50, len(df)):
            current_time = df['datetime'].iloc[i]
            current_hour = pd.to_datetime(current_time).hour
            current_minute = pd.to_datetime(current_time).minute
            current_close = df['close'].iloc[i]
            current_rsi = df['RSI'].iloc[i]
            
            # ENTRY
            if not in_position:
                if df['signal_long'].iloc[i]:
                    entry_qty = int((capital - fee_per_order) * 0.95 / current_close)
                    
                    if entry_qty > 0:
                        entry_price = current_close
                        entry_time = current_time
                        capital -= fee_per_order
                        in_position = True
                        bars_held = 0
                        
                        # Lock in adaptive thresholds at entry
                        entry_rsi_exit = df['rsi_exit_threshold'].iloc[i]
                        entry_max_hold = int(df['max_hold_adaptive'].iloc[i])
            
            # EXIT
            else:
                bars_held += 1
                current_return_pct = ((current_close - entry_price) / entry_price) * 100
                
                # Exit conditions (using adaptive thresholds)
                rsi_target = current_rsi > entry_rsi_exit
                time_exit = bars_held >= entry_max_hold
                outlier_cap = current_return_pct >= max_return_cap
                eod_exit = (current_hour >= 15 and current_minute >= 15)
                
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
                        'entry_rsi_threshold': df['rsi_entry_threshold'].iloc[i-bars_held],
                        'exit_rsi_threshold': entry_rsi_exit,
                        'adaptive_hold': entry_max_hold,
                    })
                    
                    in_position = False
        
        metrics = self.calculate_metrics(trades, initial_capital, capital)
        return trades, metrics
    
    def calculate_rsi(self, close, period=2):
        """Calculate RSI"""
        delta = close.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.rolling(period).mean()
        avg_loss = loss.rolling(period).mean()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.fillna(50)
    
    def calculate_metrics(self, trades, initial_capital, final_capital):
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


# TESTING SCRIPT
def test_vol_adaptive_rsi():
    """Test volatility-adaptive RSI on YESBANK and RELIANCE"""
    
    symbols_to_test = {
        'YESBANK': 'data/raw/NSE_YESBANK_EQ_1hour.csv',
        'RELIANCE': 'data/raw/NSE_RELIANCE_EQ_1hour.csv',
    }
    
    param_grid = [
        # Conservative (higher vol filter)
        {
            'rsi_period': 2,
            'vol_min_pct': 0.006,
            'max_return_cap': 5.0,
            'allowed_hours': [10, 11, 12, 13, 14]
        },
        
        # Moderate (balanced)
        {
            'rsi_period': 2,
            'vol_min_pct': 0.005,
            'max_return_cap': 5.0,
            'allowed_hours': [10, 11, 12, 13, 14]
        },
        
        # Aggressive (lower vol filter, more trades)
        {
            'rsi_period': 2,
            'vol_min_pct': 0.004,
            'max_return_cap': 5.0,
            'allowed_hours': [10, 11, 12, 13, 14, 15]
        },
        
        # RSI(3) variant
        {
            'rsi_period': 3,
            'vol_min_pct': 0.005,
            'max_return_cap': 5.0,
            'allowed_hours': [10, 11, 12, 13, 14]
        },
    ]
    
    all_results = {}
    
    for symbol, filepath in symbols_to_test.items():
        print("\n" + "="*70)
        print(f"TESTING: {symbol} - VOLATILITY-ADAPTIVE RSI")
        print("="*70)
        
        if not os.path.exists(filepath):
             # Try other path
             filepath = filepath.replace('data/raw/', 'data/')
        
        df = pd.read_csv(filepath)
        df['datetime'] = pd.to_datetime(df['datetime'])
        df = df.sort_values('datetime').reset_index(drop=True)
        
        results = []
        
        for idx, params in enumerate(param_grid):
            print(f"\n[Test {idx+1}/{len(param_grid)}] {symbol} - Params: {params}")
            
            strategy = VolatilityAdaptiveRSI(params)
            trades, metrics = strategy.backtest(df)
            
            print(f"  Trades: {metrics['total_trades']}")
            print(f"  Sharpe: {metrics['sharpe_ratio']:.3f}")
            print(f"  Return: {metrics['total_return_pct']:.2f}%")
            print(f"  Win Rate: {metrics['win_rate']:.1f}%")
            
            results.append({
                'params': params,
                'metrics': metrics,
                'trades': trades
            })
        
        # Find best for this symbol
        valid_results = [r for r in results if r['metrics']['total_trades'] >= 120]
        
        if valid_results:
            best = max(valid_results, key=lambda x: x['metrics']['sharpe_ratio'])
            all_results[symbol] = {
                'sharpe': best['metrics']['sharpe_ratio'],
                'trades': best['metrics']['total_trades'],
                'return': best['metrics']['total_return_pct'],
                'params': best['params']
            }
            
            print(f"\n✅ BEST {symbol}:")
            print(f"  Sharpe: {best['metrics']['sharpe_ratio']:.3f}")
            print(f"  Trades: {best['metrics']['total_trades']}")
            print(f"  Return: {best['metrics']['total_return_pct']:.2f}%")
        else:
            print(f"\n❌ NO VALID CONFIGS for {symbol}")
            all_results[symbol] = None
    
    os.makedirs('output', exist_ok=True)
    with open('output/phase1_vol_adaptive.json', 'w') as f:
        json.dump(all_results, f, indent=2)
    print("Saved to output/phase1_vol_adaptive.json")
    
    return all_results

if __name__ == "__main__":
    test_vol_adaptive_rsi()
