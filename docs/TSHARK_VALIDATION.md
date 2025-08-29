# TShark Validation Guide

This document explains how to use Wireshark's `tshark` CLI tool as the primary validation mechanism for CH10 files generated b CH10Gen.

## Overview

TShark provides an independent decoder for CH10 files, allowing us to verify that our generated files are correctly formatted and contain the expected 1553 messages. This is our PRIMARY validation approach - we trust tshark as the authoritative decoder.

## Prerequisites

### 1. Install Wireshark
Download and install Wireshark from: https://www.wireshark.org/

Ensure `tshark` is in your PATH:
```bash
tshark --version
```

### 2. Install CH10 Lua Dissector
Get the CH10 Lua dissector from:
https://github.com/diarmuidcwc/LuaDissectors/blob/master/ch10.lua

Place it in your Wireshark plugins directory:
- Windows: `%APPDATA%\Wireshark\plugins\`
- Linux: `~/.config/wireshark/plugins/`
- macOS: `~/.config/wireshark/plugins/`

## Running Validation Tests

### Enable TShark Tests
```bash
# Enable tshark validation
export WITH_TSHARK=1

# Optional: Specify paths
export TSHARK=/path/to/tshark
export TSHARK_LUA=/path/to/ch10.lua

# Run tests
pytest tests/test_tshark_validation.py -v
```

### Windows
```cmd
set WITH_TSHARK=1
pytest tests/test_tshark_validation.py -v
```

## TShark Commands Used

### Basic CH10 File Reading
```bash
tshark -r sample.ch10 -X lua_script:ch10.lua
```

### Extract 1553 Messages
```bash
tshark -r sample.ch10 -X lua_script:ch10.lua -Y 1553 \
    -T fields \
    -e frame.number \
    -e ch10.datatype \
    -e 1553.rt \
    -e 1553.tr \
    -e 1553.sa \
    -e 1553.wc \
    -e 1553.data
```

### Count Messages by RT
```bash
tshark -r sample.ch10 -X lua_script:ch10.lua -Y 1553 \
    -T fields -e 1553.rt | sort | uniq -c
```

### Filter Specific RT/SA
```bash
tshark -r sample.ch10 -X lua_script:ch10.lua \
    -Y "1553.rt == 5 && 1553.sa == 1"
```

## What We Validate

### Primary Checks (via TShark)
1. **File Readability** - Can tshark open and parse the file?
2. **Message Count** - Does the number of 1553 messages match expectations?
3. **RT/SA Values** - Are the correct RT and SA values present?
4. **Word Counts** - Do messages have the expected word count?
5. **Data Integrity** - Can tshark decode all message data?
6. **Timing** - Are messages at the expected rates?

### Secondary Checks (Supporting Tests)
- Bitfield packing/unpacking logic
- BNR16 encoding/decoding
- YAML configuration parsing
- ICD validation

## Test Organization

```
tests/
├── test_tshark_validation.py   # PRIMARY - TShark validation
├── test_bitfield_packing.py    # Secondary - Bitfield logic
├── test_icd.py                  # Secondary - ICD parsing
└── test_integration_spec.py    # Secondary - End-to-end tests
```

## Continuous Integration

For build pipelines:

```yaml
# .github/workflows/test.yml
- name: Install Wireshark
  run: |
    sudo apt-get update
    sudo apt-get install -y tshark
    
- name: Get CH10 Dissector
  run: |
    wget https://raw.githubusercontent.com/diarmuidcwc/LuaDissectors/master/ch10.lua
    mkdir -p ~/.config/wireshark/plugins
    cp ch10.lua ~/.config/wireshark/plugins/
    
- name: Run Validation
  env:
    WITH_TSHARK: 1
  run: |
    pytest tests/test_tshark_validation.py -v
```

## Troubleshooting

### TShark Not Found
```bash
# Check if tshark is installed
which tshark

# Add to PATH if needed
export PATH=$PATH:/usr/local/bin
```

### Lua Dissector Not Loading
```bash
# Check plugin directory
tshark -G plugins

# Verify dissector is loaded
tshark -G protocols | grep -i ch10
```

### Permission Issues
```bash
# On Linux, may need to add user to wireshark group
sudo usermod -a -G wireshark $USER
```

## Example Output

Successful validation:
```
$ WITH_TSHARK=1 pytest tests/test_tshark_validation.py -v
=================== test session starts ===================
tests/test_tshark_validation.py::TestTSharkValidation::test_ch10_file_readable PASSED
tests/test_tshark_validation.py::TestTSharkValidation::test_1553_message_count PASSED
tests/test_tshark_validation.py::TestTSharkValidation::test_1553_rt_sa_values PASSED
tests/test_tshark_validation.py::TestTSharkValidation::test_1553_word_count PASSED
=================== 4 passed in 2.34s ===================
```

## Performance Considerations

- TShark validation is slower than unit tests
- Run as part of integration tests, not unit tests
- Consider sampling for large files (use `-c` option)
- Cache validated files to avoid re-testing

## Best Practices

1. **Always run tshark validation before release**
2. **Use tshark as the authoritative decoder**
3. **Log tshark commands for debugging**
4. **Keep test files small for fast validation**
5. **Version-lock the Lua dissector for consistency**
