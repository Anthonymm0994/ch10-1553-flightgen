# Testing Guide

## Overview

The CH10 Generator includes a test suite to ensure reliability and correctness of all components.

## Test Structure

```
tests/
├── Core Tests
│   ├── test_bitfield_packing.py    # Bitfield encoding/decoding
│   ├── test_icd.py                 # ICD validation
│   ├── test_encode1553.py          # 1553 encoding
│   ├── test_float32_encoding.py    # Float32 split encoding
│   └── test_1553_encode.py         # Additional encoding tests
├── Integration Tests
│   ├── test_ch10_roundtrip.py      # End-to-end generation
│   ├── test_cli.py                 # CLI commands
│   └── test_integration_spec.py    # Specification compliance
├── Validation Tests
│   ├── test_tshark_validation.py   # TShark/Wireshark validation
│   ├── test_ch10_validation.py     # CH10 file validation
│   ├── test_pyc10_parsing.py       # PyChapter10 parsing
│   └── test_comprehensive_bitfields.py # Bitfield edge cases
├── Phase 1 Compliance Tests
│   ├── test_phase1_compliance.py   # Time-F1 packet compliance
│   └── test_phase1_sanity_checks_fixed.py # Pre-Phase-2 sanity checks
└── Performance Tests
    └── test_performance.py          # Performance benchmarks
```

## Running Tests

### Quick Test
```bash
# Run core tests only
pytest tests/test_bitfield_packing.py tests/test_icd.py tests/test_float32_encoding.py -v

# Run Phase 1 compliance tests
pytest tests/test_phase1_compliance.py tests/test_phase1_sanity_checks_fixed.py -v

# Run with coverage
pytest tests/ --cov=ch10gen --cov-report=html
```

### Full Test Suite
```bash
# Run all tests
pytest tests/ -v

# Run specific category
pytest tests/test_*validation*.py -v

# Run with markers
pytest -m "not slow" tests/
```

### TShark Validation
```bash
# Enable TShark tests (requires Wireshark installed)
export WITH_TSHARK=1
pytest tests/test_tshark_validation.py -v

# Specify TShark path
export TSHARK="C:/Program Files/Wireshark/tshark.exe"
pytest tests/test_tshark_comprehensive.py -v
```

## Test Categories

### 1. Unit Tests
- **Purpose**: Test individual functions and classes
- **Files**: `test_encode1553.py`, `test_icd.py`, `test_float32_encoding.py`
- **Coverage**: Core encoding, validation logic, float32 split encoding

### 2. Integration Tests
- **Purpose**: Test component interactions
- **Files**: `test_ch10_roundtrip.py`, `test_cli.py`
- **Coverage**: End-to-end workflows

### 3. Validation Tests
- **Purpose**: Verify output correctness
- **Files**: `test_tshark_validation.py`, `test_ch10_validation.py`, `test_pyc10_parsing.py`
- **Coverage**: External tool validation, CH10 file validation, PyChapter10 parsing

### 4. Phase 1 Compliance Tests
- **Purpose**: Verify IRIG-106 Chapter 10 compliance
- **Files**: `test_phase1_compliance.py`, `test_phase1_sanity_checks_fixed.py`
- **Coverage**: Time-F1 packets, channel assignments, CSDW fields, packet ordering

### 5. Performance Tests
- **Purpose**: Ensure performance requirements
- **Files**: `test_performance.py`
- **Coverage**: Speed, memory usage

## Writing Tests

### Test Structure
```python
import pytest
from ch10gen.core.encode1553 import encode_bitfield

class TestBitfieldEncoding:
    """Test bitfield encoding functionality."""
    
    def test_basic_encoding(self):
        """Test basic bitfield encoding."""
        value = 42
        mask = 0x3F
        shift = 4
        
        encoded = encode_bitfield(value, mask, shift)
        assert encoded == (42 << 4) & (0x3F << 4)
    
    def test_value_validation(self):
        """Test that invalid values are rejected."""
        with pytest.raises(ValueError):
            encode_bitfield(256, 0xFF, 0)  # Value too large
```

### Fixtures
```python
@pytest.fixture
def sample_icd():
    """Provide a sample ICD for testing."""
    return {
        'name': 'Test ICD',
        'bus': 'A',
        'messages': [...]
    }

def test_icd_loading(sample_icd):
    """Test ICD loading with fixture."""
    icd = load_icd(sample_icd)
    assert icd.name == 'Test ICD'
```

## Continuous Integration

### GitHub Actions
```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      - run: pip install -r requirements.txt
      - run: pip install pytest pytest-cov
      - run: pytest tests/ --cov=ch10gen
```

## Test Data

### Sample Files
- `icd/nav_icd.yaml` - Navigation ICD
- `icd/bitfield_example.yaml` - Bitfield packing examples
- `scenarios/test_scenario.yaml` - Test flight scenario

### Generated Files
Test outputs are placed in:
- `out/` - CH10 files
- `htmlcov/` - Coverage reports
- `.pytest_cache/` - Test cache

## Debugging Tests

### Verbose Output
```bash
# Show all output
pytest tests/test_cli.py -vv -s

# Show only failures
pytest tests/ --tb=short

# Debug specific test
pytest tests/test_icd.py::TestICDDefinition::test_load_nav_icd -vv
```

### Using pdb
```python
def test_complex_logic():
    import pdb; pdb.set_trace()
    # Test code here
```

## Coverage Goals

- **Core modules**: >90% coverage
- **Utilities**: >80% coverage
- **CLI**: >70% coverage
- **Overall**: >85% coverage

## Common Issues

### Import Errors
```bash
# Fix Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest tests/
```

### TShark Not Found
```bash
# Windows
export TSHARK="/c/Program Files/Wireshark/tshark.exe"

# Linux
export TSHARK="/usr/bin/tshark"
```

### Slow Tests
```bash
# Skip slow tests
pytest -m "not slow" tests/

# Set timeout
pytest --timeout=10 tests/
```

## Best Practices

1. **Test Isolation**: Each test should be independent
2. **Clear Names**: Use descriptive test names
3. **Assertions**: Use specific assertions with messages
4. **Fixtures**: Share setup code via fixtures
5. **Mocking**: Mock external dependencies
6. **Documentation**: Document complex test logic
7. **Performance**: Keep tests fast (<1s each)
8. **Coverage**: Aim for high coverage but focus on quality

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [Coverage.py](https://coverage.readthedocs.io/)
- [TShark documentation](https://www.wireshark.org/docs/man-pages/tshark.html)
