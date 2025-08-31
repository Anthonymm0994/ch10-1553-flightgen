# Scenario-Driven Data Generation System

## Overview

This document defines the comprehensive design for scenario-driven data generation in CH10/1553 files. The system separates structure (ICDs) from behavior (scenarios), allowing flexible test data generation without modifying ICDs.

## Core Design Principles

1. **ICD defines structure**: Messages, fields, encoding, rates
2. **Scenario defines behavior**: How data is generated
3. **One ICD, many scenarios**: Never edit ICDs for different tests
4. **Default to random**: Unspecified fields automatically use random data
5. **Progressive complexity**: Simple cases simple, complex cases possible
6. **Granular control**: Configure any single field independently

## Field Configuration Granularity

You can configure data generation at any level:

- **Single field in a word**: Just that one field
- **All fields in a message**: Message-level default
- **All fields globally**: Global default

Example - Configure just one field:
```yaml
messages:
  "Navigation Data":
    fields:
      altitude:  # Only this field uses normal distribution
        mode: random_normal
        mean: 10000
        std_dev: 500
      # All other fields in entire ICD use default (random)
```

Example - Mix different modes in same word:
```yaml
messages:
  "Sensor Data":
    fields:
      temperature:  # This field uses sine wave
        mode: sine
        center: 25
        amplitude: 10
        frequency: 0.1
      pressure:     # This field uses expression
        mode: expression
        formula: "1013 - altitude * 0.012"
      humidity:     # This field uses random (default)
        # No configuration needed
```

## Field Reference Syntax

Fields can be referenced across the entire ICD using a dot notation that handles spaces in names:

```yaml
# Same word (no prefix)
formula: "field1 + field2"

# Same message, different word
formula: "word1.field1 + word2.field2"

# Different message (spaces in names are fine)
formula: "Navigation Data.altitude + Engine Data.thrust"

# Full path for clarity (always works)
formula: "Navigation Data.word1.altitude"
```

### Reference Resolution Rules

1. **No dots**: Look in same word
2. **One dot**: Look in same message
3. **Two+ dots**: Full path from message name
4. **Spaces allowed**: Message names can contain spaces

Examples:
```yaml
# In message "Navigation Data", word 0, field "altitude"
altitude_meters:
  mode: expression
  formula: "altitude * 0.3048"  # Same word

# In message "Engine Data"  
total_thrust:
  mode: expression
  formula: "left_rpm + right_rpm"  # Same word
  
efficiency:
  mode: expression
  formula: "total_thrust / (Navigation Data.airspeed + 0.1)"  # Cross-message
```

## Data Generation Modes

### 1. Random Distributions

#### Uniform (Default)
```yaml
mode: random
min: 0
max: 100
```

#### Normal/Gaussian
```yaml
mode: random_normal
mean: 50
std_dev: 10
min: 0      # Optional: clip to range
max: 100
```

#### Multimodal
```yaml
mode: random_multimodal
peaks:
  - mean: 25
    std_dev: 5
    weight: 0.3
  - mean: 75
    std_dev: 8
    weight: 0.7
```

#### Exponential
```yaml
mode: random_exponential
lambda: 1.5
min: 0
max: 100
```

### 2. Deterministic Patterns

#### Counter/Increment
```yaml
mode: increment
start: 0
increment: 1
wrap: 65535    # Optional: wrap around
```

#### Constant
```yaml
mode: constant
value: 0x1234
```

#### Pattern/Sequence
```yaml
mode: pattern
values: [0, 1, 2, 3, 2, 1]
repeat: true   # Default: true
```

### 3. Waveform Generators

#### Sine Wave
```yaml
mode: sine
center: 50
amplitude: 20
frequency: 0.1   # Hz
phase: 0         # Optional: phase offset in radians
```

#### Cosine Wave
```yaml
mode: cosine
center: 50
amplitude: 20
frequency: 0.1
phase: 0
```

#### Sawtooth
```yaml
mode: sawtooth
min: 0
max: 100
period: 10       # seconds
```

#### Square Wave
```yaml
mode: square
low: 0
high: 100
period: 5        # seconds
duty_cycle: 0.5  # Optional: 0-1, default 0.5
```

#### Linear Ramp
```yaml
mode: ramp
start: 0
end: 100
duration: 10     # seconds
repeat: false    # Optional: repeat after duration
```

### 4. Mathematical Expressions

#### Basic Arithmetic
```yaml
mode: expression
formula: "field1 + field2 * 2 - field3 / 4"
```

#### Cross-Message References
```yaml
mode: expression
formula: "Engine Data.rpm * Navigation Data.airspeed / 1000"
```

#### Conditional Logic
```yaml
mode: expression
formula: "altitude > 10000 ? 1 : 0"
```

#### Math Functions
```yaml
mode: expression
formula: "sin(time * 0.1) * amplitude + offset"
```

## Available Functions in Expressions

### Math Functions
- `sin(x)`, `cos(x)`, `tan(x)` - Trigonometric (radians)
- `asin(x)`, `acos(x)`, `atan(x)` - Inverse trig
- `sinh(x)`, `cosh(x)`, `tanh(x)` - Hyperbolic
- `exp(x)`, `log(x)`, `log10(x)` - Exponential/logarithmic
- `sqrt(x)`, `pow(x, y)` - Power functions
- `abs(x)`, `sign(x)` - Absolute value and sign
- `floor(x)`, `ceil(x)`, `round(x)` - Rounding
- `min(x, y, ...)`, `max(x, y, ...)` - Min/max
- `clamp(x, min, max)` - Constrain to range

### Random Functions
- `random()` - Random 0-1
- `random(min, max)` - Random in range
- `random_normal(mean, std)` - Normal distribution
- `random_int(min, max)` - Random integer

### Utility Variables
- `time` - Seconds since start (for waveform generation)
- `message_count` - Number of this message sent

### Type Conversion
- `int(x)` - Convert to integer (truncate)
- `float(x)` - Convert to float
- `round(x)` - Round to nearest integer
- `bool(x)` - Convert to boolean (0 or 1)

## Evaluation Order and Dependencies

### Three-Phase Evaluation

**Phase 1: Independent Values**
- Constants
- Random values (all distributions)
- Increments/counters
- Patterns
- Time-based functions (sine, ramp, etc.)

**Phase 2: Flight Data**
- Flight profile values
- Derived flight values

**Phase 3: Expressions**
- Sorted by dependency graph
- Circular dependencies detected and reported

### Dependency Resolution Example

```yaml
messages:
  Engine Data:
    fields:
      # Phase 1: Independent
      base_rpm:
        mode: sine
        center: 3000
        amplitude: 200
        
      # Phase 3a: Depends on base_rpm
      rpm_with_noise:
        mode: expression
        formula: "base_rpm + random(-50, 50)"
        
      # Phase 3b: Depends on rpm_with_noise
      rpm_percent:
        mode: expression
        formula: "rpm_with_noise / 5000 * 100"
        
      # Phase 3c: Cross-message dependency
      thrust:
        mode: expression
        formula: "rpm_percent * Navigation Data.airspeed / 100"
```

## Scenario File Structure

### Complete Example

```yaml
# Metadata
name: comprehensive_test
description: Full demonstration of data generation capabilities
duration: 60
version: 1.0

# Global configuration
config:
  random_seed: 42           # Optional: reproducible randomness
  time_format: seconds      # seconds, milliseconds, microseconds
  default_mode: random      # Global default if not specified
  
# Global defaults for all messages
defaults:
  random:
    min: 0
    max: 65535
  random_normal:
    std_dev: 10
    
# Message-specific configuration
messages:
  # Using spaces in message names
  "Navigation Data":
    # Message-level default (overrides global)
    default_mode: random_normal
    default_config:
      mean: 32768
      std_dev: 5000
      
    # Field-specific configuration
    fields:
      altitude:
        mode: sine
        center: 10000
        amplitude: 2000
        frequency: 0.05
        
      altitude_meters:
        mode: expression
        formula: "altitude * 0.3048"
        
      altitude_valid:
        mode: expression
        formula: "altitude > 0 && altitude < 50000 ? 1 : 0"
        
      packet_counter:
        mode: increment
        start: 0
        increment: 1
        wrap: 255
        
  "Engine Data":
    fields:
      engine1_rpm:
        mode: random_normal
        mean: 3000
        std_dev: 100
        min: 0
        max: 5000
        
      engine2_rpm:
        mode: expression
        formula: "engine1_rpm * 0.98 + random(-20, 20)"
        
      total_rpm:
        mode: expression
        formula: "engine1_rpm + engine2_rpm"
        
      rpm_delta:
        mode: expression
        formula: "abs(engine1_rpm - engine2_rpm)"
        
      efficiency:
        mode: expression
        # Cross-message reference with spaces
        formula: "total_rpm / (Navigation Data.altitude * 0.001 + 1)"
        
  "Sensor Data":
    fields:
      temperature:
        mode: ramp
        start: 20
        end: 80
        duration: 30
        repeat: true
        
      pressure:
        mode: expression
        formula: "1013 - Navigation Data.altitude * 0.012"
        
      sensor_status:
        mode: pattern
        values: [0, 0, 0, 1, 0, 0, 2, 0]
        
  "System Status":
    # No configuration needed - all fields use global default (random)
```

### Minimal Example

```yaml
# Minimal scenario - everything random
name: all_random
duration: 60
# That's it! All fields will be random with default ranges
```

### Partial Configuration

```yaml
name: nav_realistic
duration: 60

# Only configure what you need
messages:
  "Navigation Data":
    fields:
      altitude:
        mode: sine
        center: 10000
        amplitude: 2000
      # All other fields in all messages will be random
```

## Type Conversion Rules

When expressions produce floats but fields expect integers:

1. **Default**: Round to nearest integer
2. **Explicit conversion**: Use `int()`, `round()`, `floor()`, `ceil()`
3. **Overflow handling**: Clamp to field type range
   - u16: 0-65535
   - i16: -32768 to 32767
4. **Bitfield handling**: Mask to valid bits after conversion

Example:
```yaml
# Float expression for u16 field
field1:
  mode: expression
  formula: "sin(time) * 32768 + 32768"  # Produces float
  # Automatically: round() then clamp(0, 65535)
```

## Error Handling

### Expression Errors

1. **Undefined field reference**: 
   - Error: "Field 'Navigation Data.altitud' not found"

2. **Circular dependency**:
   - Error: "Circular dependency: field1 → field2 → field3 → field1"
   - Show dependency chain

3. **Division by zero**:
   - Warning logged, result = 0
   - Optional: `safe_div(x, y, default=0)`

4. **Math domain errors**:
   - Example: `sqrt(-1)`, `log(0)`
   - Warning logged, result = 0 or NaN handling

5. **Type mismatches**:
   - Automatic conversion with warning
   - Example: String in numeric context

### Configuration Errors

1. **Invalid mode**: List valid modes
2. **Missing required parameters**: Show what's needed
3. **Out of range values**: Show valid range
4. **Invalid message/field names**: Show available names

## Performance Considerations

1. **Dependency graph**: Computed once at startup
2. **Expression compilation**: Parse once, evaluate many
3. **Caching**: Cache expression results within same timestamp
4. **Batch evaluation**: Evaluate all fields for a message together
5. **Lazy evaluation**: Only compute fields that are actually used

## Best Practices

### DO:
- Start simple, add complexity as needed
- Use meaningful scenario names
- Document complex expressions with comments
- Test expressions with small durations first
- Use consistent units across related fields

### DON'T:
- Create circular dependencies
- Use expressions for simple constants
- Mix units without conversion
- Assume evaluation order without dependencies
- Reference non-existent fields

### PREFER:
- Named modes over complex expressions
- Clear field names over abbreviations
- Explicit dependencies over implicit timing
- Deterministic patterns for testing
- Random distributions for stress testing

## Migration Path

### From Current System

1. **Existing ICDs**: Work as-is, all fields default to random
2. **Existing scenarios**: Continue to work, new features opt-in
3. **No src field needed**: Fields don't need src attribute
4. **No breaking changes**: All current functionality preserved

### Gradual Adoption

1. Start with all random (no configuration)
2. Add specific fields as needed
3. Build library of reusable scenarios
4. Share scenarios across projects

## Examples by Use Case

### Unit Testing
```yaml
name: unit_test
messages:
  "Test Message":
    fields:
      counter:
        mode: increment
        start: 1
      expected_value:
        mode: constant
        value: 42
```

### Stress Testing
```yaml
name: stress_test
defaults:
  random:
    min: 0
    max: 65535
# High entropy random data
```

### Realistic Simulation
```yaml
name: flight_sim
messages:
  "Navigation Data":
    fields:
      altitude:
        mode: expression
        formula: "10000 + sin(time * 0.01) * 2000"
      airspeed:
        mode: expression
        formula: "250 + random(-10, 10)"
```

### Regression Testing
```yaml
name: regression_test
config:
  random_seed: 12345  # Reproducible
messages:
  "Status":
    fields:
      test_pattern:
        mode: pattern
        values: [0x00, 0xFF, 0xAA, 0x55]
```

## Implementation Status

### ✅ Implemented and Tested
- Basic random (uniform distribution)
- Field-level configuration in scenarios

### 🚧 Partially Implemented
- Random data generation (needs scenario integration)

### ⏳ Not Yet Implemented
- Statistical distributions (normal, multimodal)
- Waveform generators (sine, cosine, sawtooth, square, ramp)
- Increment/counter mode
- Pattern/sequence mode
- Mathematical expressions
- Cross-message references
- Dependency resolution

## Architecture for Modularity

### Core Components

```python
# Base class for all data generators
class DataGenerator(ABC):
    @abstractmethod
    def generate(self, context: GenerationContext) -> Union[int, float]:
        pass

# Specific implementations
class RandomGenerator(DataGenerator):
    def __init__(self, min=0, max=65535):
        self.min = min
        self.max = max
    
    def generate(self, context):
        return random.randint(self.min, self.max)

class SineGenerator(DataGenerator):
    def __init__(self, center, amplitude, frequency, phase=0):
        self.center = center
        self.amplitude = amplitude
        self.frequency = frequency
        self.phase = phase
    
    def generate(self, context):
        t = context.time_seconds
        return self.center + self.amplitude * math.sin(2 * math.pi * self.frequency * t + self.phase)

# Factory for creating generators
class GeneratorFactory:
    @staticmethod
    def create(config: dict) -> DataGenerator:
        mode = config.get('mode', 'random')
        if mode == 'random':
            return RandomGenerator(config.get('min', 0), config.get('max', 65535))
        elif mode == 'sine':
            return SineGenerator(
                config.get('center', 0),
                config.get('amplitude', 1),
                config.get('frequency', 1),
                config.get('phase', 0)
            )
        # ... other generators
```

### Adding New Generators

To add a new data generation mode:

1. Create a new class inheriting from `DataGenerator`
2. Implement the `generate()` method
3. Add to `GeneratorFactory.create()`
4. Add configuration schema validation
5. Add unit tests
6. Update this documentation

### Context Object

```python
@dataclass
class GenerationContext:
    time_seconds: float          # Time since start
    message_count: int           # Count for this message type
    message_name: str           # Current message name
    field_name: str            # Current field name
    field_values: dict         # Already computed field values
    icd: ICDDefinition        # Full ICD for cross-references
```

## Testing Strategy

### Unit Tests
- Each generator mode independently
- Expression parser
- Dependency resolver
- Type conversion

### Integration Tests
- Full scenario loading
- Multi-message generation
- Cross-message references
- Complex expressions

### Validation Tests
- Generated data ranges
- Statistical distributions
- Waveform accuracy
- Performance benchmarks

## Summary

This system provides complete flexibility for test data generation while maintaining simplicity for basic use cases. The separation of structure (ICD) and behavior (scenario) enables powerful testing capabilities without ICD proliferation.
