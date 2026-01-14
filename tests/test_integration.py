#!/usr/bin/env python
"""
Integration test for the quantitative trading infrastructure.

This test validates that all components work together correctly
using synthetic market data.

Run with:
    python tests/test_integration.py
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import pandas as pd
import tempfile
import shutil


def generate_synthetic_data(n_rows: int = 1000, seed: int = 42) -> pd.DataFrame:
    """
    Generate synthetic market data for testing.
    
    Creates order book style data with:
    - Timestamp
    - Bid/Ask prices (with random walk)
    - Bid/Ask quantities
    
    Args:
        n_rows: Number of data rows to generate
        seed: Random seed for reproducibility
        
    Returns:
        DataFrame with synthetic market data
    """
    np.random.seed(seed)
    
    # Generate price with random walk
    base_price = 100.0
    price_changes = np.random.randn(n_rows) * 0.1
    mid_prices = base_price + np.cumsum(price_changes)
    
    # Generate bid/ask with spread
    spread = 0.01 + np.abs(np.random.randn(n_rows) * 0.005)
    bid_prices = mid_prices - spread / 2
    ask_prices = mid_prices + spread / 2
    
    # Generate quantities
    bid_qty = np.random.randint(100, 1000, n_rows)
    ask_qty = np.random.randint(100, 1000, n_rows)
    
    df = pd.DataFrame({
        'timestamp': range(n_rows),
        'bid': bid_prices,
        'ask': ask_prices,
        'bid_qty': bid_qty,
        'ask_qty': ask_qty
    })
    
    return df


def test_data_loader():
    """Test DataLoader functionality."""
    print("\n--- Testing DataLoader ---")
    
    from src.data.loader import DataLoader
    
    # Create temp file with synthetic data
    df = generate_synthetic_data(100)
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        df.to_csv(f.name, index=False)
        temp_path = f.name
    
    try:
        loader = DataLoader(verbose=False)
        
        # Test loading
        loaded_df = loader.load_csv(temp_path)
        assert len(loaded_df) == 100, "Row count mismatch"
        print("  ✓ CSV loading works")
        
        # Test schema detection
        schema = loader.detect_schema(loaded_df)
        assert schema == 'OrderBook', f"Expected OrderBook, got {schema}"
        print("  ✓ Schema detection works")
        
        # Test validation
        valid = loader.validate(loaded_df)
        assert valid, "Validation should pass"
        print("  ✓ Validation works")
        
        # Test mid price
        df_mid = loader.add_mid_price(loaded_df)
        assert 'mid' in df_mid.columns, "Mid price not added"
        print("  ✓ Mid price calculation works")
        
    finally:
        os.unlink(temp_path)
    
    print("  ✓ DataLoader tests passed")


def test_feature_engine():
    """Test FeatureEngine functionality."""
    print("\n--- Testing FeatureEngine ---")
    
    from src.data.features import FeatureEngine
    
    df = generate_synthetic_data(200)
    df['mid'] = (df['bid'] + df['ask']) / 2
    
    engine = FeatureEngine(verbose=False)
    
    # Test returns
    df_ret = engine.add_returns(df)
    assert 'returns' in df_ret.columns, "Returns not added"
    print("  ✓ Returns calculation works")
    
    # Test volatility
    df_vol = engine.add_volatility(df_ret)
    assert 'volatility' in df_vol.columns, "Volatility not added"
    print("  ✓ Volatility calculation works")
    
    # Test OBI
    df_obi = engine.add_obi(df)
    assert 'obi' in df_obi.columns, "OBI not added"
    assert df_obi['obi'].min() >= -1 and df_obi['obi'].max() <= 1, "OBI out of range"
    print("  ✓ OBI calculation works")
    
    # Test microprice
    df_mp = engine.add_microprice(df)
    assert 'microprice' in df_mp.columns, "Microprice not added"
    print("  ✓ Microprice calculation works")
    
    # Test z-score
    df_z = engine.add_z_score(df)
    assert 'z_score' in df_z.columns, "Z-score not added"
    print("  ✓ Z-score calculation works")
    
    # Test add_all
    df_all = engine.add_all(df)
    assert len(df_all.columns) > len(df.columns), "Features not added"
    print("  ✓ Add all features works")
    
    print("  ✓ FeatureEngine tests passed")


def test_signals():
    """Test signal generators."""
    print("\n--- Testing Signals ---")
    
    from src.signals.price_based import z_score_signal, momentum_signal
    from src.signals.flow_based import obi_signal
    from src.signals.regime_based import volatility_regime
    
    df = generate_synthetic_data(200)
    df['mid'] = (df['bid'] + df['ask']) / 2
    df['obi'] = (df['bid_qty'] - df['ask_qty']) / (df['bid_qty'] + df['ask_qty'])
    
    # Test z-score signal
    z_signals = z_score_signal(df, window=20, entry_z=1.5, exit_z=0.5)
    assert len(z_signals) == len(df), "Z-score signal length mismatch"
    assert all(s in [None, 'BUY', 'SELL', 'CLOSE'] for s in z_signals), "Invalid signal values"
    print("  ✓ Z-score signal works")
    
    # Test momentum signal
    mom_signals = momentum_signal(df, fast_ma=5, slow_ma=20)
    assert len(mom_signals) == len(df), "Momentum signal length mismatch"
    print("  ✓ Momentum signal works")
    
    # Test OBI signal
    obi_signals = obi_signal(df, threshold=0.3)
    assert len(obi_signals) == len(df), "OBI signal length mismatch"
    print("  ✓ OBI signal works")
    
    # Test regime
    regimes = volatility_regime(df)
    assert len(regimes) == len(df), "Regime length mismatch"
    assert all(r in ['CALM', 'NORMAL', 'VOLATILE'] for r in regimes), "Invalid regime values"
    print("  ✓ Regime classifier works")
    
    print("  ✓ Signals tests passed")


def test_risk_manager():
    """Test RiskManager functionality."""
    print("\n--- Testing RiskManager ---")
    
    from src.core.risk_manager import RiskManager
    
    rm = RiskManager(
        max_position=100,
        max_drawdown=0.15,
        vol_threshold=0.02,
        vol_window=20
    )
    
    # Test position limits
    assert rm.can_trade('BUY', 50, 100000), "Should allow buying"
    assert not rm.can_trade('BUY', 100, 100000), "Should block at max position"
    assert rm.can_trade('SELL', 100, 100000), "Should allow selling from max long"
    print("  ✓ Position limits work")
    
    # Test drawdown check
    rm.peak_equity = 100000
    assert rm.can_trade('BUY', 0, 95000), "Should allow trading at 5% drawdown"
    
    rm2 = RiskManager(max_position=100, max_drawdown=0.10)
    rm2.peak_equity = 100000
    assert not rm2.can_trade('BUY', 0, 85000), "Should block at 15% drawdown"
    print("  ✓ Drawdown check works")
    
    # Test trade size calculation
    max_buy = rm.get_max_trade_size(50, 'BUY')
    assert max_buy == 50, f"Expected 50, got {max_buy}"
    print("  ✓ Trade size calculation works")
    
    print("  ✓ RiskManager tests passed")


def test_backtester():
    """Test Backtester functionality."""
    print("\n--- Testing Backtester ---")
    
    from src.core.backtester import Backtester
    
    bt = Backtester(
        initial_cash=100000,
        maker_fee=0.0002,
        taker_fee=0.0002,
        max_position=100,
        max_drawdown=0.15
    )
    
    # Create simple test data
    df = generate_synthetic_data(100)
    df['mid'] = (df['bid'] + df['ask']) / 2
    
    # Process some ticks
    for i in range(50):
        tick = df.iloc[i]
        signal = 'BUY' if i % 20 == 0 else ('SELL' if i % 20 == 10 else None)
        bt.process_tick(tick, signal)
    
    # Check state
    assert len(bt.equity_curve) == 50, "Equity curve length mismatch"
    assert len(bt.position_curve) == 50, "Position curve length mismatch"
    print("  ✓ Tick processing works")
    
    # Get results
    results = bt.get_results()
    assert 'final_equity' in results, "Missing final_equity"
    assert 'equity_curve' in results, "Missing equity_curve"
    assert 'trades' in results, "Missing trades"
    assert 'returns' in results, "Missing returns"
    print("  ✓ Results generation works")
    
    # Check for valid values
    assert np.isfinite(results['final_equity']), "Final equity not finite"
    assert len(results['equity_curve']) == 50, "Equity curve length wrong"
    print("  ✓ Results values are valid")
    
    print("  ✓ Backtester tests passed")


def test_metrics():
    """Test MetricsCalculator functionality."""
    print("\n--- Testing MetricsCalculator ---")
    
    from src.core.metrics import MetricsCalculator
    
    # Generate test equity curve
    np.random.seed(42)
    equity = 100000 + np.cumsum(np.random.randn(1000) * 100)
    
    # Test individual metrics
    returns = np.diff(equity) / equity[:-1]
    
    sharpe = MetricsCalculator.sharpe_ratio(returns)
    assert np.isfinite(sharpe), "Sharpe ratio not finite"
    print(f"  ✓ Sharpe ratio: {sharpe:.4f}")
    
    sortino = MetricsCalculator.sortino_ratio(returns)
    assert np.isfinite(sortino), "Sortino ratio not finite"
    print(f"  ✓ Sortino ratio: {sortino:.4f}")
    
    max_dd = MetricsCalculator.max_drawdown(equity)
    assert max_dd <= 0, "Max drawdown should be negative or zero"
    assert max_dd >= -1, "Max drawdown should be >= -1"
    print(f"  ✓ Max drawdown: {max_dd:.4f}")
    
    win_rate = MetricsCalculator.win_rate(returns)
    assert 0 <= win_rate <= 1, "Win rate should be between 0 and 1"
    print(f"  ✓ Win rate: {win_rate:.4f}")
    
    profit_factor = MetricsCalculator.profit_factor(returns)
    assert np.isfinite(profit_factor) or profit_factor == float('inf'), "Profit factor invalid"
    print(f"  ✓ Profit factor: {profit_factor:.4f}")
    
    # Test calculate_all
    all_metrics = MetricsCalculator.calculate_all(equity)
    assert len(all_metrics) > 0, "No metrics calculated"
    for key, value in all_metrics.items():
        assert np.isfinite(value), f"{key} is not finite"
    print("  ✓ Calculate all works")
    
    # Test edge cases
    empty_sharpe = MetricsCalculator.sharpe_ratio(np.array([]))
    assert empty_sharpe == 0, "Empty array should return 0"
    print("  ✓ Edge cases handled")
    
    print("  ✓ MetricsCalculator tests passed")


def test_integration():
    """Full end-to-end integration test."""
    print("\n--- Testing Full Integration ---")
    
    from src.data.loader import DataLoader
    from src.data.features import FeatureEngine
    from src.core.backtester import Backtester
    from src.core.risk_manager import RiskManager
    from src.core.metrics import MetricsCalculator
    from src.signals.price_based import z_score_signal
    from src.execution.strategy import Strategy
    
    # 1. Generate data
    df = generate_synthetic_data(500)
    print("  ✓ Generated 500 rows of synthetic data")
    
    # 2. Add features
    loader = DataLoader(verbose=False)
    df = loader.add_mid_price(df)
    
    engine = FeatureEngine(verbose=False)
    df = engine.add_all(df)
    df = engine.fill_missing(df)
    print("  ✓ Added features")
    
    # 3. Initialize components
    risk_manager = RiskManager(
        max_position=10,
        max_drawdown=0.20,
        vol_threshold=0.05,
        vol_window=20
    )
    
    strategy = Strategy(
        signal_func=z_score_signal,
        risk_manager=risk_manager,
        signal_params={'window': 20, 'entry_z': 1.5, 'exit_z': 0.5}
    )
    
    backtester = Backtester(
        initial_cash=100000,
        maker_fee=0.0002,
        taker_fee=0.0002,
        max_position=10,
        max_drawdown=0.20
    )
    
    print("  ✓ Initialized strategy and backtester")
    
    # 4. Precompute signals
    signals = strategy.precompute_signals(df)
    signal_count = sum(1 for s in signals if s is not None)
    print(f"  ✓ Generated {signal_count} signals")
    
    # 5. Run backtest
    for i, (idx, tick) in enumerate(df.iterrows()):
        signal = strategy.get_signal_at_index(
            index=i,
            current_position=backtester.position,
            current_equity=backtester.cash + backtester.position * tick['mid']
        )
        backtester.process_tick(tick, signal, trade_qty=1)
    
    print(f"  ✓ Processed {len(df)} ticks")
    print(f"  ✓ Executed {len(backtester.trades)} trades")
    
    # 6. Get results
    results = backtester.get_results()
    
    # 7. Calculate metrics
    metrics = MetricsCalculator.calculate_all(results['equity_curve'])
    
    print(f"  ✓ Final equity: ${results['final_equity']:,.2f}")
    print(f"  ✓ Total return: {results['total_return']*100:.2f}%")
    print(f"  ✓ Sharpe ratio: {metrics['sharpe']:.4f}")
    print(f"  ✓ Max drawdown: {metrics['max_dd']*100:.2f}%")
    
    # 8. Validate results
    assert len(results['equity_curve']) == len(df), "Equity curve length mismatch"
    assert np.isfinite(results['final_equity']), "Final equity not finite"
    assert all(np.isfinite(v) for v in metrics.values()), "Metrics contain non-finite values"
    
    print("\n  ✓ Full integration test passed!")
    
    return results, metrics


def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("QUANTITATIVE TRADING INFRASTRUCTURE - INTEGRATION TESTS")
    print("=" * 60)
    
    try:
        test_data_loader()
        test_feature_engine()
        test_signals()
        test_risk_manager()
        test_backtester()
        test_metrics()
        results, metrics = test_integration()
        
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED ✓")
        print("=" * 60)
        
        return True
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
