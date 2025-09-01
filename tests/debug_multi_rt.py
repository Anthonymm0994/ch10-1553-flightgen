#!/usr/bin/env python3
"""Debug script to test multiple RT handling and both readers."""

import tempfile
from pathlib import Path
from ch10gen.icd import load_icd
from ch10gen.ch10_writer import write_ch10_file
from ch10gen.inspector import inspect_1553_timeline, inspect_1553_timeline_pyc10
from ch10gen.wire_reader import read_1553_wire


def debug_multi_rt():
    """Debug multiple RT handling and both readers."""
    print("=== Multi-RT Debug ===")
    
    # Load test ICD
    icd = load_icd(Path("icd/test_icd.yaml"))
    
    print(f"✅ ICD loaded with {len(icd.messages)} messages:")
    for msg in icd.messages:
        print(f"  - {msg.name}: RT={msg.rt}, SA={msg.sa}, WC={msg.wc}")
    
    # Generate a short CH10 file
    scenario = {'duration_s': 2, 'name': 'multi_rt_test'}
    
    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = Path(tmpdir) / "multi_rt_test.ch10"
        
        print(f"\n🔄 Generating CH10 file...")
        stats = write_ch10_file(
            output_path=output_file,
            scenario=scenario,
            icd=icd,
            seed=42,
            writer_backend='irig106'
        )
        
        print(f"✅ CH10 file generated: {stats}")
        
        # Test both readers
        for reader in ['wire', 'pyc10']:
            print(f"\n🔍 Testing {reader.upper()} reader:")
            
            try:
                if reader == 'pyc10':
                    messages = list(inspect_1553_timeline_pyc10(
                        filepath=output_file,
                        channel='auto',
                        max_messages=100
                    ))
                else:
                    messages = list(inspect_1553_timeline(
                        filepath=output_file,
                        channel='auto',
                        max_messages=100,
                        reader=reader
                    ))
                
                # Analyze results
                rt_values = set(msg['rt'] for msg in messages)
                sa_values = set(msg['sa'] for msg in messages)
                
                print(f"  Found {len(messages)} messages")
                print(f"  RT values: {sorted(rt_values)}")
                print(f"  SA values: {sorted(sa_values)}")
                
                # Count by message type
                nav_count = sum(1 for msg in messages if msg['rt'] == 10 and msg['sa'] == 1)
                gps_count = sum(1 for msg in messages if msg['rt'] == 11 and msg['sa'] == 2)
                
                print(f"  NAV messages (RT=10, SA=1): {nav_count}")
                print(f"  GPS messages (RT=11, SA=2): {gps_count}")
                
                # Show sample messages
                if messages:
                    print(f"  Sample message: {messages[0]}")
                
            except Exception as e:
                print(f"  ❌ {reader.upper()} reader failed: {e}")
        
        # Test wire reader directly
        print(f"\n🔍 Testing wire reader directly:")
        try:
            messages = list(read_1553_wire(output_file, max_messages=100))
            
            rt_values = set(msg['rt'] for msg in messages)
            sa_values = set(msg['sa'] for msg in messages)
            
            print(f"  Wire reader found {len(messages)} messages")
            print(f"  RT values: {sorted(rt_values)}")
            print(f"  SA values: {sorted(sa_values)}")
            
            # Count by message type
            nav_count = sum(1 for msg in messages if msg['rt'] == 10 and msg['sa'] == 1)
            gps_count = sum(1 for msg in messages if msg['rt'] == 11 and msg['sa'] == 2)
            
            print(f"  NAV messages (RT=10, SA=1): {nav_count}")
            print(f"  GPS messages (RT=11, SA=2): {gps_count}")
            
        except Exception as e:
            print(f"  ❌ Wire reader failed: {e}")
        
        # Check raw file for GPS patterns
        print(f"\n🔍 Checking raw file for GPS patterns:")
        with open(output_file, 'rb') as f:
            data = f.read()
        
        # Look for RT=11 patterns
        rt_11_pattern = b'\x00\x58'  # RT=11 in little-endian
        rt_11_count = data.count(rt_11_pattern)
        print(f"  RT=11 patterns found in raw file: {rt_11_count}")
        
        if rt_11_count > 0:
            print(f"  ⚠️  GPS messages ARE in the file but not being parsed!")
            print(f"  This suggests a parsing issue, not a generation issue.")
        else:
            print(f"  ❌ GPS messages are NOT in the file at all!")
            print(f"  This suggests a generation issue.")


if __name__ == "__main__":
    debug_multi_rt()
