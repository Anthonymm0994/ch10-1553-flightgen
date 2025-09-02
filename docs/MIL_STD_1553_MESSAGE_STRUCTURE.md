# IRIG-106 Chapter 10 File Structure

This document provides a comprehensive overview of IRIG-106 Chapter 10 file structure and packet formats based on implementation details discovered during development.

## Overview

IRIG-106 Chapter 10 is a telemetry standard for recording and playback of flight test data. CH10 files contain multiple data types including TMATS, time data, and 1553 messages organized in a structured packet format.

## CH10 Packet Types

### 1. TMATS (Test and Maintenance Data)
- **Data Type**: 0x01
- **Channel ID**: 0x000
- **Purpose**: Test and maintenance data for system configuration
- **Structure**: TMATS XML data

### 2. Time Data (Format 1)
- **Data Type**: 0x11
- **Channel ID**: 0x001
- **Purpose**: Time synchronization and reference
- **Structure**: CSDW + Time payload (IRIG-B format)

### 3. 1553 Data (Format 1)
- **Data Type**: 0x19
- **Channel ID**: 0x002+
- **Purpose**: MIL-STD-1553 message data
- **Structure**: CSDW + IPDH + 1553 message data

### 4. Computer-Generated (Format 2)
- **Data Type**: 0x02
- **Channel ID**: Variable
- **Purpose**: Recording events and system messages
- **Structure**: CSDW + Event data

## Word Structure

### Command Word (16 bits)

```
| 15 | 14 | 13 | 12 | 11 | 10 | 09 | 08 | 07 | 06 | 05 | 04 | 03 | 02 | 01 | 00 |
| RT Address (5) | T/R | Subaddress (5) | Word Count (5) | Parity |
```

**Field Descriptions:**
- **RT Address (bits 15-11)**: Remote Terminal address (0-31)
- **T/R (bit 10)**: Transfer direction (0=RT to BC, 1=BC to RT)
- **Subaddress (bits 9-5)**: Subaddress (0-31)
- **Word Count (bits 4-0)**: Number of data words (0-31, where 0 means 32)
- **Parity (bit 0)**: Odd parity bit

**Special Cases:**
- **Subaddress 0**: Mode codes (no data words)
- **Subaddress 31**: Broadcast subaddress
- **Word Count 0**: Indicates 32 data words

### Status Word (16 bits)

```
| 15 | 14 | 13 | 12 | 11 | 10 | 09 | 08 | 07 | 06 | 05 | 04 | 03 | 02 | 01 | 00 |
| RT Address (5) | Message Error | Instrumentation | Service Request | Reserved | Busy | Subsystem Flag | Dynamic Bus Control | Terminal Flag | Parity |
```

**Field Descriptions:**
- **RT Address (bits 15-11)**: Remote Terminal address (0-31)
- **Message Error (bit 15)**: Message error detected
- **Instrumentation (bit 14)**: Instrumentation bit
- **Service Request (bit 13)**: Service request pending
- **Reserved (bit 12)**: Reserved bit
- **Busy (bit 11)**: Terminal busy
- **Subsystem Flag (bit 10)**: Subsystem flag
- **Dynamic Bus Control (bit 9)**: Dynamic bus control accepted
- **Terminal Flag (bit 8)**: Terminal flag
- **Parity (bit 0)**: Odd parity bit

### Data Word (16 bits)

```
| 15 | 14 | 13 | 12 | 11 | 10 | 09 | 08 | 07 | 06 | 05 | 04 | 03 | 02 | 01 | 00 |
| Data (15 bits) | Parity |
```

**Field Descriptions:**
- **Data (bits 15-1)**: 15-bit data payload
- **Parity (bit 0)**: Odd parity bit

## Message Encoding

### Binary Number Representation (BNR)
- **Format**: Signed binary with scale and offset
- **Range**: -32,768 to 32,767 (16-bit signed)
- **Usage**: Continuous values like altitude, airspeed

### Binary Coded Decimal (BCD)
- **Format**: 4-bit BCD digits
- **Range**: 0-9 per digit
- **Usage**: Discrete values like time, counters

### Unsigned 16-bit (U16)
- **Format**: 16-bit unsigned integer
- **Range**: 0 to 65,535
- **Usage**: Counters, flags, discrete values

### Signed 16-bit (I16)
- **Format**: 16-bit signed integer (two's complement)
- **Range**: -32,768 to 32,767
- **Usage**: Signed values, differences

### Float32 Split
- **Format**: 32-bit IEEE 754 float split into two 16-bit words
- **Word Order**: LSW-MSW or MSW-LSW
- **Usage**: High-precision floating-point values

## IRIG-106 Chapter 10 Integration

### Channel Structure
- **Channel 0**: TMATS (Test and Maintenance Data)
- **Channel 1**: Time Data (Format 1)
- **Channel 2+**: 1553 Data (Format 1)

### Packet Structure
```
| CSDW | IPDH | Message Data |
```

**Field Descriptions:**
- **CSDW**: Channel-Specific Data Word (4 bytes)
- **IPDH**: Intra-Packet Data Header (18 bytes)
- **Message Data**: 1553 message payload

### CSDW Fields
- **Channel ID**: Channel identifier
- **Data Type**: 0x19 for 1553-F1
- **Time Source**: Time reference source
- **Time Format**: Time format (0=IRIG-B)

### IPDH Fields
- **Sync**: Synchronization pattern (0xEB25)
- **Message Length**: Total message length
- **Time Tag**: Time tag bits
- **Bus**: Bus identifier
- **Message Count**: Number of messages in packet

## Message Validation

### Length Validation
- **Command Word**: 1 word (16 bits)
- **Data Words**: 0-32 words (0-512 bits)
- **Status Word**: 1 word (16 bits)
- **Total**: 2-34 words (32-544 bits)

### Parity Validation
- **Odd Parity**: All words must have odd parity
- **Calculation**: XOR of all bits in word
- **Error Detection**: Parity errors indicate transmission issues

### Address Validation
- **RT Address**: Must be 0-31
- **Subaddress**: Must be 0-31
- **Word Count**: Must be 0-31 (0 means 32)

## Error Handling

### Common Errors
- **Parity Error**: Odd parity violation
- **Message Error**: Message format error
- **Busy**: Terminal busy condition
- **Service Request**: Service request pending

### Error Injection
- **Parity Errors**: Random bit flips
- **Message Errors**: Invalid message format
- **Timeout Errors**: Message timeout
- **Busy Errors**: Terminal busy condition

## Implementation Notes

### PyChapter10 Integration
- **Message Parsing**: PyChapter10 provides raw message data
- **Manual Decoding**: Command word fields must be manually decoded
- **Little-Endian**: Multi-byte fields are little-endian
- **Length Setting**: Message length must be manually set

### Data Generation
- **Random Values**: Generated based on field constraints
- **Realistic Ranges**: Values within expected operational ranges
- **Encoding Validation**: All values validated before encoding
- **Round-trip Testing**: Encode/decode validation for data integrity

### Performance Considerations
- **Message Rate**: Up to 1 MHz per bus
- **Packet Size**: 65,536 bytes target
- **Time Packets**: 1 Hz minimum rate
- **Memory Usage**: Streaming for large files

## Examples

### Basic BC2RT Message
```
Command Word: 0x5408  (RT=10, T/R=1, SA=1, WC=8)
Data Words:   8 words of data
Status Word:  0x5000  (RT=10, no errors)
```

### RT2BC Response
```
Command Word: 0x5408  (RT=10, T/R=0, SA=1, WC=8)
Data Words:   8 words of data
Status Word:  0x5000  (RT=10, no errors)
```

### Mode Code Message
```
Command Word: 0x5400  (RT=10, T/R=1, SA=0, WC=0)
Status Word:  0x5000  (RT=10, no errors)
```

### Broadcast Message
```
Command Word: 0x5F08  (RT=31, T/R=1, SA=1, WC=8)
Data Words:   8 words of data
(No status word for broadcast)
```

## Validation Tools

### Internal Validation
- **ICD Validation**: Message structure validation
- **CH10 Validation**: File format validation
- **Message Validation**: Individual message validation

### External Validation
- **PyChapter10**: IRIG-106 compliant parsing
- **c10-tools**: Command-line validation tools
- **Wireshark**: Network protocol analysis

### Test Coverage
- **Unit Tests**: Individual function testing
- **Integration Tests**: End-to-end testing
- **Performance Tests**: Large file testing
- **Error Injection Tests**: Error handling validation

## References

- **MIL-STD-1553B**: Digital Time Division Command/Response Multiplex Data Bus
- **IRIG-106**: Telemetry Standards
- **PyChapter10**: Python IRIG-106 library
- **c10-tools**: Command-line CH10 tools
