# Dependencies and External Tools

This document details the specific MIL-STD-1553 and IRIG-106 Chapter 10 tools, libraries, and projects that CH10Gen leverages, along with their exact roles in our implementation.

## Core Dependencies

### PyChapter10
**Source**: https://pypi.org/project/pychapter10/  
**License**: Open Source  
**Our Usage**: Primary library for IRIG-106 Chapter 10 file operations

PyChapter10 is the foundational library that CH10Gen builds upon. We use it for:

- **CH10 File Writing**: Creating spec-compliant IRIG-106 files
  - `chapter10.C10` - Main file handler class
  - `chapter10.Packet` - Packet structure and header management
  
- **1553 Message Formatting**: 
  - `chapter10.ms1553.MS1553F1` - Format 1 1553 message packets
  - Handles intra-packet headers and data word organization
  
- **Time Management**:
  - `chapter10.time.TimeF1` - Format 1 time packets
  - IPTS (IRIG Precision Time Stamp) generation
  
- **TMATS Generation**:
  - `chapter10.message.MessageF0` - TMATS (Telemetry Attributes Transfer Standard) packets
  - Metadata and channel configuration

**What it provides**: Low-level CH10 packet formatting, CRC calculation, file structure management, and spec compliance. Without PyChapter10, we would need to implement the entire IRIG-106 specification from scratch.

### Chapter10 (C Library Heritage)

PyChapter10 is based on the C libraries:
- **i106lib** (Bob Baggerman): https://github.com/bbaggerman/irig106lib
- **libirig106** (ATAC fork): https://github.com/atac/libirig106

While we don't directly use these C libraries, PyChapter10 inherits their:
- Packet structure definitions
- CRC algorithms
- Binary format specifications
- Field ordering and alignment rules

## Standards and Specifications

### IRIG-106 Standard
**Source**: https://www.irig106.org/  
**Our Implementation**:
- Chapter 10 file format structure
- Packet header formats (24 bytes)
- Channel ID assignments
- Data packet types (especially Type 0x19 for 1553)
- Time synchronization requirements
- TMATS structure and syntax

### MIL-STD-1553B
**Specification**: MIL-STD-1553B (1978 with notices)  
**Our Implementation**:
- Command word structure (RT|T/R|SA|WC)
- Status word structure with error flags
- Data word formatting (16-bit)
- Message timing (4μs inter-message gap)
- RT address range (0-31)
- Subaddress range (0-31)
- Word count encoding (32 words = 0)

## Fallback Implementations

### Wire Reader (Custom Binary Parser)
**Location**: `ch10gen/wire_reader.py`  
**Purpose**: Direct binary CH10 parsing when PyChapter10 fails

We developed this as a fallback because PyChapter10 sometimes struggles with:
- Non-standard packet formats
- Corrupted headers
- Unknown packet types
- Files from certain vendors

The wire reader directly parses:
- 24-byte packet headers
- MS1553F1 intra-packet headers
- 1553 message structures
- Time packets

## Analysis and Export Tools

### PCAP Export
**Implementation**: `ch10gen/pcap_export.py`  
**Leverages**: Standard PCAP file format for Wireshark compatibility

We implement PCAP generation to enable:
- Wireshark analysis of 1553 traffic
- Network-style packet inspection
- Integration with existing analysis workflows

The PCAP format follows:
- Global header with magic number 0xa1b2c3d4
- Per-packet headers with timestamps
- UDP encapsulation on port 15553
- Custom payload format for 1553 messages

### Wireshark Integration
**Related Tool**: CH10 Lua Dissector  
**Source**: https://github.com/diarmuidcwc/LuaDissectors/blob/master/ch10.lua

While we don't include the Lua dissector directly, our PCAP export is designed to be compatible with it for enhanced Wireshark analysis.

## Validation Tools

### External Validators (Optional)
**Tools Referenced**:
- IRIG106 official utilities
- Vendor-specific validators

Our `validate-external` command can invoke:
- Third-party CH10 validators if installed
- Vendor tools for compliance checking
- Format verification utilities

## Related Projects (Not Direct Dependencies)

### Similar Synthetic Data Generators
- **IRIG 106 Synthetic Data Generator**: https://github.com/atac/SyntheticData
  - Similar goals but different implementation
  - We studied this for approach validation

### Hardware Simulators (Reference Only)
- **MIL-STD-1553 Bus Simulator**: https://github.com/ShubhankarKulkarni/MIL-STD-1553-Simulator
- **Open1553 FPGA Core**: https://github.com/johnathan-convertino-afrl/open1553
- **Flex1553 Teensy**: https://github.com/bsundahl1/Flex1553

These provide reference implementations for:
- Bus timing behavior
- Error injection patterns
- Message scheduling algorithms

## What We Built Ourselves

### Core Functionality (Not Leveraged from Others)
1. **Flight Profile Generator** - Physics-based flight simulation
2. **1553 Message Scheduler** - Major/minor frame organization
3. **BNR16 Encoder** - Binary Natural Representation encoding
4. **ICD Parser** - YAML-based message definitions
5. **Error Injection** - Realistic bus error simulation
6. **Bitfield Packing** - Efficient multi-parameter word packing
7. **CH10 Studio GUI** - Tauri-based graphical interface

### Why We Needed PyChapter10

Without PyChapter10, we would need to implement:
- 700+ pages of IRIG-106 specification
- Complex CRC algorithms
- Binary packet alignment rules
- TMATS syntax and structure
- Vendor-specific quirks and compatibility

PyChapter10 provides the foundation that lets us focus on:
- Realistic data generation
- User-friendly configuration
- Advanced features like bitfield packing
- Tooling and validation

## Installation Requirements

```bash
# Core dependency
pip install pychapter10

# Optional for enhanced functionality
pip install numpy  # For flight physics calculations
pip install pyyaml # For configuration parsing
pip install click  # For CLI interface
```

## License Compatibility

All leveraged tools are compatible with our MIT license:
- **PyChapter10**: Open source (permissive)
- **libirig106**: BSD-3-Clause
- **PCAP format**: Public domain
- **MIL-STD-1553**: US Government standard (public)
- **IRIG-106**: Range Commanders Council standard (public)

## Summary

CH10Gen strategically leverages:
1. **PyChapter10** as the core CH10 file handling library
2. **IRIG-106 and MIL-STD-1553B** standards for correctness
3. **PCAP format** for analysis tool compatibility
4. **Fallback parsers** for robustness

This allows us to focus on value-added features like realistic flight simulation, intuitive configuration, and tooling while ensuring spec compliance and industry compatibility.
