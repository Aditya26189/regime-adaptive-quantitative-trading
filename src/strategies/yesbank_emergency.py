from datetime import time
import pandas as pd
import numpy as np

class YesBankEmergencyStrategy:
    def __init__(self, params=None):
        self.params = params or {}
        # Default Conservative Params
        self.rsi_period = self.params.get('rsi_period', 14)
        self.rsi_entry = self.params.get('rsi_entry', 30)   # Tuned to 30 to ensure 120 trades (25 might be too strict)
        self.rsi_exit = self.params.get('rsi_exit', 60)
        self.vol_min_pct = self.params.get('vol_min_pct', 0.005) # 0.5% min vol
        self.vol_max_pct = self.params.get('vol_max_pct', 0.03)  # 3.0% max vol (avoid crashes)
        self.max_hold_bars = self.params.get('max_hold_bars', 10)
        
    def calculate_rsi(self, series, period):
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def backtest(self, df, initial_capital=2000000.0):
        # Data Prep
        df = df.copy()
        df['datetime'] = pd.to_datetime(df['datetime'])
        df['hour'] = df['datetime'].dt.hour
        
        # Indicators
        df['rsi'] = self.calculate_rsi(df['close'], self.rsi_period)
        df['pct_change'] = df['close'].pct_change()
        df['vol'] = df['pct_change'].rolling(20).std()
        
        trades = []
        in_position = False
        entry_price = 0
        entry_time = None
        bars_held = 0
        capital = initial_capital
        fee_per_order = 48
         
        # Signal Logic
        # Entry: RSI < Entry (30), Vol inside range, Time 10-14
        df['signal_long'] = (
            (df['rsi'] < self.rsi_entry) & 
            (df['vol'] > self.vol_min_pct) & 
            (df['vol'] < self.vol_max_pct) &
            (df['hour'].between(10, 14)) # Slightly wider than 10-13 to ensure trades
        )
        
        for i in range(20, len(df)):
            current_close = df['close'].iloc[i]
            current_time = df['datetime'].iloc[i]
            
            if in_position:
                bars_held += 1
                
                # Exit Logic
                # 1. RSI Target
                # 2. Max Hold
                # 3. Stop Loss (2%)
                
                rsi_val = df['rsi'].iloc[i]
                pct_pnl = (current_close - entry_price) / entry_price
                
                is_target = rsi_val > self.rsi_exit
                is_time_limit = bars_held >= self.max_hold_bars
                is_stop = pct_pnl < -0.02
                
                if is_target or is_time_limit or is_stop:
                    exit_price = current_close
                    pnl = (exit_price - entry_price) * qty - fee_per_order
                    capital += pnl
                    
                    trades.append({
                        'symbol': 'YESBANK',
                        'entry_time': entry_time,
                        'exit_time': current_time,
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'qty': qty,
                        'pnl': pnl,
                        'return_pct': pct_pnl * 100
                    })
                    in_position = False
            
            else:
                if df['signal_long'].iloc[i]:
                    # Entry
                    # Position Sizing: Fixed fractional or simple?
                    # Using Capital / Price for simplicity but cap at something reasonable?
                    # Submission requires cumulative capital tracking, so stick to full deployment logic
                    # adjusted for expected fee drag? keeping it simple.
                    
                    # Use 95% of current simulated capital to avoid unlikely edge case overdrafts?
                    # Actually standard logic from other strats:
                    qty = int((initial_capital - fee_per_order) / current_close)
                    
                    if qty > 0:
                        entry_price = current_close
                        entry_time = current_time
                        bars_held = 0
                        in_position = True
        
        # Calculate Metrics
        metrics = {}
        if trades:
            tdf = pd.DataFrame(trades)
            metrics['total_trades'] = len(tdf)
            metrics['avg_return'] = tdf['return_pct'].mean()
            metrics['win_rate'] = len(tdf[tdf['pnl'] > 0]) / len(tdf)
            
            # Simple Sharpe approx
            returns = tdf['return_pct'] / 100
            if returns.std() > 0:
                # Annualized (assuming ~6 hours active trading, but trades are per event)
                # Using simple trade-based sharpe for tuning
                metrics['sharpe_ratio'] = (returns.mean() / returns.std()) * np.sqrt(len(tdf)) 
            else:
                metrics['sharpe_ratio'] = 0.0
        else:
            metrics['total_trades'] = 0
            metrics['sharpe_ratio'] = 0.0
            
        return trades, metrics
