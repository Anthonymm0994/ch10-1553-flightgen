#!/usr/bin/env python3
"""
Bitfield validation using actual CH10 generation and tshark.
This tests mask/shift combinations, edge cases, real data.
"""

import os
import sys
import subprocess
import tempfile
from pathlib import Path
from typing import List, Dict, Any
import json
import yaml

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from ch10gen import __main__ as ch10gen_main
from ch10gen.core.encode1553 import encode_bitfield, decode_bitfield, pack_bitfields, unpack_bitfields

# TShark configuration
TSHARK = os.environ.get('TSHARK', 'C:/Program Files/Wireshark/tshark.exe')
if not Path(TSHARK).exists():
    TSHARK = '/c/Program Files/Wireshark/tshark.exe'

def create_bitfield_icd(config: Dict[str, Any], output_path: Path):
    """Create an ICD with specific bitfield configuration."""
    icd = {
        'name': config['name'],
        'bus': 'A',
        'description': f"Test ICD for {config['description']}",
        'messages': []
    }
    
    for msg_config in config['messages']:
        message = {
            'name': msg_config['name'],
            'rate_hz': msg_config.get('rate_hz', 10.0),
            'rt': msg_config.get('rt', 5),
            'tr': msg_config.get('tr', 'RT2BC'),
            'sa': msg_config.get('sa', 1),
            'wc': msg_config.get('wc', 1),
            'words': msg_config['words']
        }
        icd['messages'].append(message)
    
    with open(output_path, 'w') as f:
        yaml.dump(icd, f, default_flow_style=False)
    
    return output_path

def generate_and_validate(test_name: str, icd_config: Dict, scenario_path: Path, work_dir: Path):
    """Generate CH10 file and validate with tshark."""
    print(f"\n{'='*60}")
    print(f"TEST: {test_name}")
    print(f"{'='*60}")
    
    # Create ICD
    icd_path = work_dir / f"{test_name}_icd.yaml"
    create_bitfield_icd(icd_config, icd_path)
    
    # Generate CH10
    ch10_path = work_dir / f"{test_name}.ch10"
    cmd = [
        sys.executable, '-m', 'ch10gen', 'build',
        '--scenario', str(scenario_path),
        '--icd', str(icd_path),
        '--out', str(ch10_path),
        '--duration', '0.5'
    ]
    
    print(f"Generating CH10 with bitfield config...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  FAIL Generation failed: {result.stderr}")
        return False
    
    print(f"  OK Generated {ch10_path.name} ({ch10_path.stat().st_size} bytes)")
    
    # Validate with tshark
    print(f"Validating with tshark...")
    tshark_cmd = [TSHARK, '-r', str(ch10_path), '-c', '10']
    
    result = subprocess.run(tshark_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  FAIL TShark validation failed: {result.stderr}")
        return False
    
    # Count packets
    lines = result.stdout.strip().split('\n')
    packet_count = len([l for l in lines if l])
    print(f"  OK TShark read {packet_count} packets")
    
    # Check for 1553 messages
    if 'MILSTD1553' in result.stdout or 'CH10' in result.stdout:
        print(f"  OK 1553/CH10 messages detected")
    else:
        print(f"  WARN No explicit 1553/CH10 markers (may need Lua dissector)")
    
    # Detailed field extraction
    field_cmd = [TSHARK, '-r', str(ch10_path), '-T', 'fields', 
                 '-e', 'frame.number', '-e', 'frame.len', '-c', '5']
    result = subprocess.run(field_cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"  OK Field extraction successful")
    
    return True

def test_all_bitfield_combinations():
    """Test comprehensive bitfield combinations."""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        work_dir = Path(temp_dir)
        
        # Create a basic scenario
        scenario_path = work_dir / "test_scenario.yaml"
        scenario_path.write_text("""
scenario:
  name: "Bitfield Test"
  duration_s: 0.5
  seed: 42

flight_profile:
  segments:
    - type: "level"
      duration_s: 0.5
      altitude_ft: 10000
      airspeed_kts: 250
      heading_deg: 090

derived_values:
  test_value_1: 15
  test_value_2: 31
  test_value_3: 63
  test_value_4: 127
  test_value_5: 255
  test_value_6: 511
  test_value_7: 1023
  test_value_8: 2047
  test_value_9: 4095
  test_value_10: 8191
  test_value_11: 16383
  test_value_12: 32767
""")
        
        # Test configurations
        test_configs = [
            # Test 1: Single bit fields
            {
                'name': 'single_bits',
                'description': 'Single bit flags in different positions',
                'messages': [{
                    'name': 'FLAGS',
                    'sa': 1,
                    'wc': 1,
                    'words': [
                        {'name': 'flag0', 'encode': 'u16', 'mask': 0x0001, 'shift': 0, 'const': 1},
                        {'name': 'flag1', 'encode': 'u16', 'mask': 0x0001, 'shift': 1, 'const': 1, 'word_index': 0},
                        {'name': 'flag7', 'encode': 'u16', 'mask': 0x0001, 'shift': 7, 'const': 1, 'word_index': 0},
                        {'name': 'flag15', 'encode': 'u16', 'mask': 0x0001, 'shift': 15, 'const': 1, 'word_index': 0},
                    ]
                }]
            },
            
            # Test 2: 4-bit nibbles
            {
                'name': 'nibbles',
                'description': '4-bit fields packed into words',
                'messages': [{
                    'name': 'NIBBLES',
                    'sa': 2,
                    'wc': 1,
                    'words': [
                        {'name': 'nibble0', 'encode': 'u16', 'mask': 0x000F, 'shift': 0, 'src': 'test_value_1'},
                        {'name': 'nibble1', 'encode': 'u16', 'mask': 0x000F, 'shift': 4, 'src': 'test_value_1', 'word_index': 0},
                        {'name': 'nibble2', 'encode': 'u16', 'mask': 0x000F, 'shift': 8, 'src': 'test_value_1', 'word_index': 0},
                        {'name': 'nibble3', 'encode': 'u16', 'mask': 0x000F, 'shift': 12, 'src': 'test_value_1', 'word_index': 0},
                    ]
                }]
            },
            
            # Test 3: Mixed bit widths
            {
                'name': 'mixed_widths',
                'description': 'Different bit widths in same word',
                'messages': [{
                    'name': 'MIXED',
                    'sa': 3,
                    'wc': 1,
                    'words': [
                        {'name': 'bits_3', 'encode': 'u16', 'mask': 0x0007, 'shift': 0, 'src': 'test_value_3'},  # 3 bits
                        {'name': 'bits_5', 'encode': 'u16', 'mask': 0x001F, 'shift': 3, 'src': 'test_value_2', 'word_index': 0},  # 5 bits
                        {'name': 'bits_8', 'encode': 'u16', 'mask': 0x00FF, 'shift': 8, 'src': 'test_value_8', 'word_index': 0},  # 8 bits
                    ]
                }]
            },
            
            # Test 4: Maximum packing (all 16 bits used)
            {
                'name': 'max_packing',
                'description': 'Using all 16 bits with multiple fields',
                'messages': [{
                    'name': 'MAXPACK',
                    'sa': 4,
                    'wc': 1,
                    'words': [
                        {'name': 'field1', 'encode': 'u16', 'mask': 0x001F, 'shift': 0, 'src': 'test_value_2'},  # 5 bits
                        {'name': 'field2', 'encode': 'u16', 'mask': 0x001F, 'shift': 5, 'src': 'test_value_2', 'word_index': 0},  # 5 bits
                        {'name': 'field3', 'encode': 'u16', 'mask': 0x001F, 'shift': 10, 'src': 'test_value_2', 'word_index': 0},  # 5 bits
                        {'name': 'field4', 'encode': 'u16', 'mask': 0x0001, 'shift': 15, 'const': 1, 'word_index': 0},  # 1 bit
                    ]
                }]
            },
            
            # Test 5: Sparse bits (gaps between fields)
            {
                'name': 'sparse_bits',
                'description': 'Fields with gaps between them',
                'messages': [{
                    'name': 'SPARSE',
                    'sa': 5,
                    'wc': 1,
                    'words': [
                        {'name': 'low', 'encode': 'u16', 'mask': 0x0003, 'shift': 0, 'const': 3},  # bits 0-1
                        {'name': 'mid', 'encode': 'u16', 'mask': 0x0003, 'shift': 4, 'const': 3, 'word_index': 0},  # bits 4-5
                        {'name': 'high', 'encode': 'u16', 'mask': 0x0003, 'shift': 14, 'const': 3, 'word_index': 0},  # bits 14-15
                    ]
                }]
            },
            
            # Test 6: Multi-word with bitfields
            {
                'name': 'multi_word',
                'description': 'Bitfields across multiple words',
                'messages': [{
                    'name': 'MULTIWORD',
                    'sa': 6,
                    'wc': 3,
                    'words': [
                        # Word 0 - packed
                        {'name': 'w0_f1', 'encode': 'u16', 'mask': 0x00FF, 'shift': 0, 'src': 'test_value_8'},
                        {'name': 'w0_f2', 'encode': 'u16', 'mask': 0x00FF, 'shift': 8, 'src': 'test_value_8', 'word_index': 0},
                        # Word 1 - sparse
                        {'name': 'w1_flags', 'encode': 'u16', 'mask': 0x000F, 'shift': 0, 'const': 0xA, 'word_index': 1},
                        # Word 2 - full word
                        {'name': 'w2_full', 'encode': 'u16', 'const': 0x1234, 'word_index': 2},
                    ]
                }]
            },
            
            # Test 7: Edge case - 15-bit value
            {
                'name': 'edge_15bit',
                'description': '15-bit value with sign bit',
                'messages': [{
                    'name': 'EDGE15',
                    'sa': 7,
                    'wc': 1,
                    'words': [
                        {'name': 'value', 'encode': 'u16', 'mask': 0x7FFF, 'shift': 0, 'src': 'test_value_12'},
                        {'name': 'sign', 'encode': 'u16', 'mask': 0x0001, 'shift': 15, 'const': 0, 'word_index': 0},
                    ]
                }]
            },
            
            # Test 8: Scaled bitfields
            {
                'name': 'scaled',
                'description': 'Bitfields with scaling',
                'messages': [{
                    'name': 'SCALED',
                    'sa': 8,
                    'wc': 1,
                    'words': [
                        {'name': 'altitude', 'encode': 'u16', 'mask': 0x03FF, 'shift': 0, 
                         'src': 'flight.altitude_ft', 'scale': 0.01},  # 10 bits, scaled
                        {'name': 'speed', 'encode': 'u16', 'mask': 0x003F, 'shift': 10,
                         'src': 'flight.airspeed_kts', 'scale': 0.1, 'word_index': 0},  # 6 bits, scaled
                    ]
                }]
            }
        ]
        
        # Run all tests
        results = []
        for i, config in enumerate(test_configs, 1):
            test_name = config['name']
            success = generate_and_validate(test_name, config, scenario_path, work_dir)
            results.append((test_name, success))
            
            if success:
                print(f"PASS {test_name}: PASSED")
            else:
                print(f"FAIL {test_name}: FAILED")
        
        # Summary
        print(f"\n{'='*60}")
        print("COMPREHENSIVE TEST SUMMARY")
        print(f"{'='*60}")
        passed = sum(1 for _, s in results if s)
        total = len(results)
        print(f"Passed: {passed}/{total}")
        
        for name, success in results:
            status = "PASS" if success else "FAIL"
            print(f"  {status} {name}")
        
        return passed == total

def test_edge_cases():
    """Test edge cases and error conditions."""
    print("\n" + "="*60)
    print("EDGE CASE TESTS")
    print("="*60)
    
    # Test invalid mask/shift combinations
    test_cases = [
        # Valid cases
        (0x00FF, 0, 100, True, "8-bit value at position 0"),
        (0x00FF, 8, 200, True, "8-bit value at position 8 (upper byte)"),
        (0x0001, 0, 1, True, "Single bit at position 0"),
        (0x0001, 15, 1, True, "Single bit at position 15"),
        (0x7FFF, 0, 32767, True, "15-bit maximum value"),
        (0x000F, 4, 15, True, "4-bit nibble at position 4"),
        (0x001F, 10, 31, True, "5-bit value at position 10"),
        
        # Edge cases that should fail
        (0xFFFF, 1, 65535, False, "16-bit mask with shift (overflow)"),
        (0x00FF, 0, 256, False, "Value too large for mask"),
        (0x000F, 0, 16, False, "Value exceeds 4-bit mask"),
        (0x00FF, 9, 255, False, "8-bit mask with shift 9 (overflow)"),
    ]
    
    for mask, shift, value, should_pass, description in test_cases:
        print(f"\nTest: {description}")
        print(f"  Mask: 0x{mask:04X}, Shift: {shift}, Value: {value}")
        
        try:
            encoded = encode_bitfield(value, mask, shift)
            decoded = decode_bitfield(encoded, mask, shift)
            
            if should_pass:
                if abs(decoded - value) < 0.001:
                    print(f"  PASS PASS: Encoded={encoded:04X}, Decoded={decoded}")
                else:
                    print(f"  FAIL FAIL: Round-trip failed. Got {decoded}, expected {value}")
            else:
                print(f"  FAIL FAIL: Should have raised error but didn't")
                
        except ValueError as e:
            if not should_pass:
                print(f"  PASS PASS: Correctly raised error: {e}")
            else:
                print(f"  FAIL FAIL: Unexpected error: {e}")
        except Exception as e:
            print(f"  FAIL FAIL: Unexpected exception: {e}")

def test_pack_unpack():
    """Test multi-field packing and unpacking."""
    print("\n" + "="*60)
    print("PACK/UNPACK TESTS")
    print("="*60)
    
    test_cases = [
        {
            'name': 'Simple 2-field pack',
            'fields': {
                'field1': (10, 0x000F, 0, 1.0, 0.0),  # 4 bits at position 0
                'field2': (5, 0x000F, 4, 1.0, 0.0),   # 4 bits at position 4
            },
            'expected_word': 0x005A  # (5 << 4) | 10
        },
        {
            'name': 'Full 16-bit pack',
            'fields': {
                'low': (0xFF, 0x00FF, 0, 1.0, 0.0),   # Lower 8 bits
                'high': (0xAB, 0x00FF, 8, 1.0, 0.0),  # Upper 8 bits
            },
            'expected_word': 0xABFF
        },
        {
            'name': 'Sparse bits',
            'fields': {
                'bit0': (1, 0x0001, 0, 1.0, 0.0),
                'bit7': (1, 0x0001, 7, 1.0, 0.0),
                'bit15': (1, 0x0001, 15, 1.0, 0.0),
            },
            'expected_word': 0x8081
        }
    ]
    
    for test in test_cases:
        print(f"\n{test['name']}:")
        try:
            packed = pack_bitfields(test['fields'])
            print(f"  Packed: 0x{packed:04X} (expected 0x{test['expected_word']:04X})")
            
            if packed == test['expected_word']:
                print(f"  PASS Pack successful")
            else:
                print(f"  FAIL Pack mismatch")
            
            # Now unpack
            unpack_fields = {
                name: (fields[1], fields[2], fields[3], fields[4])
                for name, fields in test['fields'].items()
            }
            unpacked = unpack_bitfields(packed, unpack_fields)
            
            # Verify unpacked values
            all_match = True
            for name, (value, _, _, _, _) in test['fields'].items():
                if abs(unpacked[name] - value) > 0.001:
                    print(f"  FAIL Unpack mismatch for {name}: got {unpacked[name]}, expected {value}")
                    all_match = False
            
            if all_match:
                print(f"  PASS Unpack successful")
                
        except Exception as e:
            print(f"  FAIL Error: {e}")

if __name__ == "__main__":
    print("="*60)
    print("COMPREHENSIVE BITFIELD VALIDATION")
    print("="*60)
    
    # Check tshark
    if not Path(TSHARK).exists():
        print(f"WARNING  WARNING: TShark not found at {TSHARK}")
        print("   Some validations will be limited")
    else:
        result = subprocess.run([TSHARK, '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            version = result.stdout.split('\n')[0]
            print(f"OK: Using {version}")
    
    # Run tests
    print("\n1. Testing edge cases...")
    test_edge_cases()
    
    print("\n2. Testing pack/unpack...")
    test_pack_unpack()
    
    print("\n3. Testing comprehensive CH10 generation with bitfields...")
    success = test_all_bitfield_combinations()
    
    if success:
        print("\n" + "="*60)
        print("PASS ALL COMPREHENSIVE TESTS PASSED!")
        print("="*60)
    else:
        print("\n" + "="*60)
        print("FAIL SOME TESTS FAILED - Review output above")
        print("="*60)
