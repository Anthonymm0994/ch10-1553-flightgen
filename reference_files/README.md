# Reference Ch10 Files with 1553 Messages

This directory contains reference Chapter 10 files with MIL-STD-1553 messages for validation and testing purposes.

## Current Files

### TTC-1553_107_132248.ch10
- **Source**: [elastickent/mil-std-1553-es](https://github.com/elastickent/mil-std-1553-es) repository
- **Size**: ~12MB
- **Description**: Contains eight 1553 channels with METS data
- **Date**: April 20, 2009
- **Usage**: Reference file for 1553 message structure and encoding
- **Analysis**: See [ANALYSIS_REPORT.md](ANALYSIS_REPORT.md) for detailed analysis

## Comprehensive List of Available Ch10 Files with 1553 Data

### IRIG 106 Official Sample Data Files
- **Website**: https://www.irig106.org/wiki/sample_data_files
- **Contact**: bob@irig106.org (requires username/password)
- **Available Files**:

#### Real Flight/Test Recordings
- **Enertec_12042009_19040920.ch10** (312 MB)
  - Source: Zodiac/Enertec VS1500 recorder
  - Contains: 2 MIL-STD-1553 bus channels (Channel IDs 6 and 7, ~2,571 messages each)
  - Additional: Dual NTSC video streams and IRIG-B time codes
  - Date: April 2009

- **Heim-GSS-1_00970000_09030600.ch10** (514 MB)
  - Source: Zodiac/Heim GSS recorder (firmware 2.27)
  - Contains: 8 MIL-STD-1553B bus channels (Channels 87–94, 372 message packets each)
  - Additional: PCM streams, video channels, UART, Ethernet, analog, ARINC-429
  - Date: March 2009

- **Smartronix_4PCM_5M_1553.ch10** (774 MB)
  - Source: Smartronix IMUX-G2 recorder
  - Contains: 1 MIL-STD-1553 channel (Channel 31, ~9,630 messages)
  - Additional: 4 PCM telemetry streams (5 Mbps each)
  - Date: October 31, 2018

- **TTC-1553_107_132248.ch10** (11.9 MB) ✅ **AVAILABLE**
  - Source: Teletronics/Curtiss-Wright MUX-3005R recorder
  - Contains: 8 separate MIL-STD-1553 bus recordings (697 message packets each)
  - Duration: ~13 seconds
  - Date: April 2009

- **Wideband-Systems_1553-AR429-64DISC-IRIG11.ch10** (14.1 MB)
  - Source: Wideband Systems DRS8500X recorder
  - Contains: 4 MIL-STD-1553 channels (Channels 10–13, 60 messages each)
  - Additional: 16 ARINC-429 channels, 2 discrete I/O channels
  - Format: IRIG 106-11
  - Date: January 2018

- **Wyle_24042009_15425242.ch10** (234 MB)
  - Source: Wyle Labs G2 recorder
  - Contains: 1 MIL-STD-1553 bus channel (Channel 31, 52 messages)
  - Additional: 4 PCM streams, 2 analog channels, MPEG-2 video, Ethernet
  - Date: April 24, 2009

#### Synthetic/Test Files
- **Mil1553_message_types.ch10** (2.4 KB)
  - Source: Data Bus Tools FLIDAS software
  - Contains: 5 MIL-STD-1553 message packets demonstrating different message types
  - Purpose: Demonstrates BC→RT, RT→BC, RT→RT transfers
  - Status: Small synthetic file for testing

#### Additional Files
- `Record 01 - TxMDR - short - standalone - 20151210172338_r0002f000.ch10` - Standard Chapter 10 recording with various data types including 1553 messages
- `Record 01 - Chapter7 Telemetry - Short.ch10` - Chapter 7 PCM data stream

### Bob Baggerman's Repositories
- **irig106lib**: https://github.com/bbaggerman/irig106lib
  - Open-source library for reading/writing IRIG 106 Chapter 10 files
  - Includes modules for decoding MIL-STD-1553 messages
  - Code examples for handling 1553 data in Ch10 files

- **irig106utils**: https://github.com/bbaggerman/irig106utils
  - Utility programs for working with Chapter 10 files
  - Includes `idmp1553.exe` for reading and dumping 1553 messages

### Other Useful Resources
- **IRIG 106 Handbook**: https://www.irig106.org/wiki/ch10_handbook:data_file_interpretation
- **MIL-STD-1553 Data Format Documentation**: https://www.irig106.org/wiki/ch10_handbook:mil-std-1553_data
- **Ch10Tools_v2.exe**: EMC's Chapter 10 packet viewer and validator (may be outdated)

## Value of Additional Files

### High-Value Files for Your Project

1. **Enertec_12042009_19040920.ch10** (312 MB)
   - **Why Valuable**: Dual 1553 channels with video data - great for multi-channel testing
   - **Use Case**: Testing dual bus scenarios and video+1553 combinations

2. **Heim-GSS-1_00970000_09030600.ch10** (514 MB)
   - **Why Valuable**: 8 MIL-STD-1553B channels with comprehensive avionics data
   - **Use Case**: Testing complex multi-channel scenarios with ARINC-429, PCM, video

3. **Smartronix_4PCM_5M_1553.ch10** (774 MB)
   - **Why Valuable**: High message count (~9,630) with PCM telemetry
   - **Use Case**: Testing high-throughput scenarios and PCM+1553 combinations

4. **Wideband-Systems_1553-AR429-64DISC-IRIG11.ch10** (14.1 MB)
   - **Why Valuable**: IRIG 106-11 format with ARINC-429 and discrete I/O
   - **Use Case**: Testing newer IRIG format and mixed avionics protocols

5. **Mil1553_message_types.ch10** (2.4 KB)
   - **Why Valuable**: Small synthetic file demonstrating all message types
   - **Use Case**: Quick validation and message type testing

## Usage Notes

1. The `TTC-1553_107_132248.ch10` file in this directory can be used as a reference for:
   - Validating 1553 message encoding
   - Testing Ch10 file parsing
   - Comparing output format with known good files

2. To access additional sample files from IRIG 106:
   - Contact Bob Baggerman at bob@irig106.org
   - Request username and password for sample data access
   - Download files from the official IRIG 106 sample data page

3. These reference files should be used for:
   - Development and testing
   - Format validation
   - Compatibility verification
   - Educational purposes

## IRIG-B Time Code Focus

Based on your focus on IRIG-B time codes, here are the most relevant files from the comprehensive list:

### Files with IRIG-B Time Codes
1. **Enertec_12042009_19040920.ch10** (312 MB)
   - Contains: 2 MIL-STD-1553 channels + dual NTSC video streams + **IRIG-B time codes**
   - Value: Shows 1553 data synchronized with IRIG-B time

2. **Heim-GSS-1_00970000_09030600.ch10** (514 MB)
   - Contains: 8 MIL-STD-1553B channels + **IRIG-B time** + comprehensive avionics
   - Value: Multi-channel 1553 with IRIG-B synchronization

3. **Wideband-Systems_1553-AR429-64DISC-IRIG11.ch10** (14.1 MB)
   - Contains: 4 MIL-STD-1553 channels + **IRIG-B time** + ARINC-429 + discrete I/O
   - Value: IRIG 106-11 format with IRIG-B time (smaller file size)

4. **Calculex PCM Files** (Various sizes)
   - **Calculex-PCM200_12052009_212313**: 200 Kbps PCM + **IRIG-B time**
   - **Calculex-PCM5_12052009_211602**: 5 Mbps PCM + **IRIG-B time**
   - **Calculex-PCM10_12052009_211910**: 10 Mbps PCM + **IRIG-B time**
   - **Calculex-PCM20_12052009_212115**: 20 Mbps PCM + **IRIG-B time**

### Access Status
- **Currently Available**: TTC-1553_107_132248.ch10 (12MB) - ✅ Downloaded and analyzed
- **Requires Authentication**: All IRIG 106 official files require username/password from bob@irig106.org
- **Synthetic Files**: Mil1553_message_types.ch10 (2.4 KB) - Not publicly accessible

## Recommended Next Steps

1. **Contact IRIG 106**: Request access to the official sample data repository (bob@irig106.org)
2. **Prioritize IRIG-B Files**: Focus on Wideband-Systems (14.1 MB) and Calculex files for IRIG-B time code examples
3. **Analyze Time Synchronization**: Compare IRIG-B time patterns across different vendors
4. **Test Compatibility**: Validate your generator's IRIG-B time handling against reference files

## File Validation

You can validate the Ch10 files using:
- Your project's built-in validation tools
- Bob Baggerman's irig106lib utilities
- Wireshark with appropriate plugins
- Custom validation scripts

## License and Usage

Please respect the licensing terms of the original sources when using these reference files. Most are provided for educational and development purposes.
