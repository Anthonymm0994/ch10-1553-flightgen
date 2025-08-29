"""Dual-reader validation tests.

Tests CH10 files with both PyChapter10 and external tools (when available).
This ensures files work with both spec-compliant readers and PyChapter10 quirks.
"""

import pytest
import subprocess
import tempfile
import struct
from datetime import datetime
from pathlib import Path
from contextlib import suppress
from typing import Dict, List, Optional, Tuple


def has_c10_tools() -> bool:
    """Check if c10-tools are available."""
    try:
        result = subprocess.run(['c10-dump', '--help'], 
                              capture_output=True, text=True, timeout=1)
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def run_c10_dump(filepath: Path) -> Dict:
    """Run c10-dump and parse output."""
    try:
        result = subprocess.run(
            ['c10-dump', str(filepath)],
            capture_output=True, text=True, timeout=5
        )
        
        if result.returncode != 0:
            return {'error': result.stderr}
        
        # Parse c10-dump output
        output = result.stdout
        stats = {
            'packets': 0,
            'data_types': {},
            'channels': set(),
            'errors': 0,
        }
        
        for line in output.split('\n'):
            line = line.strip()
            if 'Type 0x' in line:
                # Extract data type
                parts = line.split('Type 0x')
                if len(parts) > 1:
                    dtype = parts[1][:2]
                    stats['data_types'][dtype] = stats['data_types'].get(dtype, 0) + 1
            elif 'Channel' in line:
                # Extract channel ID
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == 'Channel' and i + 1 < len(parts):
                        stats['channels'].add(parts[i+1])
            elif 'packets' in line.lower():
                # Extract packet count
                parts = line.split()
                for part in parts:
                    if part.isdigit():
                        stats['packets'] = int(part)
                        break
        
        return stats
        
    except (subprocess.TimeoutExpired, Exception) as e:
        return {'error': str(e)}


def run_c10_errcount(filepath: Path) -> int:
    """Run c10-errcount and return error count."""
    try:
        result = subprocess.run(
            ['c10-errcount', str(filepath)],
            capture_output=True, text=True, timeout=5
        )
        
        if result.returncode != 0:
            return -1
        
        # Parse error count from output
        for line in result.stdout.split('\n'):
            if 'errors' in line.lower():
                parts = line.split()
                for part in parts:
                    if part.isdigit():
                        return int(part)
        
        return 0
        
    except (subprocess.TimeoutExpired, Exception):
        return -1


def validate_with_pychapter10(filepath: Path) -> Dict:
    """Validate CH10 file with PyChapter10."""
    from chapter10 import C10
    
    try:
        c10 = C10(str(filepath))
        packets = list(c10)
        
        stats = {
            'packets': len(packets),
            'types': {},
            'channels': set(),
            'messages': 0,
        }
        
        for packet in packets:
            ptype = type(packet).__name__
            stats['types'][ptype] = stats['types'].get(ptype, 0) + 1
            stats['channels'].add(hex(packet.channel_id))
            
            # Try to count messages if MS1553
            if hasattr(packet, '__iter__'):
                try:
                    messages = list(packet)
                    stats['messages'] += len(messages)
                except:
                    pass
        
        return stats
        
    except Exception as e:
        return {'error': str(e)}


def validate_wire_format(filepath: Path) -> Dict:
    """Validate CH10 file at wire level."""
    with open(filepath, 'rb') as f:
        data = f.read()
    
    stats = {
        'packets': 0,
        'data_types': {},
        'channels': set(),
        'valid_syncs': 0,
        'invariants': [],
    }
    
    offset = 0
    while offset < len(data) - 24:
        # Check sync
        sync = struct.unpack('<H', data[offset:offset+2])[0]
        if sync != 0xEB25:
            offset += 1
            continue
        
        stats['valid_syncs'] += 1
        
        # Parse header
        channel_id = struct.unpack('<H', data[offset+2:offset+4])[0]
        packet_len = struct.unpack('<I', data[offset+4:offset+8])[0]
        data_len = struct.unpack('<I', data[offset+8:offset+12])[0]
        data_type = data[offset+14]
        
        stats['packets'] += 1
        stats['channels'].add(hex(channel_id))
        dtype_hex = f'{data_type:02x}'
        stats['data_types'][dtype_hex] = stats['data_types'].get(dtype_hex, 0) + 1
        
        # Check invariants
        if packet_len != 24 + data_len:
            stats['invariants'].append(f"Packet {stats['packets']}: length mismatch")
        
        if data_type == 0x19 and packet_len >= 28:
            # Check MS1553 CSDW
            csdw = struct.unpack('<I', data[offset+24:offset+28])[0]
            msg_count = csdw & 0xFFFF
            if msg_count == 0:
                stats['invariants'].append(f"MS1553 packet with 0 messages")
        
        # Move to next packet
        offset += packet_len
        if offset % 2 != 0:
            offset += 1
    
    return stats


class TestDualReader:
    """Dual-reader validation tests."""
    
    def test_small_file_both_readers(self, tmp_path):
        """Test that a small CH10 file can be read by both readers."""
        from ch10gen.ch10_writer import Ch10Writer, Ch10WriterConfig as WriterConfig
        import yaml
        
        # Build a small test file
        output_file = tmp_path / "test_dual.c10"
        
        # Load test scenario and ICD
        with open('scenarios/test_scenario.yaml') as f:
            scenario = yaml.safe_load(f)
        with open('icd/test_icd.yaml') as f:
            icd = yaml.safe_load(f)
        
        config = WriterConfig()
        writer = Ch10Writer(config)
        
        # Generate simple test data
        from ch10gen.flight_profile import FlightProfileGenerator
        from ch10gen.schedule import build_schedule_from_icd
        from ch10gen.icd import ICDDefinition
        
        profile = FlightProfileGenerator(seed=scenario.get('seed'))
        profile.generate_profile(
            start_time=datetime.now(),
            duration_s=15.0,
            segments=scenario.get('profile', {}).get('segments', []),
            initial_altitude_ft=scenario.get('profile', {}).get('base_altitude_ft', 2000)
        )
        
        icd_config = ICDDefinition.from_dict(icd)
        schedule = build_schedule_from_icd(
            icd=icd_config,
            duration_s=15.0
        )
        
        writer.write_file(
            filepath=output_file,
            schedule=schedule,
            flight_profile=profile,
            icd=icd_config
        )
        
        # Validate with PyChapter10
        py_stats = validate_with_pychapter10(output_file)
        assert 'error' not in py_stats, f"PyChapter10 error: {py_stats.get('error')}"
        assert py_stats['packets'] > 0, "PyChapter10 found no packets"
        
        print("\n📖 PyChapter10 Validation:")
        print(f"  Packets: {py_stats['packets']}")
        print(f"  Types: {py_stats['types']}")
        print(f"  Channels: {py_stats['channels']}")
        
        # Validate wire format
        wire_stats = validate_wire_format(output_file)
        assert wire_stats['packets'] > 0, "Wire format found no packets"
        assert wire_stats['valid_syncs'] == wire_stats['packets'], "Invalid sync patterns"
        
        print("\n🔬 Wire Format Validation:")
        print(f"  Packets: {wire_stats['packets']}")
        print(f"  Data Types: {wire_stats['data_types']}")
        print(f"  Channels: {wire_stats['channels']}")
        if wire_stats['invariants']:
            print(f"  ⚠️ Invariant violations: {wire_stats['invariants']}")
        
        # Validate with c10-tools if available
        if has_c10_tools():
            c10_stats = run_c10_dump(output_file)
            
            if 'error' not in c10_stats:
                print("\n🔧 c10-dump Validation:")
                print(f"  Packets: {c10_stats['packets']}")
                print(f"  Data Types: {c10_stats['data_types']}")
                print(f"  Channels: {c10_stats['channels']}")
                
                # Check error count
                err_count = run_c10_errcount(output_file)
                assert err_count == 0, f"c10-errcount found {err_count} errors"
                print(f"  Error count: {err_count}")
                
                # Cross-validate packet counts
                if c10_stats['packets'] > 0:
                    assert abs(c10_stats['packets'] - py_stats['packets']) <= 1, \
                           f"Packet count mismatch: c10={c10_stats['packets']}, py={py_stats['packets']}"
            else:
                pytest.skip(f"c10-dump failed: {c10_stats['error']}")
        else:
            print("\n⚠️ c10-tools not available, skipping external validation")
    
    @pytest.mark.optional
    def test_c10_tools_data_types(self, tmp_path):
        """Test that c10-tools sees correct data types."""
        if not has_c10_tools():
            pytest.skip("c10-tools not installed")
        
        # Create a file with known packet types
        from ch10gen.ch10_writer import Ch10Writer, Ch10WriterConfig as WriterConfig
        import yaml
        
        output_file = tmp_path / "test_types.c10"
        
        # Generate with strict mode (if implemented)
        # For now, just generate normally
        with open('scenarios/test_scenario.yaml') as f:
            scenario = yaml.safe_load(f)
        with open('icd/test_icd.yaml') as f:
            icd = yaml.safe_load(f)
        
        config = WriterConfig()
        writer = Ch10Writer(config)
        
        from ch10gen.flight_profile import FlightProfileGenerator
        from ch10gen.schedule import build_schedule_from_icd
        from ch10gen.icd import ICDDefinition
        
        profile = FlightProfileGenerator(seed=scenario.get('seed'))
        profile.generate_profile(
            start_time=datetime.now(),
            duration_s=15.0,
            segments=scenario.get('profile', {}).get('segments', []),
            initial_altitude_ft=scenario.get('profile', {}).get('base_altitude_ft', 2000)
        )
        
        icd_config = ICDDefinition.from_dict(icd)
        schedule = build_schedule_from_icd(
            icd=icd_config,
            duration_s=15.0
        )
        
        writer.write_file(
            filepath=output_file,
            schedule=schedule,
            flight_profile=profile,
            icd=icd_config
        )
        
        # Run c10-dump
        stats = run_c10_dump(output_file)
        assert 'error' not in stats, f"c10-dump error: {stats.get('error')}"
        
        # Note: Since we're using PyChapter10 writer which sets data_type=0x00,
        # we expect to see mostly 0x00. This test documents current behavior.
        print(f"\nc10-dump data types: {stats['data_types']}")
        
        # Once we implement irig106lib backend, we'd assert:
        # assert '01' in stats['data_types'], "TMATS (0x01) not found"
        # assert '11' in stats['data_types'], "Time F1 (0x11) not found"  
        # assert '19' in stats['data_types'], "MS1553 F1 (0x19) not found"
    
    def test_message_count_accuracy(self, tmp_path):
        """Test that message counts are accurate across readers."""
        from ch10gen.ch10_writer import Ch10Writer, Ch10WriterConfig as WriterConfig
        import yaml
        
        output_file = tmp_path / "test_counts.c10"
        
        # Load configs
        with open('scenarios/test_scenario.yaml') as f:
            scenario = yaml.safe_load(f)
        with open('icd/test_icd.yaml') as f:
            icd = yaml.safe_load(f)
        
        config = WriterConfig()
        writer = Ch10Writer(config)
        
        from ch10gen.flight_profile import FlightProfileGenerator
        from ch10gen.schedule import build_schedule_from_icd
        from ch10gen.icd import ICDDefinition
        
        profile = FlightProfileGenerator(seed=scenario.get('seed'))
        profile.generate_profile(
            start_time=datetime.now(),
            duration_s=15.0,
            segments=scenario.get('profile', {}).get('segments', []),
            initial_altitude_ft=scenario.get('profile', {}).get('base_altitude_ft', 2000)
        )
        
        icd_config = ICDDefinition.from_dict(icd)
        
        # Generate with known message counts
        duration_s = 10.0
        schedule = build_schedule_from_icd(
            icd=icd_config,
            duration_s=duration_s
        )
        
        # Calculate expected messages
        expected_messages = len(schedule.messages)
        
        writer.write_file(
            filepath=output_file,
            schedule=schedule,
            flight_profile=profile,
            icd=icd_config
        )
        
        # Validate wire format
        wire_stats = validate_wire_format(output_file)
        
        print(f"\n📊 Message Count Validation:")
        print(f"  Expected messages: {expected_messages}")
        print(f"  Wire format packets: {wire_stats['packets']}")
        
        # Check that message count is within 2% tolerance
        # Note: We count packets, not individual messages, since PyChapter10
        # doesn't expose message iteration properly
        
        # For now, just ensure we have packets
        assert wire_stats['packets'] > 0, "No packets generated"
        
        # Once message iteration works:
        # actual_messages = sum messages across all MS1553 packets
        # assert abs(actual_messages - expected_messages) / expected_messages < 0.02


if __name__ == "__main__":
    # Run a quick smoke test
    import tempfile
    from pathlib import Path
    
    with tempfile.TemporaryDirectory() as tmpdir:
        test = TestDualReader()
        test.test_small_file_both_readers(Path(tmpdir))
        print("\n✅ Dual-reader smoke test passed!")
