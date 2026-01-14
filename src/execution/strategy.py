"""
Strategy combiner module.

This module provides the Strategy class that combines signal generators
with risk management and regime filters into a complete trading strategy.
"""

from typing import Callable, Optional, Any, List
import pandas as pd
import numpy as np

from ..core.risk_manager import RiskManager


class Strategy:
    """
    Combines signals with risk gates and regime filters.
    
    A Strategy takes a signal generation function, passes its output
    through risk management checks and optional regime filters, and
    returns the final trading decision.
    
    Example:
        >>> from src.signals.price_based import z_score_signal
        >>> risk_manager = RiskManager(max_position=100)
        >>> strategy = Strategy(z_score_signal, risk_manager)
        >>> signal = strategy.get_signal(tick, history)
    """
    
    def __init__(
        self,
        signal_func: Callable,
        risk_manager: RiskManager,
        regime_filter: Optional[Callable] = None,
        signal_params: Optional[dict] = None
    ):
        """
        Initialize the strategy.
        
        Args:
            signal_func: Function that generates signals from data
            risk_manager: RiskManager instance for risk checks
            regime_filter: Optional function that takes regime string and returns bool
            signal_params: Optional kwargs to pass to signal_func
        """
        self.signal_func = signal_func
        self.risk_manager = risk_manager
        self.regime_filter = regime_filter
        self.signal_params = signal_params or {}
        
        # Cache for precomputed signals
        self._cached_signals: Optional[List[Optional[str]]] = None
        self._cache_valid: bool = False
    
    def precompute_signals(self, data: pd.DataFrame) -> List[Optional[str]]:
        """
        Precompute all signals for a dataset.
        
        This is more efficient than computing signals tick-by-tick.
        
        Args:
            data: Full DataFrame to generate signals for
            
        Returns:
            List of signals for all rows
        """
        self._cached_signals = self.signal_func(data, **self.signal_params)
        self._cache_valid = True
        return self._cached_signals
    
    def get_signal_at_index(
        self,
        index: int,
        current_position: int,
        current_equity: float,
        current_return: Optional[float] = None,
        regime: Optional[str] = None
    ) -> Optional[str]:
        """
        Get the signal at a specific index from precomputed signals.
        
        Args:
            index: Index in the data
            current_position: Current position size
            current_equity: Current portfolio equity
            current_return: Optional return for volatility calculation
            regime: Optional regime string for filtering
            
        Returns:
            Trading signal ('BUY', 'SELL', 'CLOSE', or None)
        """
        if not self._cache_valid or self._cached_signals is None:
            raise ValueError("Signals not precomputed. Call precompute_signals first.")
        
        if index < 0 or index >= len(self._cached_signals):
            return None
        
        base_signal = self._cached_signals[index]
        
        return self._apply_filters(
            base_signal,
            current_position,
            current_equity,
            current_return,
            regime
        )
    
    def get_signal(
        self,
        tick: pd.Series,
        history: pd.DataFrame,
        current_position: int = 0,
        current_equity: float = 0.0,
        current_return: Optional[float] = None,
        regime: Optional[str] = None
    ) -> Optional[str]:
        """
        Get trading signal for current tick.
        
        This method:
        1. Generates base signal from signal_func
        2. Applies regime filter (if provided)
        3. Checks risk manager constraints
        4. Returns final decision
        
        Args:
            tick: Current tick data (pd.Series)
            history: Historical data up to current tick (for signal calculation)
            current_position: Current position size
            current_equity: Current portfolio equity
            current_return: Optional return for volatility calculation
            regime: Optional regime string for filtering
            
        Returns:
            Trading signal ('BUY', 'SELL', 'CLOSE', or None)
        """
        # Generate base signal
        # Add current tick to history for signal calculation
        full_data = pd.concat([history, tick.to_frame().T], ignore_index=True)
        signals = self.signal_func(full_data, **self.signal_params)
        
        # Get the last signal (for current tick)
        base_signal = signals[-1] if signals else None
        
        return self._apply_filters(
            base_signal,
            current_position,
            current_equity,
            current_return,
            regime
        )
    
    def _apply_filters(
        self,
        base_signal: Optional[str],
        current_position: int,
        current_equity: float,
        current_return: Optional[float] = None,
        regime: Optional[str] = None
    ) -> Optional[str]:
        """
        Apply regime filter and risk checks to a base signal.
        
        Args:
            base_signal: Raw signal from signal function
            current_position: Current position size
            current_equity: Current portfolio equity
            current_return: Optional return for volatility calculation
            regime: Optional regime string for filtering
            
        Returns:
            Filtered signal or None
        """
        if base_signal is None:
            return None
        
        # Apply regime filter
        if self.regime_filter is not None and regime is not None:
            if not self.regime_filter(regime):
                # Regime filter rejects trading
                return None
        
        # Check risk manager
        if not self.risk_manager.can_trade(
            signal=base_signal,
            current_position=current_position,
            current_equity=current_equity,
            current_return=current_return
        ):
            return None
        
        return base_signal
    
    def get_trade_size(
        self,
        signal: str,
        current_position: int,
        max_size: int = 1
    ) -> int:
        """
        Determine the trade size for a signal.
        
        Args:
            signal: Trading signal ('BUY', 'SELL', 'CLOSE')
            current_position: Current position
            max_size: Maximum trade size desired
            
        Returns:
            Actual trade size respecting risk limits
        """
        max_allowed = self.risk_manager.get_max_trade_size(current_position, signal)
        return min(max_size, max_allowed)
    
    def reset(self) -> None:
        """Reset the strategy state."""
        self._cached_signals = None
        self._cache_valid = False
        self.risk_manager.reset()


class CompositeStrategy:
    """
    Combines multiple strategies using voting or priority rules.
    
    Example:
        >>> strat1 = Strategy(z_score_signal, rm)
        >>> strat2 = Strategy(obi_signal, rm)
        >>> composite = CompositeStrategy([strat1, strat2], method='majority')
    """
    
    def __init__(
        self,
        strategies: List[Strategy],
        method: str = 'majority',
        weights: Optional[List[float]] = None
    ):
        """
        Initialize composite strategy.
        
        Args:
            strategies: List of Strategy objects
            method: Combination method ('majority', 'unanimous', 'first', 'weighted')
            weights: Optional weights for weighted voting
        """
        self.strategies = strategies
        self.method = method
        self.weights = weights or [1.0] * len(strategies)
    
    def precompute_signals(self, data: pd.DataFrame) -> None:
        """Precompute signals for all strategies."""
        for strategy in self.strategies:
            strategy.precompute_signals(data)
    
    def get_signal_at_index(
        self,
        index: int,
        current_position: int,
        current_equity: float,
        current_return: Optional[float] = None,
        regime: Optional[str] = None
    ) -> Optional[str]:
        """
        Get combined signal at a specific index.
        
        Args:
            index: Data index
            current_position: Current position
            current_equity: Current equity
            current_return: Optional return
            regime: Optional regime
            
        Returns:
            Combined trading signal
        """
        signals = []
        for strategy in self.strategies:
            sig = strategy.get_signal_at_index(
                index, current_position, current_equity, current_return, regime
            )
            signals.append(sig)
        
        return self._combine_signals(signals)
    
    def _combine_signals(self, signals: List[Optional[str]]) -> Optional[str]:
        """
        Combine signals according to the specified method.
        
        Args:
            signals: List of signals from all strategies
            
        Returns:
            Combined signal
        """
        # Filter out None signals
        valid_signals = [(s, w) for s, w in zip(signals, self.weights) if s is not None]
        
        if not valid_signals:
            return None
        
        if self.method == 'first':
            # Return first non-None signal
            return valid_signals[0][0]
        
        elif self.method == 'unanimous':
            # All must agree
            signal_values = set(s for s, w in valid_signals)
            if len(signal_values) == 1:
                return valid_signals[0][0]
            return None
        
        elif self.method == 'majority':
            # Majority vote
            buy_count = sum(1 for s, w in valid_signals if s == 'BUY')
            sell_count = sum(1 for s, w in valid_signals if s == 'SELL')
            close_count = sum(1 for s, w in valid_signals if s == 'CLOSE')
            
            max_count = max(buy_count, sell_count, close_count)
            
            if max_count == 0:
                return None
            
            if buy_count == max_count:
                return 'BUY'
            elif sell_count == max_count:
                return 'SELL'
            else:
                return 'CLOSE'
        
        elif self.method == 'weighted':
            # Weighted vote
            buy_weight = sum(w for s, w in valid_signals if s == 'BUY')
            sell_weight = sum(w for s, w in valid_signals if s == 'SELL')
            close_weight = sum(w for s, w in valid_signals if s == 'CLOSE')
            
            max_weight = max(buy_weight, sell_weight, close_weight)
            
            if max_weight == 0:
                return None
            
            if buy_weight == max_weight:
                return 'BUY'
            elif sell_weight == max_weight:
                return 'SELL'
            else:
                return 'CLOSE'
        
        return None
    
    def reset(self) -> None:
        """Reset all strategies."""
        for strategy in self.strategies:
            strategy.reset()
