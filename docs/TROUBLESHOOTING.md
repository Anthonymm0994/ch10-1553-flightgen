# Troubleshooting Guide

This guide helps resolve common issues with the CH10 Generator.

## Table of Contents
- [Installation Issues](#installation-issues)
- [Generation Errors](#generation-errors)
- [Validation Problems](#validation-problems)
- [Performance Issues](#performance-issues)
- [Bitfield Packing Issues](#bitfield-packing-issues)
- [Platform-Specific Issues](#platform-specific-issues)

## Installation Issues

### Python Version Errors

**Problem:** `SyntaxError` or `ModuleNotFoundError` during installation

**Solution:**
```bash
# Check Python version (must be 3.10+)
python --version

# If wrong version, use specific Python
python3.10 -m pip install -r requirements.txt
python3.10 -m pip install -e .
```

### PyChapter10 Installation Fails

**Problem:** `ERROR: Could not find a version that satisfies the requirement pychapter10`

**Solution:**
```bash
# Install from GitHub directly
pip install git+https://github.com/atac/pychapter10.git

# Or install without PyChapter10 (limited validation)
pip install --no-deps -e .
```

### Missing Dependencies

**Problem:** `ImportError: No module named 'yaml'` or similar

**Solution:**
```bash
# Reinstall all dependencies
pip install -r requirements.txt --force-reinstall

# Check installed packages
pip list | grep -E "pyyaml|click|numpy"
```

## Generation Errors

### ICD Validation Failures

**Problem:** `ValueError: Invalid ICD: ...`

**Common Causes and Solutions:**

1. **Missing required fields**
   ```yaml
   # BAD - missing rate_hz
   - name: "NAV_DATA"
     rt: 1
     sa: 1
   
   # GOOD
   - name: "NAV_DATA"
     rate_hz: 10.0
     rt: 1
     sa: 1
     tr: "BC2RT"
     wc: 10
   ```

2. **Invalid RT/SA values**
   ```yaml
   # BAD - RT must be 0-31
   rt: 32
   
   # GOOD
   rt: 31
   ```

3. **Word count mismatch**
   ```yaml
   # BAD - wc doesn't match word definitions
   wc: 5
   words:
     - name: "word1"
     - name: "word2"  # Only 2 words defined!
   
   # GOOD
   wc: 2
   words:
     - name: "word1"
     - name: "word2"
   ```

### Scenario Loading Errors

**Problem:** `KeyError: 'flight_profile'` or similar

**Solution:**
```yaml
# Ensure scenario has required structure
name: "Test Scenario"
duration_s: 60
seed: 12345
flight_profile:
  segments:
    - type: "level"
      duration_s: 60
      altitude_ft: 15000
      airspeed_kts: 300
      heading_deg: 90
```

### File Write Errors

**Problem:** `PermissionError: [Errno 13] Permission denied`

**Solutions:**
```bash
# Check file is not open in another program
lsof my_file.ch10  # Linux/Mac
handle my_file.ch10  # Windows (requires SysInternals)

# Check directory permissions
ls -la output/  # Linux/Mac
icacls output  # Windows

# Use different output directory
ch10gen build --out /tmp/test.ch10 ...
```

## Validation Problems

### PyChapter10 Reader Errors

**Problem:** `ValueError: Unimplemented packet type` during validation

**Solution:**
```bash
# This is a known limitation - PyChapter10 doesn't support all packet types
# Use TShark validation instead:
export WITH_TSHARK=1
export TSHARK_PATH="C:/Program Files/Wireshark/tshark.exe"
python -m pytest tests/test_tshark_validation.py
```

### TShark Not Found

**Problem:** `TShark not found at path`

**Solutions:**
```bash
# Windows - typical paths
set TSHARK_PATH="C:\Program Files\Wireshark\tshark.exe"

# Linux
export TSHARK_PATH=/usr/bin/tshark

# macOS
export TSHARK_PATH=/Applications/Wireshark.app/Contents/MacOS/tshark

# Verify TShark works
"$TSHARK_PATH" -v
```

### Lua Dissector Not Working

**Problem:** TShark doesn't recognize CH10 files

**Solution:**
```bash
# Specify Lua dissector path
export TSHARK_LUA="wireshark/ch10.lua"

# Test with explicit Lua script
tshark -r test.ch10 -X lua_script:wireshark/ch10.lua
```

## Performance Issues

### Slow Generation

**Problem:** CH10 file generation takes too long

**Solutions:**

1. **Reduce packet size for better performance**
   ```python
   config = Ch10WriterConfig(
       target_packet_bytes=1024,  # Smaller packets
       time_packet_interval_s=10.0  # Less frequent time packets
   )
   ```

2. **Disable unnecessary features**
   ```bash
   # Skip TMATS generation
   ch10gen build --no-tmats ...
   
   # Skip timeline export
   ch10gen build --no-timeline ...
   ```

3. **Use faster writer backend**
   ```python
   # In code
   write_ch10_file(output_path, scenario, icd, 
                   writer_backend='wire')  # Faster than 'irig106'
   ```

### Memory Errors

**Problem:** `MemoryError` or system runs out of RAM

**Solutions:**

1. **Generate in chunks**
   ```bash
   # Generate 1-hour file in 10-minute chunks
   for i in {0..5}; do
     ch10gen build --start-offset $((i*600)) --duration 600 \
       --out chunk_$i.ch10 ...
   done
   ```

2. **Reduce message rates**
   ```yaml
   # Lower rates in ICD
   rate_hz: 1.0  # Instead of 100.0
   ```

3. **Increase system resources**
   ```bash
   # Windows - increase virtual memory
   # System Properties > Advanced > Performance > Virtual Memory
   
   # Linux - add swap
   sudo fallocate -l 4G /swapfile
   sudo chmod 600 /swapfile
   sudo mkswap /swapfile
   sudo swapon /swapfile
   ```

## Bitfield Packing Issues

### Mask/Shift Validation Errors

**Problem:** `ValueError: Mask 0xFFFF with shift 8 exceeds 16 bits`

**Solution:**
```yaml
# BAD - shifted mask exceeds 16 bits
mask: 0xFFFF
shift: 8  # 0xFFFF << 8 = 0xFFFF00 (exceeds 16 bits!)

# GOOD - mask fits after shift
mask: 0x00FF
shift: 8  # 0x00FF << 8 = 0xFF00 (fits in 16 bits)
```

### Bitfield Overlap Errors

**Problem:** `ValueError: Bitfield 'field2' overlaps with another field in word 0`

**Solution:**
```yaml
# BAD - overlapping bitfields
- name: "field1"
  mask: 0x00FF  # Bits 0-7
  shift: 0
  word_index: 0
- name: "field2"
  mask: 0x00FF  # Also bits 0-7!
  shift: 0
  word_index: 0

# GOOD - non-overlapping
- name: "field1"
  mask: 0x00FF  # Bits 0-7
  shift: 0
  word_index: 0
- name: "field2"
  mask: 0x00FF  # Bits 8-15
  shift: 8
  word_index: 0
```

### Value Doesn't Fit Mask

**Problem:** `ValueError: Value 256 doesn't fit in 8 bits (max=255)`

**Solution:**
```python
# Check value range before encoding
mask = 0x00FF  # 8 bits
max_value = mask  # 255
if value > max_value:
    value = max_value  # Clamp to maximum

# Or use scaling
scale = 255.0 / 1000.0  # Map 0-1000 to 0-255
```

## Platform-Specific Issues

### Windows

#### File Handle Issues
**Problem:** `PermissionError` when deleting temporary files

**Solution:**
```python
# Ensure files are closed
import gc
gc.collect()  # Force garbage collection

# Or skip test on Windows
@pytest.mark.skipif(sys.platform == "win32", 
                    reason="File cleanup issues on Windows")
```

#### Path Issues
**Problem:** Backslash/forward slash confusion

**Solution:**
```python
from pathlib import Path

# Use Path for cross-platform compatibility
file_path = Path("icd") / "test.yaml"
```

### Linux/macOS

#### Permission Denied
**Problem:** Can't execute built file

**Solution:**
```bash
# Make executable
chmod +x dist/ch10gen

# Check shebang line
head -1 ch10gen/__main__.py
# Should be: #!/usr/bin/env python3
```

#### Library Not Found
**Problem:** `error while loading shared libraries`

**Solution:**
```bash
# Check dependencies
ldd dist/ch10gen

# Set library path if needed
export LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH
```

## Debug Techniques

### Enable Verbose Output

```bash
# Maximum verbosity
ch10gen -vvv build ...

# Debug mode
ch10gen --debug build ...

# Dry run (no file creation)
ch10gen build --dry-run ...
```

### Python Debugging

```python
# Add to your script
import pdb; pdb.set_trace()  # Breakpoint

# Or use logging
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.debug(f"Value: {value}, Mask: {mask:#06x}")
```

### Check Intermediate Files

```bash
# Keep temporary files
ch10gen build --keep-temp ...

# Export JSON metadata
ch10gen build --export-json metadata.json ...

# Export timeline
ch10gen build --export-timeline timeline.jsonl ...
```

## Getting Help

### Diagnostic Information

When reporting issues, include:

```bash
# System info
python --version
pip list | grep ch10
uname -a  # Linux/Mac
systeminfo  # Windows

# Test command
ch10gen build --scenario scenarios/test_scenario.yaml \
  --icd icd/nav_icd.yaml --out test.ch10 --debug

# Error output (full traceback)
```

### Common Error Codes

| Error | Meaning | Solution |
|-------|---------|----------|
| Exit 1 | General error | Check error message |
| Exit 2 | Invalid arguments | Check command syntax |
| Exit 3 | File not found | Verify file paths |
| Exit 4 | Validation failed | Fix ICD/scenario |
| Exit 5 | Write failed | Check permissions |

### Log Files

```bash
# Enable logging
export CH10GEN_LOG_FILE=ch10gen.log
export CH10GEN_LOG_LEVEL=DEBUG

# View logs
tail -f ch10gen.log

# Search for errors
grep ERROR ch10gen.log
```

## Quick Fixes

### Reset Everything
```bash
# Clean build artifacts
rm -rf build/ dist/ *.egg-info __pycache__/

# Reinstall
pip uninstall ch10gen -y
pip install -e .

# Test
python -m ch10gen --version
```

### Minimal Test
```bash
# Create minimal ICD
cat > minimal.yaml << EOF
name: "Minimal"
bus: "A"
messages:
  - name: "TEST"
    rate_hz: 1.0
    rt: 1
    tr: "BC2RT"
    sa: 1
    wc: 1
    words:
      - name: "data"
        encode: "u16"
        const: 42
EOF

# Test generation
python -m ch10gen check-icd minimal.yaml
```

## Conclusion

Most issues can be resolved by:
1. Checking Python version and dependencies
2. Validating YAML syntax and structure
3. Ensuring proper file permissions
4. Using appropriate platform-specific commands

If problems persist after trying these solutions, please file an issue with:
- Full error message and traceback
- System information
- Minimal reproducible example
- Steps to reproduce
