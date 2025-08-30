# Breaking Changes - Scenario-Driven Data Generation

## Overview

The CH10 generator has been updated with a new scenario-driven data generation system that provides granular control over how data is generated for each field in your ICD. This document outlines the breaking changes and migration guide.

## Breaking Changes

### 1. Scenario Format Changes

#### Old Format
```yaml
# Old scenarios used 'data_mode' at the root level
name: Test Scenario
data_mode: random  # or 'flight'
random_config:
  distribution: uniform
```

#### New Format
```yaml
# New scenarios use 'defaults' section
name: Test Scenario
defaults:
  data_mode: random  # or 'flight' 
  default_config:
    distribution: uniform
```

### 2. Random Data Generation

The old `RandomDataGenerator` class has been replaced with a modular system. If you were using `data_mode: random`, your scenarios will still work but should be updated to use the new format for better control.

### 3. ICD Changes

#### Removed `src: random` Field
ICDs no longer need or support the `src: random` field. All data generation is controlled by scenarios.

**Before:**
```yaml
words:
  - name: field1
    encode: u16
    src: random  # No longer needed
```

**After:**
```yaml
words:
  - name: field1
    encode: u16
    const: 0  # Use const: 0 as placeholder
```

### 4. XML to YAML Converter Updates

The XML converter has been updated with the following changes:
- Default bus is now 'B' (was 'A')
- ICD name is derived from the input filename
- Word number appears at the top of word definitions
- No `src` field is generated

## Migration Guide

### Step 1: Update Your Scenarios

Add a `defaults` section to your scenarios:

```yaml
defaults:
  data_mode: flight  # For flight profile data
  # OR
  data_mode: random  # For random data
  default_config:
    distribution: uniform
```

### Step 2: Remove `src: random` from ICDs

Replace any `src: random` with `const: 0`:

```bash
# Quick sed command to update ICDs (backup first!)
sed -i.bak 's/src: random/const: 0/g' your_icd.yaml
```

### Step 3: Leverage New Features

Take advantage of the new granular control:

```yaml
messages:
  "Your Message":
    fields:
      field1:
        mode: sine
        amplitude: 100
        frequency: 1.0
      field2:
        mode: increment
        start: 0
        step: 1
      field3:
        mode: expression
        formula: "field1 + field2"
```

## New Features

### Available Data Generation Modes

1. **Random Distributions**
   - `uniform`: Random values with uniform distribution
   - `normal`: Gaussian distribution with mean and std_dev
   - `multimodal`: Multiple gaussian peaks

2. **Deterministic Patterns**
   - `constant`: Fixed value
   - `increment`: Counter with configurable step
   - `pattern`: Repeating sequence of values

3. **Waveforms**
   - `sine`, `cosine`: Trigonometric waves
   - `square`: Square wave
   - `sawtooth`: Sawtooth wave
   - `ramp`: Linear ramp

4. **Mathematical Expressions**
   - `expression`: Calculate values using formulas
   - Reference other fields in same word, same message, or different messages
   - Supports standard math operations and functions

### Example: Complete Scenario

```yaml
name: Advanced Test
duration_s: 10

defaults:
  data_mode: random
  default_config:
    distribution: uniform

messages:
  "Navigation":
    fields:
      altitude:
        mode: sine
        amplitude: 5000
        frequency: 0.1
        offset: 10000
      
      speed:
        mode: ramp
        start: 0
        end: 500
        duration: 10
      
      distance:
        mode: expression
        formula: "speed * 0.1"  # Simple integration

  "Engine":
    fields:
      rpm:
        mode: random
        distribution: normal
        mean: 3000
        std_dev: 100
      
      temperature:
        mode: expression
        formula: "rpm * 0.05 + 100"  # Temperature based on RPM
```

## Backward Compatibility

### Flight Mode
Scenarios using `data_mode: flight` continue to work as before. The scenario manager is bypassed for flight mode, using the original flight profile data generation.

### Default Behavior
If no scenario configuration is provided, the system defaults to using flight profile data (backward compatible).

## Performance Improvements

The new system has been tested to handle:
- 1000+ messages per second
- ICDs with 10,000+ lines
- Complex mathematical expressions
- Real-time waveform generation

## Getting Help

For questions or issues with migration:
1. Check the comprehensive test suite in `tests/test_scenario_integration.py`
2. Review example scenarios in `scenarios/`
3. See `docs/SCENARIO_DATA_GENERATION.md` for detailed documentation

## Version Information

These changes are effective as of version 2.0.0 (December 2024).
