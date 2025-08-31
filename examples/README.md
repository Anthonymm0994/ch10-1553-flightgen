# CH10 Generator Examples

This directory contains example scripts and demonstrations of the CH10 Generator capabilities.

## Examples

### 1. bitfield_demo.py
Demonstrates bitfield packing and unpacking functionality:
- Basic bitfield encoding/decoding
- Multi-field packing into single 16-bit words
- Scaling and offset operations
- Error handling for invalid values
- Realistic avionics scenario

**Usage:**
```bash
python examples/bitfield_demo.py
```

### 2. generate_basic.py
Simple CH10 file generation example.

### 3. custom_encoding.py
Advanced encoding techniques with custom data sources.

### 4. error_injection.py
Demonstrates error injection capabilities.

### 5. pcap_export.py
Shows how to export CH10 data to PCAP format.

## Sample CH10 Files

Sample CH10 files are stored in the `out/` directory:
- `out/sample_nav.ch10` - Navigation data example
- `out/sample_sensor.ch10` - Sensor data example
- `out/sample_bitfield.ch10` - Bitfield packing example

## Running Examples

All examples can be run directly:
```bash
# Run bitfield demonstration
python examples/bitfield_demo.py

# Generate a basic CH10 file
python examples/generate_basic.py

# Export to PCAP
python examples/pcap_export_demo.py
```

## Creating Your Own Examples

To create a new example:
1. Import the necessary modules from `ch10gen`
2. Load or create an ICD
3. Configure flight profile or data sources
4. Generate the CH10 file

Example template:
```python
from ch10gen.icd import load_icd
from ch10gen.scenario import load_scenario, create_flight_profile
from ch10gen.schedule import build_schedule_from_icd
from ch10gen.ch10_writer import write_ch10_file, Ch10WriterConfig

# Load configurations
icd = load_icd('icd/your_icd.yaml')
scenario = load_scenario('scenarios/your_scenario.yaml')

# Create components
profile = create_flight_profile(scenario)
schedule = build_schedule_from_icd(icd)

# Generate CH10
config = Ch10WriterConfig()
write_ch10_file('output.ch10', schedule, profile, config, duration_s=60)
```
