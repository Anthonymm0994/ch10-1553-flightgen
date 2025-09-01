#!/usr/bin/env python3
"""Debug script to trace CH10 writer message generation."""

import tempfile
from pathlib import Path
from ch10gen.icd import load_icd
from ch10gen.schedule import build_schedule_from_icd
from ch10gen.ch10_writer import write_ch10_file
from ch10gen.wire_reader import read_1553_wire


def debug_ch10_writer():
    """Debug the CH10 writer to see where GPS messages are being lost."""
    print("=== CH10 Writer Debug ===")
    
    # Load test ICD
    icd = load_icd(Path("icd/test_icd.yaml"))
    print(f"✅ ICD loaded with {len(icd.messages)} messages")
    
    # Check each message
    for i, msg in enumerate(icd.messages):
        print(f"  Message {i}: {msg.name}")
        print(f"    RT={msg.rt}, SA={msg.sa}, TR={msg.tr}, WC={msg.wc}")
        print(f"    Rate={msg.rate_hz}Hz, Words={len(msg.words)}")
        for j, word in enumerate(msg.words):
            print(f"      Word {j}: {word.name}, encode={word.encode}")
    
    # Generate schedule
    schedule = build_schedule_from_icd(icd, duration_s=5.0)  # Shorter duration for debugging
    print(f"\n✅ Schedule generated with {len(schedule.messages)} messages")
    
    # Check schedule by message type
    nav_messages = [msg for msg in schedule.messages if msg.message.rt == 10 and msg.message.sa == 1]
    gps_messages = [msg for msg in schedule.messages if msg.message.rt == 11 and msg.message.sa == 2]
    
    print(f"  NAV messages in schedule: {len(nav_messages)}")
    print(f"  GPS messages in schedule: {len(gps_messages)}")
    
    # Show first few messages of each type
    print(f"\nFirst 3 NAV messages:")
    for i, msg in enumerate(nav_messages[:3]):
        print(f"  {i}: {msg.message.name} at {msg.time_s:.3f}s")
    
    print(f"\nFirst 3 GPS messages:")
    for i, msg in enumerate(gps_messages[:3]):
        print(f"  {i}: {msg.message.name} at {msg.time_s:.3f}s")
    
    # Generate CH10 file
    scenario = {'duration_s': 5, 'name': 'debug_test'}
    
    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = Path(tmpdir) / "debug_test.ch10"
        
        print(f"\n🔄 Generating CH10 file...")
        stats = write_ch10_file(
            output_path=output_file,
            scenario=scenario,
            icd=icd,
            seed=42,
            writer_backend='irig106'
        )
        
        print(f"✅ CH10 file generated: {stats}")
        
        # Read messages from file
        print(f"\n🔄 Reading messages from CH10 file...")
        messages = list(read_1553_wire(output_file, max_messages=1000))
        
        # Analyze what we got
        rt_values = set(msg['rt'] for msg in messages)
        sa_values = set(msg['sa'] for msg in messages)
        
        print(f"❌ CH10 file contains:")
        print(f"  RT values: {sorted(rt_values)}")
        print(f"  SA values: {sorted(sa_values)}")
        
        # Count by type
        nav_count = sum(1 for msg in messages if msg['rt'] == 10 and msg['sa'] == 1)
        gps_count = sum(1 for msg in messages if msg['rt'] == 11 and msg['sa'] == 2)
        
        print(f"  NAV messages: {nav_count}")
        print(f"  GPS messages: {gps_count}")
        
        # Show first few messages from file
        print(f"\nFirst 5 messages from CH10 file:")
        for i, msg in enumerate(messages[:5]):
            print(f"  {i}: RT={msg['rt']}, SA={msg['sa']}, TR={msg['tr']}, WC={msg['wc']}")
        
        # Check if GPS messages are in the file but not being parsed
        print(f"\n🔍 Checking if GPS messages are in file but not parsed...")
        
        # Read raw file to see if GPS messages are there
        with open(output_file, 'rb') as f:
            data = f.read()
        
        # Look for RT=11 in raw data (command word with RT=11 would be 0x5800 + ...)
        rt_11_pattern = b'\x00\x58'  # RT=11 in little-endian
        rt_11_count = data.count(rt_11_pattern)
        print(f"  RT=11 patterns found in raw file: {rt_11_count}")
        
        if rt_11_count > 0:
            print(f"  ⚠️  GPS messages ARE in the file but not being parsed correctly!")
        else:
            print(f"  ❌ GPS messages are NOT in the file at all")


if __name__ == "__main__":
    debug_ch10_writer()
