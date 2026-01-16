"""
Portfolio Management Layer
===========================
Quant Games Hackathon - IIT Kharagpur

Unified capital pool for multi-asset, multi-strategy trading.

Features:
- Single capital pool (₹100,000 initial)
- Multi-asset event processing on merged timeline
- Transaction cost accounting (₹24 per order)
- Global 3-position limit enforcement
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from datetime import datetime


@dataclass
class Position:
    """Represents an open trading position."""
    symbol: str
    strategy: str
    entry_time: str
    entry_price: float
    qty: int
    
    def current_value(self, current_price: float) -> float:
        """Calculate current position value."""
        return self.qty * current_price
    
    def unrealized_pnl(self, current_price: float) -> float:
        """Calculate unrealized P&L."""
        return (current_price - self.entry_price) * self.qty


@dataclass
class Trade:
    """Represents a completed trade."""
    student_roll_number: str
    strategy_submission_number: int
    symbol: str
    timeframe: str
    entry_trade_time: str
    exit_trade_time: str
    entry_trade_price: float
    exit_trade_price: float
    qty: int
    fees: float = 48
    cumulative_capital_after_trade: float = 0
    
    def gross_pnl(self) -> float:
        return (self.exit_trade_price - self.entry_trade_price) * self.qty
    
    def net_pnl(self) -> float:
        return self.gross_pnl() - self.fees


class PortfolioManager:
    """
    Unified portfolio manager for multi-asset trading.
    
    Features:
    - Unified capital pool
    - 3-position maximum global limit
    - Transaction cost accounting
    - Trade history tracking
    """
    
    MAX_CONCURRENT_POSITIONS = 3
    FEE_PER_ORDER = 24
    
    def __init__(self, initial_capital: float = 100000, student_roll: str = "23ME3EP03"):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions: Dict[Tuple[str, str], Position] = {}  # {(symbol, strategy): Position}
        self.trades_history: List[Trade] = []
        self.student_roll = student_roll
    
    def get_open_positions(self) -> List[Position]:
        """Get list of currently open positions."""
        return list(self.positions.values())
    
    def can_enter_position(self) -> bool:
        """Check if we can open a new position (max 3 concurrent)."""
        return len(self.positions) < self.MAX_CONCURRENT_POSITIONS
    
    def available_capital(self) -> float:
        """Get available cash for new positions."""
        return self.cash
    
    def total_portfolio_value(self, current_prices: Dict[str, float]) -> float:
        """Calculate total portfolio value (cash + positions)."""
        positions_value = sum(
            pos.current_value(current_prices.get(pos.symbol, pos.entry_price))
            for pos in self.positions.values()
        )
        return self.cash + positions_value
    
    def enter_position(self, symbol: str, strategy: str, timeframe: str,
                       timestamp: str, price: float, allocation_pct: float = 0.33) -> bool:
        """
        Enter a new position.
        
        Args:
            symbol: Trading symbol (e.g., "NSE:NIFTY50-INDEX")
            strategy: Strategy name (e.g., "RSI2" or "DONCHIAN")
            timeframe: Timeframe (e.g., "60" or "1D")
            timestamp: Entry time
            price: Entry price
            allocation_pct: Percentage of available capital to allocate
            
        Returns:
            True if position was entered, False otherwise
        """
        # Check global position limit
        if not self.can_enter_position():
            return False
        
        # Check if already in position for this symbol/strategy
        key = (symbol, strategy)
        if key in self.positions:
            return False
        
        # Calculate position size
        available = self.cash * allocation_pct - self.FEE_PER_ORDER
        if available <= 0:
            return False
        
        qty = int(available / price)
        if qty <= 0:
            return False
        
        # Deduct capital and fees
        cost = qty * price + self.FEE_PER_ORDER
        self.cash -= cost
        
        # Record position
        self.positions[key] = Position(
            symbol=symbol,
            strategy=strategy,
            entry_time=timestamp,
            entry_price=price,
            qty=qty
        )
        
        return True
    
    def close_position(self, symbol: str, strategy: str, timeframe: str,
                       timestamp: str, price: float, strategy_num: int = 1) -> Optional[Trade]:
        """
        Close an existing position.
        
        Args:
            symbol: Trading symbol
            strategy: Strategy name
            timeframe: Timeframe for submission
            timestamp: Exit time
            price: Exit price
            strategy_num: Strategy submission number (1 or 2)
            
        Returns:
            Trade object if position was closed, None otherwise
        """
        key = (symbol, strategy)
        if key not in self.positions:
            return None
        
        position = self.positions[key]
        
        # Add back position value minus exit fee
        self.cash += position.qty * price - self.FEE_PER_ORDER
        
        # Create trade record
        trade = Trade(
            student_roll_number=self.student_roll,
            strategy_submission_number=strategy_num,
            symbol=symbol,
            timeframe=timeframe,
            entry_trade_time=position.entry_time,
            exit_trade_time=timestamp,
            entry_trade_price=position.entry_price,
            exit_trade_price=price,
            qty=position.qty,
            fees=48,
            cumulative_capital_after_trade=round(self.cash, 2)
        )
        
        # Record trade and remove position
        self.trades_history.append(trade)
        del self.positions[key]
        
        return trade
    
    def get_trades_df(self) -> pd.DataFrame:
        """Get all trades as DataFrame."""
        if not self.trades_history:
            return pd.DataFrame()
        
        return pd.DataFrame([{
            'student_roll_number': t.student_roll_number,
            'strategy_submission_number': t.strategy_submission_number,
            'symbol': t.symbol,
            'timeframe': t.timeframe,
            'entry_trade_time': t.entry_trade_time,
            'exit_trade_time': t.exit_trade_time,
            'entry_trade_price': t.entry_trade_price,
            'exit_trade_price': t.exit_trade_price,
            'qty': t.qty,
            'fees': t.fees,
            'cumulative_capital_after_trade': t.cumulative_capital_after_trade
        } for t in self.trades_history])
    
    def get_metrics(self) -> dict:
        """Calculate portfolio performance metrics."""
        if not self.trades_history:
            return {'total_trades': 0}
        
        returns = []
        for trade in self.trades_history:
            ret = (trade.exit_trade_price - trade.entry_trade_price) / trade.entry_trade_price
            returns.append(ret)
        
        returns = np.array(returns)
        
        total_trades = len(self.trades_history)
        winning_trades = sum(1 for r in returns if r > 0)
        win_rate = winning_trades / total_trades * 100 if total_trades > 0 else 0
        total_return = (self.cash - self.initial_capital) / self.initial_capital * 100
        
        # Sharpe Ratio (simplified)
        if len(returns) > 1 and np.std(returns) > 0:
            sharpe = np.mean(returns) / np.std(returns) * np.sqrt(252)
        else:
            sharpe = 0
        
        # Max Drawdown
        cumulative = [self.initial_capital]
        for trade in self.trades_history:
            cumulative.append(trade.cumulative_capital_after_trade)
        cumulative = np.array(cumulative)
        peak = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - peak) / peak * 100
        max_dd = drawdown.min()
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': total_trades - winning_trades,
            'win_rate': round(win_rate, 2),
            'total_return': round(total_return, 2),
            'final_capital': round(self.cash, 2),
            'sharpe_ratio': round(sharpe, 2),
            'max_drawdown': round(max_dd, 2)
        }


def run_portfolio_backtest(symbols_data: Dict[str, pd.DataFrame],
                           strategies: List[callable],
                           config: dict) -> pd.DataFrame:
    """
    Run portfolio backtest across multiple symbols and strategies.
    
    Process all symbols/strategies on unified timeline with global position limits.
    
    Args:
        symbols_data: Dict of {symbol: DataFrame with signals}
        strategies: List of strategy names corresponding to signal columns
        config: Configuration dict with student_roll, timeframe, etc.
    
    Returns:
        DataFrame of all trades
    """
    # Step 1: Merge all timestamps
    all_timestamps = set()
    for symbol, df in symbols_data.items():
        all_timestamps.update(df['datetime'].tolist())
    
    timeline = sorted(all_timestamps)
    
    # Step 2: Initialize portfolio
    portfolio = PortfolioManager(
        initial_capital=config.get('initial_capital', 100000),
        student_roll=config.get('student_roll', '23ME3EP03')
    )
    
    # Step 3: Process chronologically
    for timestamp in timeline:
        # Check each symbol/strategy for signals at this timestamp
        for symbol, df in symbols_data.items():
            # Get row for this timestamp if exists
            row = df[df['datetime'] == timestamp]
            if len(row) == 0:
                continue
            
            row = row.iloc[0]
            price = row['close']
            signal = row.get('signal', 0)
            
            strategy = config.get('strategy_name', 'RSI2')
            strategy_num = config.get('strategy_num', 1)
            timeframe = config.get('timeframe', '60')
            
            # EXIT FIRST (check existing positions)
            if signal == -1:
                portfolio.close_position(
                    symbol=symbol,
                    strategy=strategy,
                    timeframe=timeframe,
                    timestamp=timestamp,
                    price=price,
                    strategy_num=strategy_num
                )
            
            # ENTRY (if signal and can open position)
            elif signal == 1:
                if portfolio.can_enter_position():
                    portfolio.enter_position(
                        symbol=symbol,
                        strategy=strategy,
                        timeframe=timeframe,
                        timestamp=timestamp,
                        price=price,
                        allocation_pct=0.33  # 33% per position (max 3 positions)
                    )
    
    return portfolio.get_trades_df(), portfolio.get_metrics()


# ============================================
# MAIN EXECUTION - Test
# ============================================

if __name__ == "__main__":
    print("=" * 60)
    print("PORTFOLIO MANAGER TEST")
    print("=" * 60)
    
    # Simple test
    pm = PortfolioManager(initial_capital=100000, student_roll="TEST123")
    
    print(f"Initial capital: ₹{pm.cash:,.2f}")
    print(f"Can enter position: {pm.can_enter_position()}")
    
    # Test entering position
    success = pm.enter_position(
        symbol="NSE:NIFTY50-INDEX",
        strategy="RSI2",
        timeframe="60",
        timestamp="2025-01-01 09:15:00",
        price=24000,
        allocation_pct=0.33
    )
    print(f"\nEntered position: {success}")
    print(f"Cash after entry: ₹{pm.cash:,.2f}")
    print(f"Open positions: {len(pm.get_open_positions())}")
    
    # Test closing position
    trade = pm.close_position(
        symbol="NSE:NIFTY50-INDEX",
        strategy="RSI2",
        timeframe="60",
        timestamp="2025-01-01 10:15:00",
        price=24100,
        strategy_num=1
    )
    print(f"\nClosed position: {trade is not None}")
    print(f"Cash after exit: ₹{pm.cash:,.2f}")
    print(f"Trade PnL: ₹{trade.net_pnl():.2f}" if trade else "No trade")
    
    # Print metrics
    metrics = pm.get_metrics()
    print(f"\nMetrics: {metrics}")
    print("=" * 60)
