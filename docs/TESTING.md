# FRANKENSTEIN 1.0 - Testing Guide

## Quick Start

### 1. First Time Setup

Run the automated setup script to install all dependencies:

```batch
setup_env.bat
```

This will:
- Check Python installation (requires Python 3.9+)
- Upgrade pip
- Install all dependencies from requirements.txt
- Install testing tools (pytest, pytest-cov, black, mypy)

### 2. Run Tests

You have multiple options for running tests:

#### Option A: Batch Script (Windows)

```batch
# Standard tests
run_tests.bat

# Quick tests (no coverage)
run_tests.bat quick

# Full coverage report
run_tests.bat coverage

# Verbose output
run_tests.bat verbose

# Unit tests only
run_tests.bat unit
```

#### Option B: Python Test Runner

```bash
# Standard tests
python test_runner.py

# Quick tests
python test_runner.py quick

# Full coverage report
python test_runner.py coverage

# Verbose output
python test_runner.py verbose

# Unit tests only
python test_runner.py unit
```

#### Option C: Direct pytest

```bash
# Run all tests
python -m pytest tests/

# Run with coverage
python -m pytest tests/ --cov=core --cov-report=html

# Run specific test file
python -m pytest tests/unit/test_safety.py

# Run with verbose output
python -m pytest tests/ -vv -s
```

---

## Test Structure

```
tests/
├── __init__.py
└── unit/
    ├── __init__.py
    ├── test_safety.py          # Safety constraints tests
    ├── test_governor.py        # Resource governor tests
    ├── test_memory.py          # Memory system tests
    └── test_orchestrator.py    # Task orchestrator tests
```

### Test Coverage

Current test files cover:

1. **Safety System** (`test_safety.py`)
   - Immutable safety constraints
   - Resource violation detection
   - Tier 1 compliance checks
   - Constraint dictionary export

2. **Resource Governor** (`test_governor.py`)
   - Governor lifecycle (start/stop)
   - Throttle level management
   - Resource monitoring
   - Singleton pattern

3. **Memory System** (`test_memory.py`)
   - Task record creation
   - Session state management
   - Memory initialization
   - Directory structure

4. **Task Orchestrator** (`test_orchestrator.py`)
   - Task creation and management
   - Priority queue ordering
   - Worker thread limits
   - Task status tracking

---

## Test Modes Explained

### Quick Mode
- **Purpose**: Fast feedback during development
- **Coverage**: No coverage reporting
- **Use When**: Making small changes, quick validation
- **Command**: `run_tests.bat quick` or `python test_runner.py quick`

### Standard Mode (Default)
- **Purpose**: Regular testing with basic coverage
- **Coverage**: Core modules only, terminal report
- **Use When**: Normal development workflow
- **Command**: `run_tests.bat` or `python test_runner.py`

### Coverage Mode
- **Purpose**: Comprehensive coverage analysis
- **Coverage**: All modules, HTML + terminal report
- **Use When**: Before commits, ensuring code quality
- **Command**: `run_tests.bat coverage` or `python test_runner.py coverage`
- **Output**: `htmlcov/index.html` - Open in browser for detailed coverage

### Verbose Mode
- **Purpose**: Debugging test failures
- **Coverage**: Shows all print statements and detailed output
- **Use When**: Investigating test failures
- **Command**: `run_tests.bat verbose` or `python test_runner.py verbose`

### Unit Mode
- **Purpose**: Run only unit tests
- **Coverage**: Unit tests only (no integration tests)
- **Use When**: Testing core component changes
- **Command**: `run_tests.bat unit` or `python test_runner.py unit`

---

## Writing New Tests

### Test File Naming Convention

- Test files must start with `test_`
- Example: `test_newmodule.py`

### Test Class Structure

```python
"""
FRANKENSTEIN 1.0 - Module Tests
Unit tests for module_name.py
"""

import pytest
from module import ClassName, function_name


class TestClassName:
    """Test ClassName functionality"""

    def test_basic_creation(self):
        """Test creating an instance"""
        obj = ClassName()
        assert obj is not None

    def test_specific_behavior(self):
        """Test specific behavior"""
        obj = ClassName()
        result = obj.method()
        assert result == expected_value
```

### Best Practices

1. **One assertion per test** (when possible)
2. **Descriptive test names** that explain what is being tested
3. **Use docstrings** to describe test purpose
4. **Group related tests** into test classes
5. **Clean up resources** in tests (use pytest fixtures)
6. **Test edge cases** and error conditions

---

## Continuous Integration

### Pre-Commit Checklist

Before committing code:

1. Run standard tests: `python test_runner.py`
2. Check coverage: `python test_runner.py coverage`
3. Format code: `python -m black .`
4. Type check: `python -m mypy core/`

### Automated Testing

The test suite is designed to run in CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Install dependencies
  run: pip install -r requirements.txt

- name: Run tests
  run: python test_runner.py coverage

- name: Upload coverage
  uses: codecov/codecov-action@v3
```

---

## Troubleshooting

### "pytest not found"

**Solution**: Install pytest
```bash
pip install pytest pytest-cov
```

### "ModuleNotFoundError: No module named 'core'"

**Solution**: Run tests from repository root directory
```bash
cd c:\Users\adamn\Frankenstein-1.0
python -m pytest tests/
```

### "psutil not installed" warning

**Solution**: Install psutil for full functionality
```bash
pip install psutil
```

### Tests fail on resource tests

**Solution**: Some tests require system resources. Try:
1. Close other applications
2. Run in unit mode: `python test_runner.py unit`
3. Skip specific tests: `pytest tests/ -k "not test_name"`

### Coverage report not generated

**Solution**: Install pytest-cov
```bash
pip install pytest-cov
```

---

## Performance Testing

### Resource Usage Tests

Tests monitor system resources to ensure FRANKENSTEIN respects limits:

- **CPU Usage**: Should not exceed 80%
- **Memory Usage**: Should not exceed 70%
- **Thread Count**: Should not exceed 3 worker threads

### Benchmarking

To benchmark test execution time:

```bash
python -m pytest tests/ --durations=10
```

This shows the 10 slowest tests.

---

## Test Coverage Goals

### Current Coverage

Run coverage mode to see current coverage:
```bash
python test_runner.py coverage
```

### Target Coverage

- **Core modules**: 80%+ coverage
- **Safety critical code**: 95%+ coverage
- **Utility functions**: 70%+ coverage

### Viewing Coverage Report

After running coverage mode:

1. Open `htmlcov/index.html` in a browser
2. Click on modules to see line-by-line coverage
3. Red lines indicate uncovered code
4. Green lines indicate covered code

---

## Adding Integration Tests

Create integration tests in `tests/integration/`:

```python
# tests/integration/test_full_system.py
"""
Integration tests for full system functionality
"""

import pytest
from core import get_governor, get_memory, get_orchestrator


class TestSystemIntegration:
    """Test full system integration"""

    def test_system_startup(self):
        """Test complete system can start up"""
        governor = get_governor()
        memory = get_memory()
        orchestrator = get_orchestrator()

        governor.start()
        memory.initialize()
        orchestrator.start()

        # Verify all systems running
        assert governor._running
        assert memory._initialized
        # Add more assertions

        # Clean up
        governor.stop()
        orchestrator.stop()
```

---

## Questions?

For issues or questions about testing:

1. Check this guide first
2. Review test examples in `tests/unit/`
3. Run tests in verbose mode for detailed output
4. Check pytest documentation: https://docs.pytest.org

---

**Last Updated**: January 25, 2026
**FRANKENSTEIN Version**: 1.0 (Phase 1)
