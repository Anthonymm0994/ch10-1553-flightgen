# TShark Validation Test Suite

## Overview

This test suite uses Wireshark's `tshark` CLI tool as an **independent validator** for our CH10 files. This is our PRIMARY validation mechanism - we trust tshark as the authoritative decoder.

## Quick Start

### 1. Install Wireshark
Download from: https://www.wireshark.org/

### 2. Run Validation

```bash
# Simple validation
python tests/run_tshark_validation.py out/test.ch10

# Run tests
export WITH_TSHARK=1
pytest tests/test_tshark_comprehensive.py -v

# Check tshark installation
python tests/test_tshark_comprehensive.py --check
```

## Test Files

- `test_tshark_validation.py` - Basic tshark integration tests
- `test_tshark_comprehensive.py` - Validation suite
- `run_tshark_validation.py` - Standalone validation script

## What We Validate

### Primary (via TShark)
1. **File Readability** - Can tshark open and parse the file?
2. **Packet Structure** - Are CH10 packets properly formatted?
3. **1553 Messages** - Are MIL-STD-1553 messages present and valid?
4. **Data Integrity** - Can tshark extract all expected fields?

### Secondary (Supporting Tests)
- Bitfield packing logic
- BNR16 encoding
- ICD validation
- Timing accuracy

## Environment Variables

```bash
# Enable tshark tests
export WITH_TSHARK=1

# Custom tshark path (optional)
export TSHARK="/path/to/tshark"

# Verbose output
export TSHARK_VERBOSE=1

# CH10 Lua dissector (optional)
export TSHARK_LUA="/path/to/ch10.lua"
```

## Windows Setup

```cmd
# Windows Command Prompt
set WITH_TSHARK=1
set TSHARK=C:\Program Files\Wireshark\tshark.exe

# Git Bash
export TSHARK="/c/Program Files/Wireshark/tshark.exe"
```

## Example Output

```
$ python tests/run_tshark_validation.py out/test.ch10
Validating: test.ch10
Using tshark: C:/Program Files/Wireshark/tshark.exe
------------------------------------------------------------
Test 1: File readability...
  PASS: File is readable

Test 2: Packet analysis...
  Found 4 packets (2428 bytes total)

Test 3: 1553 message detection...
  Found 4 CH10 packets
  PASS: MIL-STD-1553 messages detected

Test 4: Field extraction...
  Sample frames:
    Frame 1: 28 bytes
    Frame 2: 36 bytes
    Frame 3: 2328 bytes
    Frame 4: 36 bytes

============================================================
VALIDATION COMPLETE: SUCCESS
============================================================
```

## TShark Commands Reference

```bash
# Basic file reading
tshark -r file.ch10

# Count packets
tshark -r file.ch10 -q -z io,stat,0

# Filter CH10 packets
tshark -r file.ch10 -Y ch10

# Extract specific fields
tshark -r file.ch10 -T fields -e frame.number -e frame.len

# With Lua dissector
tshark -r file.ch10 -X lua_script:ch10.lua

# Export as JSON
tshark -r file.ch10 -T json > output.json
```

## Continuous Integration

```yaml
# GitHub Actions example
- name: Install Wireshark
  run: |
    sudo apt-get update
    sudo apt-get install -y tshark
    
- name: Run TShark Validation
  env:
    WITH_TSHARK: 1
  run: |
    python tests/run_tshark_validation.py out/*.ch10
    pytest tests/test_tshark_comprehensive.py -v
```

## Troubleshooting

### TShark not found
- Check installation: `tshark --version`
- Add to PATH or set TSHARK environment variable
- On Windows: Usually in `C:\Program Files\Wireshark\`

### Permission denied (Linux)
```bash
sudo usermod -a -G wireshark $USER
# Log out and back in
```

### CH10 not recognized
- Install CH10 Lua dissector
- Place in Wireshark plugins directory
- Verify with: `tshark -G protocols | grep -i ch10`

## Best Practices

1. **Always validate before release** - Run tshark validation on all generated files
2. **Use in Build Pipelines** - Automate validation in your build process
3. **Keep test files small** - For faster validation
4. **Log commands** - For debugging and reproducibility
5. **Version control** - Track which tshark version was used

## Summary

TShark validation provides:
- **Independent verification** - Not relying on our own code
- **Industry standard** - Wireshark is the de facto packet analyzer
- **Complete checks** - Packet structure, timing, data integrity
- **Easy integration** - Simple commands, clear output
- **Cross-platform** - Works on Windows, Linux, macOS

This is our **primary quality gate** - if tshark says our CH10 files are valid, we can be confident they'll work with other tools.
