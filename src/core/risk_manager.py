"""
Risk management module for trading decisions.

This module provides a RiskManager class that gates all trading decisions
through position limits, drawdown thresholds, and volatility filters.
All risk checks must pass before a trade is allowed.
"""

from typing import List, Optional
import numpy as np


class RiskManager:
    """
    Risk manager that gates all trading decisions.
    
    Every trade must pass through the risk manager's checks:
    1. Drawdown check: Prevent trading if portfolio drawdown is too high
    2. Position limit check: Enforce maximum position constraints
    3. Volatility check: Reduce trading during high volatility periods
    
    Example:
        >>> rm = RiskManager(max_position=100, max_drawdown=0.15)
        >>> if rm.can_trade('BUY', current_position=50, current_equity=100000):
        ...     execute_trade()
    """
    
    def __init__(
        self,
        max_position: int = 100,
        max_drawdown: float = 0.15,
        vol_threshold: float = 0.01,
        vol_window: int = 100
    ):
        """
        Initialize the risk manager.
        
        Args:
            max_position: Maximum allowed position (absolute value)
            max_drawdown: Maximum drawdown before halting (as decimal)
            vol_threshold: Maximum volatility threshold for trading
            vol_window: Window size for volatility calculation
        """
        self.max_position = max_position
        self.max_drawdown = max_drawdown
        self.vol_threshold = vol_threshold
        self.vol_window = vol_window
        
        # State tracking
        self.peak_equity: float = 0.0
        self.returns_history: List[float] = []
        self.is_halted: bool = False
    
    def update_peak_equity(self, current_equity: float) -> None:
        """
        Update the peak equity value.
        
        Args:
            current_equity: Current portfolio equity
        """
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity
    
    def add_return(self, period_return: float) -> None:
        """
        Add a return to the history for volatility calculation.
        
        Args:
            period_return: Return for the current period
        """
        self.returns_history.append(period_return)
        # Keep only the most recent returns within the window
        if len(self.returns_history) > self.vol_window:
            self.returns_history = self.returns_history[-self.vol_window:]
    
    def _check_drawdown(self, current_equity: float) -> bool:
        """
        Check if current drawdown is within acceptable limits.
        
        Args:
            current_equity: Current portfolio equity
            
        Returns:
            True if drawdown is acceptable, False if exceeded
        """
        # Update peak equity
        self.update_peak_equity(current_equity)
        
        if self.peak_equity <= 0:
            return True  # No valid peak equity yet
        
        drawdown = (self.peak_equity - current_equity) / self.peak_equity
        
        if drawdown > self.max_drawdown:
            self.is_halted = True
            return False
        
        return True
    
    def _check_position_limit(self, signal: str, current_position: int) -> bool:
        """
        Check if the proposed trade respects position limits.
        
        Args:
            signal: Trading signal ('BUY', 'SELL', 'CLOSE')
            current_position: Current position
            
        Returns:
            True if trade is allowed, False otherwise
        """
        if signal == 'CLOSE':
            return True  # Always allow closing positions
        
        if signal == 'BUY' and current_position >= self.max_position:
            return False  # Already at max long position
        
        if signal == 'SELL' and current_position <= -self.max_position:
            return False  # Already at max short position
        
        return True
    
    def _check_volatility(self) -> bool:
        """
        Check if current volatility is within acceptable limits.
        
        Returns:
            True if volatility is acceptable, False if too high
        """
        if len(self.returns_history) < 2:
            return True  # Not enough data to calculate volatility
        
        recent_vol = np.std(self.returns_history)
        
        if recent_vol > self.vol_threshold:
            return False  # Volatility too high, don't trade
        
        return True
    
    def can_trade(
        self,
        signal: str,
        current_position: int,
        current_equity: float,
        current_return: Optional[float] = None
    ) -> bool:
        """
        Determine if a trade can be executed given current risk state.
        
        All checks must pass for the trade to be allowed:
        1. Not halted due to drawdown
        2. Position limits respected
        3. Volatility within threshold
        
        Args:
            signal: Trading signal ('BUY', 'SELL', 'CLOSE', or None)
            current_position: Current position
            current_equity: Current portfolio equity
            current_return: Optional return for the current period
            
        Returns:
            True if trade is allowed, False otherwise
        """
        if signal is None:
            return False  # No signal, no trade
        
        # Update return history if provided
        if current_return is not None:
            self.add_return(current_return)
        
        # Check 1: Drawdown circuit breaker
        if not self._check_drawdown(current_equity):
            return False
        
        # Check 2: Position limits
        if not self._check_position_limit(signal, current_position):
            return False
        
        # Check 3: Volatility filter
        if not self._check_volatility():
            return False
        
        return True
    
    def get_max_trade_size(self, current_position: int, signal: str) -> int:
        """
        Calculate the maximum allowed trade size given current position.
        
        Args:
            current_position: Current position
            signal: Trading signal ('BUY' or 'SELL')
            
        Returns:
            Maximum number of units that can be traded
        """
        if signal == 'BUY':
            return max(0, self.max_position - current_position)
        elif signal == 'SELL':
            return max(0, self.max_position + current_position)
        else:
            return abs(current_position)  # For CLOSE signal
    
    def get_current_drawdown(self, current_equity: float) -> float:
        """
        Calculate current drawdown from peak.
        
        Args:
            current_equity: Current portfolio equity
            
        Returns:
            Current drawdown as a decimal (0.0 to 1.0)
        """
        if self.peak_equity <= 0:
            return 0.0
        
        return max(0, (self.peak_equity - current_equity) / self.peak_equity)
    
    def get_current_volatility(self) -> float:
        """
        Calculate current rolling volatility.
        
        Returns:
            Current volatility of returns history
        """
        if len(self.returns_history) < 2:
            return 0.0
        
        return float(np.std(self.returns_history))
    
    def reset(self) -> None:
        """Reset the risk manager state."""
        self.peak_equity = 0.0
        self.returns_history = []
        self.is_halted = False
