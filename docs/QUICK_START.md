# Quick Start Guide

Get up and running with CH10-1553-FlightGen in 5 minutes!

## Prerequisites

Before you begin, ensure you have:
- **Python 3.10+** installed
- **Windows 10/11** (primary platform)
- **Git** for cloning the repository
- **Git Bash** (recommended terminal for Windows)

## Installation

### Option 1: From Source (Recommended)
```bash
# Clone the repository
git clone https://github.com/yourusername/ch10-1553-flightgen.git
cd ch10-1553-flightgen

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .

# Verify installation
python -m ch10gen --version
```

### Option 2: Windows Executable
```bash
# Download the latest release
# https://github.com/yourusername/ch10-1553-flightgen/releases

# Or build it yourself
pyinstaller --onefile --name ch10gen --distpath dist ch10gen/__main__.py

# Run the executable
./dist/ch10gen.exe --help
```

## Your First CH10 File

### Step 1: Generate a Simple Flight
```bash
# Generate a 5-minute demo flight
python -m ch10gen build \
    --scenario scenarios/test_scenario.yaml \
    --icd icd/nav_icd.yaml \
    --out my_first_flight.ch10 \
    --duration 300
```

### Step 2: Validate the Output
```bash
# Check that the file is valid
ch10gen validate my_first_flight.c10
```

You should see output like:
```
[SUCCESS] CH10 file validation passed
  - TMATS packet found
  - Time packets: 300
  - 1553 messages: 15,000
  - File size: 5.2 MB
```

### Step 3: Inspect the Generated Data
```bash
# View statistics
ch10gen inspect my_first_flight.c10 --stats

# Export first 100 messages to CSV
ch10gen export my_first_flight.c10 --format csv --limit 100 --out preview.csv
```

## Understanding the Data Flow

```mermaid
graph LR
    A[Scenario YAML] --> C[CH10 Generator]
    B[ICD YAML] --> C
    C --> D[Flight Simulator]
    D --> E[1553 Messages]
    E --> F[CH10 File]
    
    style A fill:#e8f5e9
    style B fill:#e8f5e9
    style F fill:#fff3e0
```

### What's in a Scenario?
The scenario defines your flight profile:
```yaml
name: "Quick Demo Flight"
duration_s: 300
profile:
  segments:
    - type: climb
      to_altitude_ft: 10000
      duration_s: 120
    - type: cruise
      altitude_ft: 10000
      duration_s: 180
```

### What's in an ICD?
The ICD defines your 1553 messages:
```yaml
bus: A
messages:
  - name: NAVIGATION
    rate_hz: 50
    rt: 10
    tr: BC2RT
    sa: 1
    wc: 8
    words:
      - name: altitude
        src: flight.altitude_ft
        encode: bnr16
```

## Interactive Mode (GUI)

Launch the CH10 Studio application for a visual interface:

```bash
# Launch the GUI
cd ch10-studio
npm run tauri dev

# Or use the installer
./ch10-studio-installer.exe
```

![CH10 Studio Screenshot](images/studio-screenshot.png)

## Common Use Cases

### 1. Testing a CH10 Reader
```bash
# Generate predictable test data
ch10gen build \
    --scenario scenarios/test_pattern.yaml \
    --icd icd/simple_nav.yaml \
    --out test_data.c10 \
    --seed 42  # Reproducible output
```

### 2. Simulating Flight Test Data
```bash
# Create realistic flight test data
ch10gen build \
    --scenario scenarios/flight_test.yaml \
    --icd icd/full_avionics.yaml \
    --out flight_test.c10 \
    --duration 3600 \
    --err.parity 0.01  # 1% parity errors
```

### 3. Stress Testing
```bash
# High-rate message generation
ch10gen build \
    --scenario scenarios/stress_test.yaml \
    --icd icd/high_rate.yaml \
    --out stress_test.c10 \
    --packet-bytes 65536  # Large packets
```

## Creating Your Own Scenarios

### Simple Climb and Cruise
```yaml
# my_scenario.yaml
name: "My Custom Flight"
duration_s: 600
seed: 123

profile:
  base_altitude_ft: 2000
  segments:
    - type: climb
      to_altitude_ft: 15000
      ias_kt: 250
      duration_s: 300
      
    - type: cruise
      altitude_ft: 15000
      mach: 0.5
      duration_s: 300
```

### Combat Maneuvers
```yaml
# combat_scenario.yaml
name: "Fighter Training"
duration_s: 900

profile:
  segments:
    - type: takeoff
      duration_s: 30
      
    - type: combat_turn
      bank_deg: 60
      g_force: 4.0
      heading_change_deg: 180
      duration_s: 45
      
    - type: vertical_climb
      climb_rate_fpm: 6000
      duration_s: 30
```

## Troubleshooting

### Issue: "Module not found"
```bash
# Ensure you're in the project directory
cd ch10-1553-flightgen

# Reinstall dependencies
pip install -r requirements.txt
```

### Issue: "Invalid YAML"
```bash
# Validate your YAML files
ch10gen check-icd your_icd.yaml
ch10gen check-scenario your_scenario.yaml
```

### Issue: "Memory error on large files"
```bash
# Use streaming mode for large files
ch10gen build --streaming \
    --scenario large_scenario.yaml \
    --icd complex_icd.yaml \
    --out large_file.c10
```

## Next Steps

Now that you've generated your first CH10 file:

1. **Explore the Examples**: Check out `scenarios/` and `icd/` directories
2. **Read the Documentation**: 
   - [Configuration Guide](CONFIGURATION.md) - Detailed YAML options
   - [Architecture Overview](ARCHITECTURE.md) - How it all works
   - [Operations Manual](OPERATIONS.md) - Advanced CLI usage
3. **Join the Community**: Report issues and contribute on GitHub

## Pro Tips

1. **Use Seeds for Reproducibility**: Always specify `--seed` when you need consistent output
2. **Start Small**: Test with short durations first, then scale up
3. **Monitor Performance**: Use `--verbose` to see detailed progress
4. **Validate Often**: Run `validate` after each generation to catch issues early
5. **Export for Analysis**: Use the `export` command to inspect data in Excel/CSV

## Getting Help

- **Documentation**: Full docs in the `docs/` directory
- **Examples**: Working examples in `scenarios/` and `icd/`
- **Issues**: [GitHub Issues](https://github.com/yourusername/ch10-1553-flightgen/issues)
- **Discord**: [Join our community](https://discord.gg/example)

---

**Congratulations!** You're now ready to generate realistic CH10 files with 1553 flight test data!
