"""
Event-driven backtester for tick-by-tick trading simulation.

This module provides a realistic backtesting engine that:
- Processes data one tick at a time (no lookahead bias)
- Applies transaction costs to all trades
- Implements circuit breakers on excessive drawdown
- Tracks full position and equity history
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd


@dataclass
class Trade:
    """
    Represents a single executed trade.
    
    Attributes:
        timestamp: The timestamp when the trade was executed
        side: Trade direction ('BUY' or 'SELL')
        price: Execution price
        quantity: Number of units traded
        fee: Transaction fee paid
    """
    timestamp: Any
    side: str
    price: float
    quantity: int
    fee: float


class Backtester:
    """
    Event-driven backtester that processes market data tick-by-tick.
    
    This backtester simulates realistic trading conditions including:
    - Transaction costs (maker/taker fees)
    - Position limits
    - Circuit breakers (halt trading on excessive drawdown)
    - Mark-to-market equity calculation
    
    Example:
        >>> bt = Backtester(initial_cash=100000, maker_fee=0.0002, taker_fee=0.0002)
        >>> for idx, tick in data.iterrows():
        ...     signal = strategy.get_signal(tick)
        ...     bt.process_tick(tick, signal)
        >>> results = bt.get_results()
    """
    
    def __init__(
        self,
        initial_cash: float = 100000.0,
        maker_fee: float = 0.0002,
        taker_fee: float = 0.0002,
        max_position: int = 100,
        max_drawdown: float = 0.15
    ):
        """
        Initialize the backtester.
        
        Args:
            initial_cash: Starting cash balance
            maker_fee: Fee rate for limit orders (as decimal)
            taker_fee: Fee rate for market orders (as decimal)
            max_position: Maximum allowed position (absolute value)
            max_drawdown: Maximum drawdown before circuit breaker triggers
        """
        self.initial_cash = initial_cash
        self.maker_fee = maker_fee
        self.taker_fee = taker_fee
        self.max_position = max_position
        self.max_drawdown = max_drawdown
        
        # State tracking
        self.cash: float = initial_cash
        self.position: int = 0
        self.equity_curve: List[float] = []
        self.position_curve: List[int] = []
        self.trades: List[Trade] = []
        self.timestamps: List[Any] = []
        self.peak_equity: float = initial_cash
        self.is_halted: bool = False
        
        # Track min/max position for reporting
        self._max_position_reached: int = 0
        self._min_position_reached: int = 0
    
    def _calculate_mid_price(self, tick: pd.Series) -> float:
        """
        Calculate the mid price from a tick.
        
        Supports multiple data formats:
        - OrderBook: (bid + ask) / 2
        - OHLCV: close price
        - Tick: price field
        """
        if 'bid' in tick.index and 'ask' in tick.index:
            return (tick['bid'] + tick['ask']) / 2
        elif 'close' in tick.index:
            return tick['close']
        elif 'mid' in tick.index:
            return tick['mid']
        elif 'price' in tick.index:
            return tick['price']
        else:
            raise ValueError("Cannot determine mid price from tick data")
    
    def _calculate_equity(self, mid_price: float) -> float:
        """Calculate current equity (mark-to-market)."""
        return self.cash + self.position * mid_price
    
    def _check_circuit_breaker(self, current_equity: float) -> bool:
        """
        Check if drawdown exceeds threshold.
        
        Returns:
            True if circuit breaker should trigger
        """
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity
        
        if self.peak_equity > 0:
            drawdown = (self.peak_equity - current_equity) / self.peak_equity
            if drawdown > self.max_drawdown:
                return True
        return False
    
    def _execute_buy(
        self,
        price: float,
        qty: int,
        timestamp: Any
    ) -> Optional[Trade]:
        """
        Execute a buy order.
        
        Args:
            price: Execution price (typically ask price)
            qty: Quantity to buy
            timestamp: Timestamp of the trade
            
        Returns:
            Trade object if executed, None otherwise
        """
        if qty <= 0:
            return None
        
        # Check position limit
        if self.position + qty > self.max_position:
            qty = self.max_position - self.position
            if qty <= 0:
                return None
        
        # Calculate cost including fees
        gross_cost = price * qty
        fee = gross_cost * self.taker_fee
        total_cost = gross_cost + fee
        
        # Check if we have enough cash
        if total_cost > self.cash:
            # Reduce quantity to what we can afford
            max_qty = int(self.cash / (price * (1 + self.taker_fee)))
            if max_qty <= 0:
                return None
            qty = max_qty
            gross_cost = price * qty
            fee = gross_cost * self.taker_fee
            total_cost = gross_cost + fee
        
        # Execute trade
        self.cash -= total_cost
        self.position += qty
        
        # Track position extremes
        self._max_position_reached = max(self._max_position_reached, self.position)
        
        trade = Trade(
            timestamp=timestamp,
            side='BUY',
            price=price,
            quantity=qty,
            fee=fee
        )
        self.trades.append(trade)
        
        return trade
    
    def _execute_sell(
        self,
        price: float,
        qty: int,
        timestamp: Any
    ) -> Optional[Trade]:
        """
        Execute a sell order.
        
        Args:
            price: Execution price (typically bid price)
            qty: Quantity to sell
            timestamp: Timestamp of the trade
            
        Returns:
            Trade object if executed, None otherwise
        """
        if qty <= 0:
            return None
        
        # Check position limit (for short positions)
        if self.position - qty < -self.max_position:
            qty = self.position + self.max_position
            if qty <= 0:
                return None
        
        # Calculate proceeds including fees
        gross_proceeds = price * qty
        fee = gross_proceeds * self.taker_fee
        net_proceeds = gross_proceeds - fee
        
        # Execute trade
        self.cash += net_proceeds
        self.position -= qty
        
        # Track position extremes
        self._min_position_reached = min(self._min_position_reached, self.position)
        
        trade = Trade(
            timestamp=timestamp,
            side='SELL',
            price=price,
            quantity=qty,
            fee=fee
        )
        self.trades.append(trade)
        
        return trade
    
    def _close_position(
        self,
        tick: pd.Series,
        timestamp: Any
    ) -> Optional[Trade]:
        """
        Close the current position.
        
        Returns:
            Trade object if executed, None otherwise
        """
        if self.position == 0:
            return None
        
        if self.position > 0:
            # Sell to close long position
            price = tick.get('bid', self._calculate_mid_price(tick))
            return self._execute_sell(price, self.position, timestamp)
        else:
            # Buy to close short position
            price = tick.get('ask', self._calculate_mid_price(tick))
            return self._execute_buy(price, abs(self.position), timestamp)
    
    def process_tick(
        self,
        tick: pd.Series,
        signal: Optional[str],
        trade_qty: int = 1
    ) -> None:
        """
        Process a single tick of market data.
        
        This is the main entry point for the event-driven backtest.
        Call this method for each row in your market data.
        
        Args:
            tick: Single row of market data (pd.Series)
            signal: Trading signal ('BUY', 'SELL', 'CLOSE', or None)
            trade_qty: Quantity to trade (default 1)
        """
        # Get mid price for equity calculation
        mid_price = self._calculate_mid_price(tick)
        
        # Calculate current equity
        current_equity = self._calculate_equity(mid_price)
        
        # Check circuit breaker
        if self._check_circuit_breaker(current_equity):
            self.is_halted = True
        
        # Get timestamp
        timestamp = tick.get('timestamp', tick.name)
        
        # Execute signal if not halted
        if not self.is_halted and signal is not None:
            if signal == 'BUY':
                price = tick.get('ask', mid_price)
                self._execute_buy(price, trade_qty, timestamp)
            elif signal == 'SELL':
                price = tick.get('bid', mid_price)
                self._execute_sell(price, trade_qty, timestamp)
            elif signal == 'CLOSE':
                self._close_position(tick, timestamp)
        
        # Record state after processing
        final_equity = self._calculate_equity(mid_price)
        self.equity_curve.append(final_equity)
        self.position_curve.append(self.position)
        self.timestamps.append(timestamp)
    
    def get_results(self) -> Dict[str, Any]:
        """
        Get complete backtest results.
        
        Returns:
            Dictionary containing:
            - final_equity: Ending equity value
            - total_pnl: Total profit/loss
            - total_return: Percentage return
            - num_trades: Number of trades executed
            - final_position: Ending position
            - max_position: Maximum position reached
            - min_position: Minimum position reached
            - was_halted: Whether circuit breaker triggered
            - equity_curve: Array of equity values
            - position_curve: Array of position values
            - returns: Array of period returns
            - trades: List of Trade objects
            - trades_df: DataFrame of trades with cumulative PnL
        """
        equity_array = np.array(self.equity_curve)
        
        # Calculate returns
        if len(equity_array) > 1:
            returns = np.diff(equity_array) / equity_array[:-1]
            # Prepend 0 for first period
            returns = np.concatenate([[0], returns])
        else:
            returns = np.array([0])
        
        final_equity = equity_array[-1] if len(equity_array) > 0 else self.initial_cash
        total_pnl = final_equity - self.initial_cash
        total_return = total_pnl / self.initial_cash if self.initial_cash > 0 else 0
        
        # Create trades DataFrame with cumulative PnL
        trades_df = self._create_trades_df()
        
        return {
            'final_equity': final_equity,
            'total_pnl': total_pnl,
            'total_return': total_return,
            'num_trades': len(self.trades),
            'final_position': self.position,
            'max_position': self._max_position_reached,
            'min_position': self._min_position_reached,
            'was_halted': self.is_halted,
            'equity_curve': equity_array,
            'position_curve': np.array(self.position_curve),
            'returns': returns,
            'trades': self.trades,
            'trades_df': trades_df,
            'timestamps': self.timestamps
        }
    
    def _create_trades_df(self) -> pd.DataFrame:
        """
        Convert trades list to DataFrame with cumulative PnL.
        
        Returns:
            DataFrame with columns: timestamp, side, price, quantity, fee, pnl, cumulative_pnl
        """
        if not self.trades:
            return pd.DataFrame(columns=[
                'timestamp', 'side', 'price', 'quantity', 'fee', 'pnl', 'cumulative_pnl'
            ])
        
        trades_data = []
        cumulative_pnl = 0.0
        avg_entry_price = 0.0
        position = 0
        
        for trade in self.trades:
            pnl = 0.0
            
            if trade.side == 'BUY':
                # Buying - if we're short, this closes short; otherwise opens long
                if position < 0:
                    # Closing short position
                    close_qty = min(trade.quantity, abs(position))
                    pnl = (avg_entry_price - trade.price) * close_qty - trade.fee
                    remaining_qty = trade.quantity - close_qty
                    if remaining_qty > 0:
                        avg_entry_price = trade.price
                    position += trade.quantity
                else:
                    # Opening or adding to long
                    total_value = avg_entry_price * position + trade.price * trade.quantity
                    position += trade.quantity
                    avg_entry_price = total_value / position if position > 0 else 0
                    pnl = -trade.fee
            else:  # SELL
                # Selling - if we're long, this closes long; otherwise opens short
                if position > 0:
                    # Closing long position
                    close_qty = min(trade.quantity, position)
                    pnl = (trade.price - avg_entry_price) * close_qty - trade.fee
                    remaining_qty = trade.quantity - close_qty
                    if remaining_qty > 0:
                        avg_entry_price = trade.price
                    position -= trade.quantity
                else:
                    # Opening or adding to short
                    total_value = avg_entry_price * abs(position) + trade.price * trade.quantity
                    position -= trade.quantity
                    avg_entry_price = total_value / abs(position) if position != 0 else 0
                    pnl = -trade.fee
            
            cumulative_pnl += pnl
            
            trades_data.append({
                'timestamp': trade.timestamp,
                'side': trade.side,
                'price': round(trade.price, 4),
                'quantity': trade.quantity,
                'fee': round(trade.fee, 6),
                'pnl': round(pnl, 4),
                'cumulative_pnl': round(cumulative_pnl, 4)
            })
        
        df = pd.DataFrame(trades_data)
        return df.sort_values('timestamp').reset_index(drop=True)
    
    def save_trades(self, filepath: str) -> None:
        """
        Export trades to CSV file.
        
        Args:
            filepath: Path to save the trades CSV
        """
        trades_df = self._create_trades_df()
        trades_df.to_csv(filepath, index=False)
        print(f"  ✓ Saved {len(trades_df)} trades to {filepath}")
    
    def reset(self) -> None:
        """Reset the backtester to initial state."""
        self.cash = self.initial_cash
        self.position = 0
        self.equity_curve = []
        self.position_curve = []
        self.trades = []
        self.timestamps = []
        self.peak_equity = self.initial_cash
        self.is_halted = False
        self._max_position_reached = 0
        self._min_position_reached = 0
