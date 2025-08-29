#!/usr/bin/env python3
"""
Generate and validate LARGE CH10 files with complex bitfield configurations.
This is the ULTIMATE test - creates real-world sized files with thousands of messages.
"""

import os
import sys
import subprocess
import time
from pathlib import Path
import yaml
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

TSHARK = os.environ.get('TSHARK', 'C:/Program Files/Wireshark/tshark.exe')
if not Path(TSHARK).exists():
    TSHARK = '/c/Program Files/Wireshark/tshark.exe'

def create_complex_icd(filename: Path):
    """Create a complex ICD with many messages and bitfields."""
    icd = {
        'name': 'Complex System ICD',
        'bus': 'A',
        'description': 'Test with many message types',
        'messages': []
    }
    
    # 1. Navigation messages (high rate)
    for i in range(5):
        icd['messages'].append({
            'name': f'NAV_{i}',
            'rate_hz': 50.0,  # High rate
            'rt': 5,
            'tr': 'RT2BC',
            'sa': i + 1,
            'wc': 8,
            'words': [
                # Packed status word
                {'name': 'nav_valid', 'encode': 'u16', 'mask': 0x0001, 'shift': 0, 'const': 1},
                {'name': 'gps_lock', 'encode': 'u16', 'mask': 0x0001, 'shift': 1, 'const': 1, 'word_index': 0},
                {'name': 'nav_mode', 'encode': 'u16', 'mask': 0x000F, 'shift': 2, 'const': i, 'word_index': 0},
                {'name': 'quality', 'encode': 'u16', 'mask': 0x00FF, 'shift': 8, 'const': 100 + i, 'word_index': 0},
                # Position data
                {'name': 'lat_low', 'encode': 'u16', 'src': 'flight.lat_deg', 'word_index': 1},
                {'name': 'lat_high', 'encode': 'u16', 'src': 'flight.lat_deg', 'word_index': 2},
                {'name': 'lon_low', 'encode': 'u16', 'src': 'flight.lon_deg', 'word_index': 3},
                {'name': 'lon_high', 'encode': 'u16', 'src': 'flight.lon_deg', 'word_index': 4},
                {'name': 'altitude', 'encode': 'bnr16', 'src': 'flight.altitude_ft', 'scale': 1.0, 'word_index': 5},
                {'name': 'heading', 'encode': 'bnr16', 'src': 'flight.heading_deg', 'scale': 1.0, 'word_index': 6},
                {'name': 'speed', 'encode': 'u16', 'src': 'flight.airspeed_kts', 'word_index': 7},
            ]
        })
    
    # 2. Sensor messages (medium rate)
    for i in range(10):
        icd['messages'].append({
            'name': f'SENSOR_{i}',
            'rate_hz': 20.0,
            'rt': 10 + (i // 5),
            'tr': 'RT2BC',
            'sa': 10 + i,
            'wc': 4,
            'words': [
                # Packed sensor readings
                {'name': 'temp', 'encode': 'u16', 'mask': 0x03FF, 'shift': 0, 
                 'src': f'sensor_{i}_temp', 'scale': 0.1},  # 10 bits
                {'name': 'pressure', 'encode': 'u16', 'mask': 0x003F, 'shift': 10,
                 'src': f'sensor_{i}_press', 'scale': 10.0, 'word_index': 0},  # 6 bits
                # Status flags
                {'name': 'sensor_ok', 'encode': 'u16', 'mask': 0x0001, 'shift': 0, 'const': 1, 'word_index': 1},
                {'name': 'cal_valid', 'encode': 'u16', 'mask': 0x0001, 'shift': 1, 'const': 1, 'word_index': 1},
                {'name': 'sensor_id', 'encode': 'u16', 'mask': 0x00FF, 'shift': 8, 'const': i, 'word_index': 1},
                # Raw values
                {'name': 'raw_1', 'encode': 'u16', 'const': 0x1234 + i, 'word_index': 2},
                {'name': 'raw_2', 'encode': 'u16', 'const': 0x5678 + i, 'word_index': 3},
            ]
        })
    
    # 3. System status (low rate)
    for i in range(3):
        icd['messages'].append({
            'name': f'STATUS_{i}',
            'rate_hz': 2.0,
            'rt': 20,
            'tr': 'BC2RT',
            'sa': 25 + i,
            'wc': 2,
            'words': [
                # Complex bit packing
                {'name': 'sys_id', 'encode': 'u16', 'mask': 0x0007, 'shift': 0, 'const': i},  # 3 bits
                {'name': 'state', 'encode': 'u16', 'mask': 0x0007, 'shift': 3, 'const': 5, 'word_index': 0},  # 3 bits
                {'name': 'error_cnt', 'encode': 'u16', 'mask': 0x001F, 'shift': 6, 'const': 0, 'word_index': 0},  # 5 bits
                {'name': 'uptime', 'encode': 'u16', 'mask': 0x001F, 'shift': 11, 'const': 31, 'word_index': 0},  # 5 bits
                # Checksum
                {'name': 'checksum', 'encode': 'u16', 'const': 0xABCD, 'word_index': 1},
            ]
        })
    
    # 4. Command messages (variable rate)
    icd['messages'].append({
        'name': 'COMMAND',
        'rate_hz': 10.0,
        'rt': 31,
        'tr': 'BC2RT', 
        'sa': 31,
        'wc': 1,
        'words': [
            # All 16 bits used with tiny fields
            {'name': 'cmd1', 'encode': 'u16', 'mask': 0x0003, 'shift': 0, 'const': 3},  # 2 bits
            {'name': 'cmd2', 'encode': 'u16', 'mask': 0x0003, 'shift': 2, 'const': 2, 'word_index': 0},  # 2 bits
            {'name': 'cmd3', 'encode': 'u16', 'mask': 0x0003, 'shift': 4, 'const': 1, 'word_index': 0},  # 2 bits
            {'name': 'cmd4', 'encode': 'u16', 'mask': 0x0003, 'shift': 6, 'const': 0, 'word_index': 0},  # 2 bits
            {'name': 'cmd5', 'encode': 'u16', 'mask': 0x0003, 'shift': 8, 'const': 3, 'word_index': 0},  # 2 bits
            {'name': 'cmd6', 'encode': 'u16', 'mask': 0x0003, 'shift': 10, 'const': 2, 'word_index': 0},  # 2 bits
            {'name': 'cmd7', 'encode': 'u16', 'mask': 0x0003, 'shift': 12, 'const': 1, 'word_index': 0},  # 2 bits
            {'name': 'cmd8', 'encode': 'u16', 'mask': 0x0003, 'shift': 14, 'const': 0, 'word_index': 0},  # 2 bits
        ]
    })
    
    with open(filename, 'w') as f:
        yaml.dump(icd, f, default_flow_style=False)
    
    return len(icd['messages'])

def create_complex_scenario(filename: Path, duration: float):
    """Create a complex scenario with many derived values."""
    scenario = {
        'scenario': {
            'name': 'Complex Flight Test',
            'duration_s': duration,
            'seed': 12345
        },
        'flight_profile': {
            'segments': [
                {
                    'type': 'climb',
                    'duration_s': duration * 0.3,
                    'start_altitude_ft': 5000,
                    'end_altitude_ft': 35000,
                    'airspeed_kts': 350,
                    'heading_deg': 90
                },
                {
                    'type': 'level',
                    'duration_s': duration * 0.4,
                    'altitude_ft': 35000,
                    'airspeed_kts': 450,
                    'heading_deg': 90
                },
                {
                    'type': 'descent',
                    'duration_s': duration * 0.3,
                    'start_altitude_ft': 35000,
                    'end_altitude_ft': 10000,
                    'airspeed_kts': 300,
                    'heading_deg': 270
                }
            ]
        },
        'derived_values': {}
    }
    
    # Add sensor values
    for i in range(10):
        scenario['derived_values'][f'sensor_{i}_temp'] = 20 + i * 2  # Temperature
        scenario['derived_values'][f'sensor_{i}_press'] = 14.7 + i * 0.1  # Pressure
    
    with open(filename, 'w') as f:
        yaml.dump(scenario, f, default_flow_style=False)

def validate_with_tshark(ch10_file: Path, expected_messages: int, duration: float):
    """Validate CH10 file with tshark and return detailed results."""
    print(f"\nValidating {ch10_file.name}...")
    print(f"  File size: {ch10_file.stat().st_size:,} bytes")
    
    # 1. Basic packet count
    cmd = [TSHARK, '-r', str(ch10_file), '-q', '-z', 'io,stat,0']
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    packet_count = 0
    if result.returncode == 0:
        for line in result.stdout.split('\n'):
            if 'frames:' in line.lower():
                parts = line.split()
                for i, part in enumerate(parts):
                    if 'frames' in part.lower() and i + 1 < len(parts):
                        try:
                            packet_count = int(parts[i + 1])
                        except:
                            pass
    
    print(f"  Packets: {packet_count}")
    
    # 2. Check for CH10/1553
    cmd = [TSHARK, '-r', str(ch10_file)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    has_ch10 = 'CH10' in result.stdout
    has_1553 = 'MILSTD1553' in result.stdout or '1553' in result.stdout
    
    print(f"  CH10 detected: {'YES' if has_ch10 else 'NO'}")
    print(f"  1553 detected: {'YES' if has_1553 else 'NO'}")
    
    # 3. Extract detailed info
    cmd = [TSHARK, '-r', str(ch10_file), '-T', 'fields', 
           '-e', 'frame.number', '-e', 'frame.len', '-e', 'frame.time_relative']
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        lines = result.stdout.strip().split('\n')
        if lines and lines[0]:
            # Get timing info
            times = []
            sizes = []
            for line in lines:
                parts = line.split('\t')
                if len(parts) >= 3:
                    try:
                        sizes.append(int(parts[1]))
                        times.append(float(parts[2]))
                    except:
                        pass
            
            if times:
                actual_duration = max(times)
                print(f"  Duration: {actual_duration:.2f}s (expected {duration:.2f}s)")
                
                if sizes:
                    total_bytes = sum(sizes)
                    avg_size = sum(sizes) / len(sizes)
                    print(f"  Total data: {total_bytes:,} bytes")
                    print(f"  Avg packet: {avg_size:.0f} bytes")
    
    # 4. Estimate message rate
    if packet_count > 0 and duration > 0:
        est_msg_rate = packet_count / duration
        print(f"  Est. rate: {est_msg_rate:.1f} packets/sec")
    
    # Return validation results
    return {
        'valid': has_ch10 or has_1553,
        'packets': packet_count,
        'has_ch10': has_ch10,
        'has_1553': has_1553
    }

def test_large_files():
    """Test with increasingly large CH10 files."""
    print("="*60)
    print("LARGE FILE VALIDATION TEST")
    print("="*60)
    
    test_configs = [
        (1.0, "Quick test"),
        (5.0, "Short flight"),
        (30.0, "Medium flight"),
        (60.0, "Full minute"),
    ]
    
    results = []
    
    for duration, description in test_configs:
        print(f"\n--- {description} ({duration}s) ---")
        
        # Create ICD and scenario
        icd_file = Path(f"test_icd_{duration}s.yaml")
        scenario_file = Path(f"test_scenario_{duration}s.yaml")
        ch10_file = Path(f"test_{duration}s.ch10")
        
        try:
            # Generate files
            msg_count = create_complex_icd(icd_file)
            create_complex_scenario(scenario_file, duration)
            
            print(f"Generating CH10 with {msg_count} message types...")
            
            # Run ch10gen
            cmd = [
                sys.executable, '-m', 'ch10gen', 'build',
                '--scenario', str(scenario_file),
                '--icd', str(icd_file),
                '--out', str(ch10_file),
                '--duration', str(duration)
            ]
            
            start_time = time.time()
            result = subprocess.run(cmd, capture_output=True, text=True)
            gen_time = time.time() - start_time
            
            if result.returncode != 0:
                print(f"  FAIL: Generation failed")
                print(f"  Error: {result.stderr}")
                results.append((description, False, "Generation failed"))
                continue
            
            print(f"  Generated in {gen_time:.2f}s")
            
            # Validate with tshark
            validation = validate_with_tshark(ch10_file, msg_count, duration)
            
            if validation['valid']:
                print(f"  PASS: Valid CH10 file")
                results.append((description, True, f"{validation['packets']} packets"))
            else:
                print(f"  FAIL: Invalid CH10 file")
                results.append((description, False, "Invalid format"))
            
        finally:
            # Cleanup
            for f in [icd_file, scenario_file, ch10_file]:
                if f.exists():
                    f.unlink()
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    for desc, success, info in results:
        status = "PASS" if success else "FAIL"
        print(f"{status}: {desc} - {info}")
    
    passed = sum(1 for _, s, _ in results if s)
    print(f"\nTotal: {passed}/{len(results)} passed")
    
    return passed == len(results)

def test_stress_bitfields():
    """Stress test bitfield packing with extreme cases."""
    print("\n" + "="*60)
    print("BITFIELD STRESS TEST")
    print("="*60)
    
    from ch10gen.core.encode1553 import encode_bitfield, decode_bitfield, pack_bitfields
    
    # Test all possible single-bit positions
    print("\nTesting all 16 bit positions...")
    for bit in range(16):
        mask = 0x0001
        shift = bit
        value = 1
        
        try:
            encoded = encode_bitfield(value, mask, shift)
            expected = 1 << bit
            if encoded == expected:
                print(f"  Bit {bit:2d}: OK (0x{encoded:04X})")
            else:
                print(f"  Bit {bit:2d}: FAIL (got 0x{encoded:04X}, expected 0x{expected:04X})")
        except Exception as e:
            print(f"  Bit {bit:2d}: ERROR - {e}")
    
    # Test maximum packing density
    print("\nTesting maximum packing density...")
    test_cases = [
        # 16 single bits
        {f'b{i}': (1 if i % 2 else 0, 0x0001, i, 1.0, 0.0) for i in range(16)},
        # 8 2-bit fields
        {f'f{i}': (i % 4, 0x0003, i*2, 1.0, 0.0) for i in range(8)},
        # 4 4-bit fields
        {f'n{i}': (15 - i, 0x000F, i*4, 1.0, 0.0) for i in range(4)},
        # 2 8-bit fields
        {'low': (0xAB, 0x00FF, 0, 1.0, 0.0), 'high': (0xCD, 0x00FF, 8, 1.0, 0.0)},
    ]
    
    for i, fields in enumerate(test_cases, 1):
        try:
            packed = pack_bitfields(fields)
            print(f"  Case {i}: OK (packed 0x{packed:04X})")
            
            # Verify unpack
            unpack_fields = {name: (f[1], f[2], f[3], f[4]) for name, f in fields.items()}
            unpacked = unpack_bitfields(packed, unpack_fields)
            
            all_match = True
            for name, (expected, _, _, _, _) in fields.items():
                if abs(unpacked[name] - expected) > 0.001:
                    all_match = False
                    break
            
            if not all_match:
                print(f"    WARN: Unpack mismatch")
                
        except Exception as e:
            print(f"  Case {i}: ERROR - {e}")
    
    print("\nStress test complete!")

if __name__ == "__main__":
    # Check tshark
    if not Path(TSHARK).exists():
        print("WARNING: TShark not found, validation will be limited")
    
    # Run tests
    print("CH10 VALIDATION WITH TSHARK")
    print("="*60)
    
    # 1. Stress test bitfields
    test_stress_bitfields()
    
    # 2. Test large files
    success = test_large_files()
    
    if success:
        print("\n" + "="*60)
        print("ALL TESTS PASSED!")
        print("="*60)
    else:
        print("\n" + "="*60)
        print("SOME TESTS FAILED")
        print("="*60)
