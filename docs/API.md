# API Reference

## Core Modules

### ch10gen.icd

Interface Control Document (ICD) handling for MIL-STD-1553 messages.

#### Classes

##### `WordDefinition`
Defines a single 16-bit word within a 1553 message.

```python
class WordDefinition:
    name: str                    # Word name
    encode: str                  # Encoding type
    src: Optional[str]          # Data source
    const: Optional[Any]        # Constant value
    scale: float                # Scale factor
    offset: float               # Offset value
    mask: Optional[int]         # Bit mask for packing
    shift: Optional[int]        # Bit shift for packing
    word_index: Optional[int]   # Word position in message
```

**Methods:**
- `validate() -> List[str]`: Validate word definition
- `get_word_count() -> int`: Get number of 16-bit words

##### `MessageDefinition`
Defines a complete 1553 message.

```python
class MessageDefinition:
    name: str           # Message name
    rate_hz: float      # Transmission rate in Hz
    rt: int            # Remote Terminal address (0-31)
    tr: str            # Transfer type (RT2BC, BC2RT, etc.)
    sa: int            # Subaddress (0-31)
    wc: int            # Word count (1-32)
    words: List[WordDefinition]  # Word definitions
```

**Methods:**
- `validate() -> List[str]`: Validate message definition
- `is_receive() -> bool`: Check if RT receives
- `is_transmit() -> bool`: Check if RT transmits

##### `ICDDefinition`
Complete ICD containing multiple messages.

```python
class ICDDefinition:
    name: str                          # ICD name
    bus: str                          # Bus identifier
    messages: List[MessageDefinition] # Message definitions
```

**Methods:**
- `validate() -> List[str]`: Validate entire ICD
- `get_message_by_name(name: str) -> MessageDefinition`: Find message
- `calculate_bandwidth() -> float`: Calculate total bandwidth

#### Functions

##### `load_icd(icd_file: Path) -> ICDDefinition`
Load ICD from YAML file.

```python
from ch10gen.icd import load_icd

icd = load_icd('icd/nav_icd.yaml')
print(f"Loaded {len(icd.messages)} messages")
```

##### `validate_icd_file(icd_file: Path) -> bool`
Validate ICD file without loading.

```python
from ch10gen.icd import validate_icd_file

if validate_icd_file('icd/test.yaml'):
    print("ICD is valid")
```

### ch10gen.core.encode1553

MIL-STD-1553 word encoding and decoding functions.

#### Functions

##### `encode_u16(value: Union[int, float]) -> int`
Encode unsigned 16-bit integer.

```python
from ch10gen.core.encode1553 import encode_u16

word = encode_u16(12345)  # Returns 0x3039
```

##### `encode_i16(value: Union[int, float]) -> int`
Encode signed 16-bit integer.

```python
from ch10gen.core.encode1553 import encode_i16

word = encode_i16(-1000)  # Two's complement
```

##### `bnr16(value: float, scale: float = 1.0, offset: float = 0.0) -> int`
Encode Binary Number Representation (BNR) value.

```python
from ch10gen.core.encode1553 import bnr16

# Encode altitude with 1 ft resolution
word = bnr16(altitude_ft, scale=1.0)
```

##### `encode_bitfield(value, mask, shift, scale=1.0, offset=0.0) -> int`
Encode value into bitfield.

```python
from ch10gen.core.encode1553 import encode_bitfield

# Pack 5-bit value at position 3
encoded = encode_bitfield(value=15, mask=0x1F, shift=3)
```

##### `float32_split(value: float, word_order: str = 'lsw_msw') -> Tuple[int, int]`
Split 32-bit float into two 16-bit words.

```python
from ch10gen.core.encode1553 import float32_split

# Split float into two words
lsw, msw = float32_split(123.456, word_order='lsw_msw')
```

##### `pack_bitfields(fields: Dict) -> int`
Pack multiple bitfields into single word.

```python
from ch10gen.core.encode1553 import pack_bitfields

word = pack_bitfields({
    'status': (1, 0x0001, 0, 1.0, 0.0),    # Bit 0
    'mode': (3, 0x0007, 1, 1.0, 0.0),      # Bits 1-3
    'count': (15, 0x000F, 4, 1.0, 0.0),    # Bits 4-7
})
```

### ch10gen.schedule

Message scheduling for 1553 bus simulation.

#### Classes

##### `Schedule`
Manages message transmission schedule.

```python
class Schedule:
    messages: List[ScheduledMessage]
    major_frame_time: float
    minor_frame_time: float
```

**Methods:**
- `add_message(msg: MessageDefinition, rate_hz: float)`: Add message
- `get_messages_at_time(t: float) -> List[ScheduledMessage]`: Get messages

#### Functions

##### `build_schedule_from_icd(icd: ICDDefinition) -> Schedule`
Build transmission schedule from ICD.

```python
from ch10gen.schedule import build_schedule_from_icd

schedule = build_schedule_from_icd(icd)
print(f"Major frame: {schedule.major_frame_time}s")
```

### ch10gen.flight_profile

Flight profile generation for realistic test data.

#### Classes

##### `FlightProfile`
Generates realistic flight parameters.

```python
class FlightProfile:
    duration_s: float
    seed: Optional[int]
    segments: List[FlightSegment]
```

**Methods:**
- `add_segment(config: Dict)`: Add flight segment
- `get_state_at_time(t: float) -> FlightState`: Get parameters
- `get_value(path: str, t: float) -> float`: Get specific value

##### `FlightState`
Flight parameters at specific time.

```python
@dataclass
class FlightState:
    time: float
    altitude_ft: float
    airspeed_kts: float
    heading_deg: float
    lat_deg: float
    lon_deg: float
    pitch_deg: float
    roll_deg: float
    yaw_deg: float
```

### ch10gen.ch10_writer

Chapter 10 file writing.

#### Classes

##### `Ch10WriterConfig`
Configuration for CH10 file generation.

```python
@dataclass
class Ch10WriterConfig:
    time_channel_id: int = 0x001
    tmats_channel_id: int = 0x000
    bus_a_channel_id: int = 0x002
    bus_b_channel_id: int = 0x003
    target_packet_bytes: int = 65536
    time_packet_interval_s: float = 1.0
    include_filler: bool = False
```

#### Functions

##### `write_ch10_file(output_file, schedule, profile, config)`
Generate CH10 file.

```python
from ch10gen.ch10_writer import write_ch10_file, Ch10WriterConfig

config = Ch10WriterConfig(packet_size=65536)
write_ch10_file(
    output_file='output.ch10',
    schedule=schedule,
    profile=flight_profile,
    config=config,
    duration_s=60.0
)
```

## CLI Interface

### Commands

#### `ch10gen build`
Generate CH10 file from ICD and scenario.

```bash
python -m ch10gen build \
    --scenario scenarios/random_test.yaml \
    --icd icd/nav_icd.yaml \
    --out output.ch10 \
    --duration 60
```

**Options:**
- `--scenario, -s`: Scenario YAML file (required)
- `--icd, -i`: ICD YAML file (required)
- `--out, -o`: Output CH10 file (required)
- `--duration, -d`: Duration in seconds
- `--seed`: Random seed for reproducibility
- `--writer`: Writer backend (pyc10, irig106)
- `--verbose, -v`: Verbose output

#### `ch10gen validate`
Validate CH10 file.

```bash
# Validate CH10 file
python -m ch10gen validate output.ch10
```

**Options:**
- `FILE`: CH10 file to validate (required)
- `--verbose, -v`: Verbose output

#### `ch10gen check-icd`
Validate ICD file.

```bash
# Validate ICD
python -m ch10gen check-icd icd/nav_icd.yaml
```

**Options:**
- `ICD`: ICD file to validate (required)
- `--verbose, -v`: Verbose output

#### `ch10gen inspect`
Inspect CH10 file contents.

```bash
python -m ch10gen inspect output.ch10 --max-messages 10
```

**Options:**
- `FILE`: CH10 file to inspect (required)
- `--max-messages`: Maximum messages to display
- `--verbose, -v`: Verbose output

## Examples

### Basic CH10 Generation
```python
from ch10gen.icd import load_icd
from ch10gen.scenario import load_scenario, create_flight_profile
from ch10gen.schedule import build_schedule_from_icd
from ch10gen.ch10_writer import write_ch10_file, Ch10WriterConfig

# Load configuration
icd = load_icd('icd/nav_icd.yaml')
scenario = load_scenario('scenarios/flight.yaml')

# Create components
profile = create_flight_profile(scenario)
schedule = build_schedule_from_icd(icd)

# Generate CH10 file
config = Ch10WriterConfig()
write_ch10_file(
    'output.ch10',
    schedule,
    profile,
    config,
    duration_s=60.0
)
```

### Custom Encoding
```python
from ch10gen.core.encode1553 import encode_bitfield, pack_bitfields, float32_split

# Single bitfield
altitude_encoded = encode_bitfield(
    value=altitude_ft,
    mask=0x3FF,  # 10 bits
    shift=0,
    scale=0.1    # 0.1 ft resolution
)

# Float32 split encoding
lat_lsw, lat_msw = float32_split(latitude_deg, word_order='lsw_msw')

# Multiple fields in one word
status_word = pack_bitfields({
    'valid': (1, 0x0001, 0, 1.0, 0.0),
    'mode': (mode_value, 0x0007, 1, 1.0, 0.0),
    'count': (count_value, 0x00FF, 8, 1.0, 0.0)
})
```

### ICD Validation
```python
from ch10gen.icd import load_icd

try:
    icd = load_icd('icd/test.yaml')
    errors = icd.validate()
    if errors:
        print("Validation errors:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("ICD is valid")
except Exception as e:
    print(f"Failed to load ICD: {e}")
```

## Error Handling

All API functions may raise:
- `FileNotFoundError`: File doesn't exist
- `ValueError`: Invalid parameters
- `yaml.YAMLError`: YAML parsing error
- `IOError`: File I/O error

Example:
```python
try:
    icd = load_icd('missing.yaml')
except FileNotFoundError:
    print("ICD file not found")
except ValueError as e:
    print(f"Invalid ICD: {e}")
```
