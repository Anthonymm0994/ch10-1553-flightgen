# Output Directory

This directory contains generated CH10 files and related outputs from the CH10 Generator.

## Sample CH10 Files

### Available Files
- `tshark_test.ch10` - Test file validated with TShark/Wireshark
- `test_output.c10` - Basic test output file

### File Formats
- `.ch10` / `.c10` - IRIG-106 Chapter 10 data files
- `.json` - Metadata and configuration exports
- `.pcap` - Wireshark-compatible packet captures
- `.jsonl` - Timeline data (JSON Lines format)

## Generating New Files

### Basic Generation
```bash
python -m ch10gen build \
    --scenario ../scenarios/test_scenario.yaml \
    --icd ../icd/nav_icd.yaml \
    --out new_file.ch10 \
    --duration 60
```

### With Bitfield Packing
```bash
python -m ch10gen build \
    --scenario ../scenarios/bitfield_test.yaml \
    --icd ../icd/bitfield_example.yaml \
    --out bitfield_output.ch10 \
    --duration 30
```

### With Error Injection
```bash
python -m ch10gen build \
    --scenario ../scenarios/test_scenario.yaml \
    --icd ../icd/nav_icd.yaml \
    --out error_test.ch10 \
    --errors ../scenarios/error_config.yaml \
    --duration 60
```

## Validating Files

### Using ch10gen
```bash
python -m ch10gen validate test_output.c10
```

### Using TShark
```bash
# Requires Wireshark installation
tshark -r test_output.c10 -c 10
```

### Export to PCAP
```bash
python -m ch10gen export test_output.c10 --format pcap --out test.pcap
```

## File Structure

CH10 files contain:
- **TMATS**: Telemetry Attributes Transfer Standard metadata
- **Time packets**: IRIG-106 time synchronization
- **1553 packets**: MIL-STD-1553 bus data
- **Data packets**: Encoded flight parameters

## Reports

Generated reports in this directory:
- `TEST_REPORT.md` - Test execution results
- `QUALITY_REPORT.md` - Code quality metrics
- `TEST_MATRIX.md` - Test coverage matrix

## Cleanup

To clean generated files:
```bash
# Remove all CH10 files
rm *.ch10 *.c10

# Remove all outputs
rm *.json *.pcap *.jsonl
```

## Notes

- Files in this directory are typically temporary/test outputs
- Production files should be stored in appropriate project directories
- Large files (>100MB) should not be committed to version control
