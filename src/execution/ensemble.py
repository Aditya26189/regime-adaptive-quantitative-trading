"""
Ensemble Strategy Combiner.

Combines multiple signals using weighted voting for robust trading decisions.
Reduces reliance on single strategies that may fail in regime shifts.

Example:
    ensemble = EnsembleStrategy([
        (obi_signal, {'threshold': 0.3}),
        (z_score_signal, {'window': 20, 'entry_z': 2.0})
    ])
    signal = ensemble.get_signal(tick, history_df)
"""

from typing import List, Dict, Tuple, Callable, Optional, Any
import numpy as np
import pandas as pd


class EnsembleStrategy:
    """
    Combine multiple signal strategies using weighted voting.
    
    Aggregates signals from multiple strategies and returns a consensus
    signal when sufficient agreement is reached.
    
    Attributes:
        signal_funcs: List of (signal_function, params_dict) tuples
        weights: List of weights for each strategy (sum to 1.0)
        min_agreement: Minimum weighted vote for signal (default: 0.4)
    """
    
    def __init__(
        self,
        signal_funcs: List[Tuple[Callable, Dict[str, Any]]],
        weights: str | List[float] = 'equal',
        min_agreement: float = 0.4,
        risk_manager = None
    ):
        """
        Initialize ensemble strategy.
        
        Args:
            signal_funcs: List of (signal_function, params_dict) tuples.
                Each signal_function should accept (data, **params) and
                return a list of signals ('BUY', 'SELL', 'CLOSE', None).
            weights: 'equal', 'ic', or list of floats summing to 1.0
            min_agreement: Minimum weighted vote to generate signal
            risk_manager: Optional RiskManager for risk checks
            
        Example:
            ensemble = EnsembleStrategy(
                signal_funcs=[
                    (obi_signal, {'threshold': 0.3}),
                    (z_score_signal, {'window': 20})
                ],
                weights='equal'
            )
        """
        self.signal_funcs = signal_funcs
        self.risk_manager = risk_manager
        self.min_agreement = min_agreement
        self._precomputed_signals: List[List[Optional[str]]] = []
        
        # Set weights
        n = len(signal_funcs)
        if weights == 'equal':
            self.weights = [1.0 / n] * n
        elif isinstance(weights, list):
            if abs(sum(weights) - 1.0) > 0.01:
                raise ValueError("Weights must sum to 1.0")
            self.weights = weights
        else:
            self.weights = [1.0 / n] * n
    
    def precompute_signals(self, data: pd.DataFrame) -> None:
        """
        Precompute signals from all strategies for efficiency.
        
        Args:
            data: Full dataset to generate signals for
        """
        self._precomputed_signals = []
        
        for signal_func, params in self.signal_funcs:
            try:
                signals = signal_func(data, **params) if params else signal_func(data)
                self._precomputed_signals.append(signals)
            except Exception as e:
                # If signal function fails, use list of Nones
                print(f"Warning: Signal function failed: {e}")
                self._precomputed_signals.append([None] * len(data))
    
    def get_signal_at_index(
        self,
        index: int,
        current_position: int = 0,
        current_equity: float = 0
    ) -> Optional[str]:
        """
        Get aggregated signal at specific index using precomputed signals.
        
        Args:
            index: Index in precomputed signals
            current_position: Current position (for risk checks)
            current_equity: Current equity (for risk checks)
            
        Returns:
            'BUY', 'SELL', 'CLOSE', or None
        """
        if not self._precomputed_signals:
            return None
        
        votes = {'BUY': 0.0, 'SELL': 0.0, 'CLOSE': 0.0}
        
        for signals, weight in zip(self._precomputed_signals, self.weights):
            if index < len(signals):
                signal = signals[index]
                if signal in votes:
                    votes[signal] += weight
        
        # Find winner
        max_vote = max(votes.values())
        
        # Require minimum agreement
        if max_vote < self.min_agreement:
            return None
        
        winner = max(votes, key=votes.get)
        
        # Apply risk checks if available
        if self.risk_manager:
            if not self.risk_manager.can_trade(winner, current_position, current_equity):
                return None
        
        return winner
    
    def get_vote_distribution(self, index: int) -> Dict[str, float]:
        """
        Get vote distribution at index for debugging.
        
        Returns:
            Dict with vote percentages for each signal type
        """
        votes = {'BUY': 0.0, 'SELL': 0.0, 'CLOSE': 0.0, 'HOLD': 0.0}
        
        for signals, weight in zip(self._precomputed_signals, self.weights):
            if index < len(signals):
                signal = signals[index]
                if signal in votes:
                    votes[signal] += weight
                else:
                    votes['HOLD'] += weight
        
        return votes
    
    def get_strategy_info(self) -> str:
        """Get string representation of ensemble composition."""
        info_lines = ["Ensemble Strategy:"]
        
        for i, ((func, params), weight) in enumerate(zip(self.signal_funcs, self.weights)):
            func_name = func.__name__ if hasattr(func, '__name__') else str(func)
            info_lines.append(f"  [{i+1}] {func_name} (weight: {weight:.2%})")
            if params:
                for k, v in params.items():
                    info_lines.append(f"      - {k}: {v}")
        
        return "\n".join(info_lines)


def create_ic_weighted_ensemble(
    ic_results: Dict[str, Dict[str, Any]],
    signal_configs: List[Tuple[Callable, str, Dict[str, Any]]],
    min_ic: float = 0.03
) -> EnsembleStrategy:
    """
    Create ensemble weighted by IC values.
    
    Args:
        ic_results: Output from analyze_all_signals()
            Example: {
                'obi': {'ic': 0.12, ...},
                'z_score': {'ic': 0.08, ...}
            }
        signal_configs: List of (signal_function, signal_name, params_dict)
            Example: [
                (obi_signal, 'obi', {'threshold': 0.3}),
                (z_score_signal, 'z_score', {'window': 20})
            ]
        min_ic: Minimum IC to include signal in ensemble
        
    Returns:
        EnsembleStrategy with IC-weighted voting
        
    Example:
        from src.evaluation.signal_analysis import analyze_all_signals
        from src.signals.flow_based import obi_signal
        from src.signals.price_based import z_score_signal
        
        ic_results = analyze_all_signals(df)
        
        ensemble = create_ic_weighted_ensemble(
            ic_results,
            [
                (obi_signal, 'obi', {'threshold': 0.3}),
                (z_score_signal, 'z_score', {'window': 20})
            ]
        )
    """
    # Filter by minimum IC
    valid_configs = []
    ics = []
    
    for func, name, params in signal_configs:
        if name in ic_results:
            ic = abs(ic_results[name].get('ic', 0))
            if ic >= min_ic:
                valid_configs.append((func, params))
                ics.append(ic)
    
    if not valid_configs:
        raise ValueError("No signals meet minimum IC threshold")
    
    # Normalize ICs to weights
    total_ic = sum(ics)
    weights = [ic / total_ic for ic in ics]
    
    print("Creating IC-weighted ensemble:")
    for i, ((func, params), weight, ic) in enumerate(zip(valid_configs, weights, ics)):
        func_name = func.__name__ if hasattr(func, '__name__') else str(func)
        print(f"  [{i+1}] {func_name}: IC={ic:.4f}, weight={weight:.2%}")
    
    return EnsembleStrategy(valid_configs, weights=weights)


def create_top_n_ensemble(
    ic_results: Dict[str, Dict[str, Any]],
    signal_registry: Dict[str, Tuple[Callable, Dict[str, Any]]],
    n: int = 3
) -> EnsembleStrategy:
    """
    Create ensemble from top N signals by IC.
    
    Args:
        ic_results: Output from analyze_all_signals()
        signal_registry: Dict mapping signal names to (function, default_params)
        n: Number of top signals to include
        
    Returns:
        EnsembleStrategy with equal weights
    """
    # Sort signals by IC
    sorted_signals = sorted(
        ic_results.items(),
        key=lambda x: abs(x[1].get('ic', 0)),
        reverse=True
    )
    
    # Take top N that are in registry
    signal_funcs = []
    for signal_name, _ in sorted_signals[:n]:
        if signal_name in signal_registry:
            func, params = signal_registry[signal_name]
            signal_funcs.append((func, params))
    
    if not signal_funcs:
        raise ValueError("No matching signals found in registry")
    
    print(f"Creating ensemble from top {len(signal_funcs)} signals:")
    for i, (func, params) in enumerate(signal_funcs):
        func_name = func.__name__ if hasattr(func, '__name__') else str(func)
        print(f"  [{i+1}] {func_name}")
    
    return EnsembleStrategy(signal_funcs, weights='equal')


# Test code
if __name__ == '__main__':
    import sys
    from pathlib import Path
    
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    
    print("=" * 60)
    print("ENSEMBLE STRATEGY TEST")
    print("=" * 60)
    
    # Mock signal functions for testing
    def mock_bullish_signal(data, **params):
        """Always returns BUY."""
        return ['BUY'] * len(data)
    
    def mock_bearish_signal(data, **params):
        """Always returns SELL."""
        return ['SELL'] * len(data)
    
    def mock_neutral_signal(data, **params):
        """Always returns None."""
        return [None] * len(data)
    
    # Create test data
    import pandas as pd
    import numpy as np
    
    np.random.seed(42)
    df = pd.DataFrame({'mid': np.random.randn(100).cumsum() + 100})
    
    # Test 1: Equal weight with 2 bullish, 1 bearish
    print("\nTest 1: 2 bullish + 1 bearish (equal weights)")
    ensemble = EnsembleStrategy([
        (mock_bullish_signal, {}),
        (mock_bullish_signal, {}),
        (mock_bearish_signal, {})
    ], weights='equal')
    
    ensemble.precompute_signals(df)
    signal = ensemble.get_signal_at_index(50)
    votes = ensemble.get_vote_distribution(50)
    
    print(f"  Votes: {votes}")
    print(f"  Signal: {signal}")
    assert signal == 'BUY', "Should be BUY (2/3 vote)"
    print("  ✅ Passed")
    
    # Test 2: No consensus
    print("\nTest 2: No consensus (below threshold)")
    ensemble = EnsembleStrategy([
        (mock_bullish_signal, {}),
        (mock_bearish_signal, {}),
        (mock_neutral_signal, {})
    ], weights='equal', min_agreement=0.4)
    
    ensemble.precompute_signals(df)
    signal = ensemble.get_signal_at_index(50)
    votes = ensemble.get_vote_distribution(50)
    
    print(f"  Votes: {votes}")
    print(f"  Signal: {signal}")
    assert signal is None, "Should be None (no consensus)"
    print("  ✅ Passed")
    
    # Test 3: Custom weights
    print("\nTest 3: Custom weights (bearish has 60%)")
    ensemble = EnsembleStrategy([
        (mock_bullish_signal, {}),
        (mock_bearish_signal, {})
    ], weights=[0.4, 0.6])
    
    ensemble.precompute_signals(df)
    signal = ensemble.get_signal_at_index(50)
    votes = ensemble.get_vote_distribution(50)
    
    print(f"  Votes: {votes}")
    print(f"  Signal: {signal}")
    assert signal == 'SELL', "Should be SELL (60% weight)"
    print("  ✅ Passed")
    
    print("\n" + "=" * 60)
    print("✅ All ensemble tests passed!")
    print("=" * 60)
