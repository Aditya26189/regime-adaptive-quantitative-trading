# Contributing to Algorithmic Trading Strategy Framework

First off, thank you for considering contributing to this project! It's people like you that make this framework better for everyone.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Process](#development-process)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Documentation](#documentation)
- [Community](#community)

---

## Code of Conduct

This project and everyone participating in it is governed by our commitment to creating a welcoming and inclusive environment. By participating, you are expected to uphold this standard.

### Our Standards

- **Be Respectful:** Treat everyone with respect. Disagreements happen, but don't let them turn into personal attacks.
- **Be Collaborative:** Work together to resolve conflicts and improve the codebase.
- **Be Professional:** Use welcoming and inclusive language.
- **Be Open-Minded:** Accept constructive criticism gracefully.

---

## Getting Started

### Prerequisites

Before you begin, ensure you have:

- Python 3.10 or higher installed
- Git for version control
- A GitHub account
- Familiarity with quantitative trading concepts (recommended)

### Setting Up Your Development Environment

1. **Fork the repository** on GitHub
   ```bash
   # Click the "Fork" button on GitHub
   ```

2. **Clone your fork locally**
   ```bash
   git clone https://github.com/YOUR_USERNAME/LSTM.git
   cd LSTM
   ```

3. **Add the upstream repository**
   ```bash
   git remote add upstream https://github.com/Aditya26189/LSTM.git
   ```

4. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

5. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # If available
   ```

6. **Create a new branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

---

## Development Process

### Workflow Overview

1. **Find or Create an Issue:** Look for existing issues or create a new one describing what you want to work on
2. **Discuss:** Comment on the issue to let others know you're working on it
3. **Develop:** Write your code following our coding standards
4. **Test:** Ensure all tests pass and add new tests for your changes
5. **Document:** Update documentation as needed
6. **Submit:** Create a pull request

### Branch Naming Convention

Use descriptive branch names:

- `feature/add-new-strategy` - For new features
- `fix/correct-sharpe-calculation` - For bug fixes
- `docs/update-readme` - For documentation updates
- `refactor/optimize-backtest-engine` - For code refactoring
- `test/add-strategy-tests` - For adding tests

### Keeping Your Fork Updated

```bash
# Fetch upstream changes
git fetch upstream

# Merge upstream main into your local main
git checkout main
git merge upstream/main

# Update your fork on GitHub
git push origin main
```

---

## Pull Request Process

### Before Submitting

1. **Ensure your code works:**
   - Run all tests: `python -m pytest tests/`
   - Test your changes manually
   - Verify no regression in existing functionality

2. **Follow coding standards:**
   - Code passes linting: `flake8 src/`
   - Code is formatted: `black src/`
   - Imports are organized: `isort src/`

3. **Update documentation:**
   - Update docstrings
   - Update relevant markdown files
   - Add examples if applicable

4. **Write a clear commit message:**
   ```bash
   git commit -m "feat: Add volatility-based position sizing

   - Implement dynamic position sizing based on ATR
   - Add tests for position size calculation
   - Update documentation with examples
   
   Closes #123"
   ```

### Submitting Your Pull Request

1. **Push your changes:**
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Create a Pull Request on GitHub:**
   - Go to your fork on GitHub
   - Click "New Pull Request"
   - Fill out the PR template

3. **PR Title Format:**
   ```
   [TYPE] Brief description
   
   Examples:
   [FEATURE] Add Kalman filter strategy
   [FIX] Correct RSI calculation for edge cases
   [DOCS] Update installation instructions
   [REFACTOR] Optimize backtest performance
   ```

4. **PR Description Should Include:**
   - What changes were made
   - Why these changes are necessary
   - How to test the changes
   - Any breaking changes
   - Related issue numbers

### Review Process

- Maintainers will review your PR within 3-5 business days
- Address any requested changes
- Once approved, a maintainer will merge your PR

---

## Coding Standards

### Python Style Guide

We follow **PEP 8** with some modifications:

- **Line Length:** 100 characters (instead of 79)
- **Indentation:** 4 spaces (no tabs)
- **Quotes:** Use double quotes for strings
- **Naming Conventions:**
  - `snake_case` for functions and variables
  - `PascalCase` for classes
  - `UPPER_CASE` for constants

### Code Organization

```python
# Standard library imports
import os
import sys
from typing import Dict, List, Tuple

# Third-party imports
import numpy as np
import pandas as pd

# Local imports
from src.strategies.base_strategy import BaseStrategy
from src.utils.helpers import calculate_returns
```

### Docstring Format

Use Google-style docstrings:

```python
def calculate_sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.0) -> float:
    """
    Calculate the Sharpe ratio for a returns series.
    
    Args:
        returns: Series of returns
        risk_free_rate: Annual risk-free rate (default: 0.0)
    
    Returns:
        Sharpe ratio (annualized)
    
    Raises:
        ValueError: If returns series is empty
    
    Example:
        >>> returns = pd.Series([0.01, 0.02, -0.01, 0.03])
        >>> sharpe = calculate_sharpe_ratio(returns)
        >>> print(f"Sharpe: {sharpe:.2f}")
    """
    if returns.empty:
        raise ValueError("Returns series cannot be empty")
    
    excess_returns = returns - risk_free_rate / 252
    return np.sqrt(252) * excess_returns.mean() / excess_returns.std()
```

### Type Hints

Always use type hints:

```python
from typing import Dict, List, Optional, Tuple

def backtest_strategy(
    data: pd.DataFrame,
    params: Dict[str, float],
    initial_capital: float = 100000.0
) -> Tuple[List[Dict], Dict[str, float]]:
    """Backtest a trading strategy."""
    pass
```

---

## Testing Guidelines

### Test Structure

```
tests/
├── unit/                 # Unit tests for individual functions
│   ├── test_strategies.py
│   ├── test_indicators.py
│   └── test_utils.py
├── integration/          # Integration tests
│   ├── test_backtest_engine.py
│   └── test_optimization.py
└── fixtures/             # Test data and fixtures
    └── sample_data.csv
```

### Writing Tests

```python
import pytest
import pandas as pd
from src.strategies.hybrid_adaptive_v2 import HybridAdaptiveV2

class TestHybridAdaptiveV2:
    """Tests for Hybrid Adaptive V2 strategy."""
    
    @pytest.fixture
    def sample_data(self):
        """Create sample market data for testing."""
        return pd.DataFrame({
            'date': pd.date_range('2020-01-01', periods=100, freq='H'),
            'close': np.random.randn(100).cumsum() + 100,
            'volume': np.random.randint(1000, 10000, 100)
        })
    
    def test_signal_generation(self, sample_data):
        """Test that signals are generated correctly."""
        strategy = HybridAdaptiveV2(params={'rsi_period': 2})
        signals = strategy.generate_signals(sample_data)
        
        assert 'signal' in signals.columns
        assert signals['signal'].isin([-1, 0, 1]).all()
    
    def test_backtest_returns_trades(self, sample_data):
        """Test that backtest returns trade list."""
        strategy = HybridAdaptiveV2(params={'rsi_period': 2})
        trades, metrics = strategy.backtest(sample_data)
        
        assert isinstance(trades, list)
        assert isinstance(metrics, dict)
        assert 'sharpe_ratio' in metrics
```

### Running Tests

```bash
# Run all tests
python -m pytest

# Run specific test file
python -m pytest tests/unit/test_strategies.py

# Run with coverage
python -m pytest --cov=src tests/

# Run with verbose output
python -m pytest -v
```

---

## Documentation

### Code Documentation

- **Every function** must have a docstring
- **Every class** must have a docstring
- **Complex algorithms** should have inline comments
- **Type hints** are required for all function signatures

### Markdown Documentation

When updating documentation:

1. Keep it concise and clear
2. Use proper markdown formatting
3. Include code examples
4. Add links to related sections
5. Update the table of contents if needed

### Documentation Files to Update

- `README.md` - For major features
- `docs/USER_GUIDE.md` - For usage instructions
- `docs/ADVANCED_METHODOLOGY.md` - For strategy details
- `CHANGELOG.md` - For all changes

---

## Community

### Getting Help

- **Issues:** Use GitHub issues for bug reports and feature requests
- **Discussions:** Use GitHub discussions for questions and ideas
- **Email:** For sensitive matters, contact the maintainers directly

### Recognition

Contributors will be recognized in:

- `CONTRIBUTORS.md` file
- Release notes for their contributions
- GitHub's contributors page

---

## Types of Contributions

We welcome all types of contributions:

### 🐛 Bug Reports

When reporting bugs, include:

- Python version
- Operating system
- Steps to reproduce
- Expected vs. actual behavior
- Error messages and stack traces

### ✨ Feature Requests

When suggesting features:

- Describe the problem it solves
- Explain why it's useful
- Provide examples of usage
- Consider implementation challenges

### 📝 Documentation Improvements

- Fix typos and grammar
- Clarify confusing sections
- Add missing examples
- Improve formatting

### 🔧 Code Contributions

- New trading strategies
- Performance optimizations
- Bug fixes
- Test coverage improvements
- Refactoring

---

## Versioning

We use [Semantic Versioning](https://semver.org/):

- **MAJOR:** Incompatible API changes
- **MINOR:** New functionality (backward compatible)
- **PATCH:** Bug fixes (backward compatible)

---

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

## Questions?

If you have questions about contributing, feel free to:

- Open an issue with the `question` label
- Start a discussion on GitHub Discussions
- Contact the maintainers

---

Thank you for contributing to make this project better! 🎉
