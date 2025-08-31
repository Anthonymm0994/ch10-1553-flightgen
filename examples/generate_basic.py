#!/usr/bin/env python3
"""
Basic CH10 file generation example.
Shows the simplest way to generate a CH10 file with navigation data.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from ch10gen.icd import load_icd
from ch10gen.flight_profile import FlightProfile
from ch10gen.schedule import build_schedule_from_icd
from ch10gen.ch10_writer import write_ch10_file, Ch10WriterConfig

def generate_basic_ch10():
    """Generate a basic CH10 file with navigation data."""
    
    print("Basic CH10 Generation Example")
    print("="*50)
    
    # 1. Load the ICD (Interface Control Document)
    print("\n1. Loading ICD...")
    icd_path = Path(__file__).parent.parent / "icd" / "nav_icd.yaml"
    icd = load_icd(icd_path)
    print(f"   Loaded {len(icd.messages)} messages")
    
    # 2. Create a flight profile
    print("\n2. Creating flight profile...")
    profile = FlightProfile(seed=12345)
    
    # Add a simple level flight segment
    profile.segments = [{
        'type': 'level',
        'duration_s': 10.0,
        'altitude_ft': 15000,
        'airspeed_kts': 300,
        'heading_deg': 90
    }]
    profile.duration_s = 10.0
    print("   Created 10-second level flight at 15,000 ft")
    
    # 3. Build the message schedule
    print("\n3. Building message schedule...")
    schedule = build_schedule_from_icd(icd, duration_s=10.0)
    stats = schedule.get_statistics()
    print(f"   Total messages: {stats['total_messages']}")
    print(f"   Major frames: {stats['major_frames']}")
    print(f"   Minor frames: {stats['minor_frames']}")
    
    # 4. Configure CH10 writer
    print("\n4. Configuring CH10 writer...")
    config = Ch10WriterConfig(
        target_packet_bytes=65536,
        time_packet_interval_s=1.0
    )
    
    # 5. Generate the CH10 file
    print("\n5. Generating CH10 file...")
    output_file = Path(__file__).parent.parent / "out" / "basic_example.ch10"
    output_file.parent.mkdir(exist_ok=True)
    
    # Create scenario dict for the writer
    scenario = {
        'name': 'Basic Example',
        'duration_s': 10.0,
        'seed': 12345,
        'flight_profile': {
            'segments': profile.segments
        }
    }
    
    stats = write_ch10_file(
        output_path=output_file,
        scenario=scenario,
        icd=icd,
        seed=12345
    )
    
    # 6. Report results
    print(f"\n" + "="*50)
    print("SUCCESS: CH10 file generated!")
    print(f"  File: {output_file}")
    print(f"  Size: {output_file.stat().st_size:,} bytes")
    print(f"  Duration: 10 seconds")
    print(f"  Messages: ~{len(schedule.messages) * 10} total")
    
    return output_file

def main():
    """Main entry point."""
    try:
        output_file = generate_basic_ch10()
        print(f"\nYou can validate this file with:")
        print(f"  python -m ch10gen validate {output_file}")
        return 0
    except Exception as e:
        print(f"\nERROR: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
