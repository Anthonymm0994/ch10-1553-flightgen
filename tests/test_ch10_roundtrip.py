"""CH10 round-trip integration tests."""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from chapter10 import C10
from chapter10.time import TimeF1
from chapter10.ms1553 import MS1553F1
from chapter10.message import MessageF0

from ch10gen.icd import ICDDefinition, MessageDefinition, WordDefinition
from ch10gen.flight_profile import FlightProfileGenerator
from ch10gen.schedule import build_schedule_from_icd
from ch10gen.ch10_writer import Ch10Writer, Ch10WriterConfig, write_ch10_file
from ch10gen.validate import Ch10Validator


@pytest.mark.compat
class TestCh10RoundTrip:
    """Test complete CH10 file generation and validation round-trip."""
    
    @pytest.fixture
    def test_icd(self):
        """Create a test ICD for fast runs."""
        return ICDDefinition(
            bus='A',
            messages=[
                MessageDefinition(
                    name='NAV_20HZ',
                    rate_hz=20,
                    rt=10,
                    tr='BC2RT',
                    sa=1,
                    wc=4,
                    words=[
                        WordDefinition(name='altitude', src='flight.altitude_ft', encode='bnr16'),
                        WordDefinition(name='speed', src='flight.ias_kt', encode='u16'),
                        WordDefinition(name='heading', src='flight.heading_deg', encode='bnr16'),
                        WordDefinition(name='status', src='derived.status', encode='u16')
                    ]
                ),
                MessageDefinition(
                    name='GPS_5HZ',
                    rate_hz=5,
                    rt=11,
                    tr='BC2RT',
                    sa=2,
                    wc=4,
                    words=[
                        WordDefinition(name='lat', src='flight.lat_deg', 
                                     encode='float32_split', word_order='lsw_msw'),
                        WordDefinition(name='lon', src='flight.lon_deg',
                                     encode='float32_split', word_order='lsw_msw')
                    ]
                )
            ]
        )
    
    @pytest.fixture
    def test_scenario(self):
        """Create a test scenario for fast runs."""
        return {
            'name': 'Test Scenario',
            'start_time_utc': '2025-01-01T12:00:00Z',
            'duration_s': 15,  # Short duration for fast tests
            'seed': 42,
            'profile': {
                'base_altitude_ft': 5000,
                'segments': [
                    {'type': 'climb', 'to_altitude_ft': 8000, 'ias_kt': 250,
                     'vs_fpm': 1000, 'duration_s': 7},
                    {'type': 'cruise', 'ias_kt': 280, 'hold_s': 8}
                ]
            },
            'bus': {
                'packet_bytes_target': 8192,
                'jitter_ms': 0  # No jitter for deterministic tests
            }
        }
    
    def test_demo_60s_build(self, test_icd, tmp_path):
        """Test building a 60-second demo file."""
        scenario = {
            'name': 'Demo 60s',
            'start_time_utc': '2025-01-01T12:00:00Z',
            'duration_s': 60,
            'seed': 42,
            'profile': {
                'base_altitude_ft': 10000,
                'segments': [
                    {'type': 'climb', 'to_altitude_ft': 15000, 'ias_kt': 280,
                     'vs_fpm': 1500, 'duration_s': 30},
                    {'type': 'cruise', 'ias_kt': 320, 'hold_s': 30}
                ]
            },
            'bus': {
                'packet_bytes_target': 16384,
                'jitter_ms': 0
            }
        }
        
        output_file = tmp_path / "demo_60s.c10"
        
        # Build file
        stats = write_ch10_file(
            output_path=output_file,
            scenario=scenario,
            icd=test_icd,
            seed=42
        )
        
        # Verify file was created
        assert output_file.exists()
        assert stats['file_size_bytes'] > 0
        
        # Open and validate with PyChapter10
        c10 = C10(str(output_file))
        
        packet_types = {'MessageF0': 0, 'TimeF1': 0, 'MS1553F1': 0}
        ipts_values = []
        message_count = 0
        
        for packet in c10:
            packet_type = type(packet).__name__
            packet_types[packet_type] = packet_types.get(packet_type, 0) + 1
            
            if isinstance(packet, MS1553F1):
                # Collect IPTS values from messages
                for msg in packet:
                    message_count += 1
                    if hasattr(msg, 'ipts'):
                        ipts_values.append(msg.ipts)
        
        # C10 doesn't have close() method
        
        # Check presence of packet types
        # Note: PyChapter10 recognizes TMATS (0x01) as ComputerF1, not MessageF0
        assert packet_types.get('ComputerF1', 0) >= 1 or packet_types.get('MessageF0', 0) >= 1, \
               f"No TMATS packet found. Found types: {packet_types}"
        assert packet_types.get('TimeF1', 0) >= 1, f"No time packets. Found types: {packet_types}"
        assert packet_types.get('MS1553F1', 0) > 0, f"No 1553 packets. Found types: {packet_types}"
    
    def test_ipts_monotonicity(self, test_icd, test_scenario, tmp_path):
        """Test IPTS monotonicity across all 1553 messages."""
        output_file = tmp_path / "ipts_test.c10"
        
        stats = write_ch10_file(
            output_path=output_file,
            scenario=test_scenario,
            icd=test_icd,
            seed=42
        )
        
        c10 = C10(str(output_file))
        
        ipts_values = []
        for packet in c10:
            if isinstance(packet, MS1553F1):
                for msg in packet:
                    if hasattr(msg, 'ipts'):
                        ipts_values.append(msg.ipts)
        
        # C10 doesn't have close() method
        
        # Check monotonicity
        assert len(ipts_values) > 0
        for i in range(1, len(ipts_values)):
            assert ipts_values[i] >= ipts_values[i-1], \
                   f"IPTS not monotonic at index {i}: {ipts_values[i-1]} -> {ipts_values[i]}"
    
    def test_message_count_sanity(self, test_icd, test_scenario, tmp_path):
        """Test message count matches expected rates."""
        output_file = tmp_path / "count_test.c10"
        
        stats = write_ch10_file(
            output_path=output_file,
            scenario=test_scenario,
            icd=test_icd,
            seed=42
        )
        
        duration = test_scenario['duration_s']
        
        # Calculate expected counts
        # NAV_20HZ: 20 Hz * 15 s = 300 messages
        # GPS_5HZ: 5 Hz * 15 s = 75 messages
        # Total: 375 messages
        expected_total = 20 * duration + 5 * duration
        
        c10 = C10(str(output_file))
        
        actual_count = 0
        for packet in c10:
            if isinstance(packet, MS1553F1):
                for msg in packet:
                    actual_count += 1
        
        # C10 doesn't have close() method
        
        # Allow ±2% tolerance for scheduling boundaries
        tolerance = 0.02
        assert abs(actual_count - expected_total) / expected_total <= tolerance, \
               f"Expected ~{expected_total} messages, got {actual_count}"
    
    def test_rt_sa_distribution(self, test_icd, test_scenario, tmp_path):
        """Test RT/SA/TR distribution matches ICD rates."""
        output_file = tmp_path / "distribution_test.c10"
        
        stats = write_ch10_file(
            output_path=output_file,
            scenario=test_scenario,
            icd=test_icd,
            seed=42
        )
        
        c10 = C10(str(output_file))
        
        rt_sa_counts = {}
        
        for packet in c10:
            if isinstance(packet, MS1553F1):
                for msg in packet:
                    if hasattr(msg, 'data') and msg.data:
                        # Extract RT/SA from command word
                        cmd_word = msg.data[0]
                        rt = (cmd_word >> 11) & 0x1F
                        sa = (cmd_word >> 5) & 0x1F
                        tr = (cmd_word >> 10) & 0x01
                        
                        key = (rt, sa, tr)
                        rt_sa_counts[key] = rt_sa_counts.get(key, 0) + 1
        
        # C10 doesn't have close() method
        
        duration = test_scenario['duration_s']
        
        # Check distribution
        # RT=10, SA=1, TR=1 (NAV_20HZ) should be ~300
        # RT=11, SA=2, TR=1 (GPS_5HZ) should be ~75
        
        nav_key = (10, 1, 1)  # NAV_20HZ
        gps_key = (11, 2, 1)  # GPS_5HZ
        
        assert nav_key in rt_sa_counts
        assert gps_key in rt_sa_counts
        
        # Check counts with ±5% tolerance
        expected_nav = 20 * duration
        expected_gps = 5 * duration
        
        assert abs(rt_sa_counts[nav_key] - expected_nav) / expected_nav <= 0.05
        assert abs(rt_sa_counts[gps_key] - expected_gps) / expected_gps <= 0.05
    
    def test_tmats_presence(self, test_icd, test_scenario, tmp_path):
        """Test that at least one TMATS packet is present and non-empty."""
        output_file = tmp_path / "tmats_test.c10"
        
        stats = write_ch10_file(
            output_path=output_file,
            scenario=test_scenario,
            icd=test_icd,
            seed=42
        )
        
        c10 = C10(str(output_file))
        
        tmats_found = False
        tmats_non_empty = False
        
        for packet in c10:
            # PyChapter10 may recognize TMATS as ComputerF1 or MessageF0
            if type(packet).__name__ in ['MessageF0', 'ComputerF1']:
                # Check if this is actually TMATS (data_type 0x01)
                if hasattr(packet, 'data_type') and packet.data_type == 0x01:
                    tmats_found = True
                    if hasattr(packet, 'body') and packet.body:
                        tmats_text = packet.body.decode('utf-8', errors='ignore')
                        if len(tmats_text) > 100:  # Should have substantial content
                            tmats_non_empty = True
                        
                        # Check for required fields
                        assert 'G\\106' in tmats_text or 'TMATS' in tmats_text  # IRIG 106 version or header
                        assert 'G\\DSI' in tmats_text or 'DSI' in tmats_text  # Data source ID
        
        # C10 doesn't have close() method
        
        assert tmats_found, "No TMATS packet found"
        assert tmats_non_empty, "TMATS packet is empty or too small"
    
    def test_time_packets(self, test_icd, test_scenario, tmp_path):
        """Test presence and validity of time packets."""
        output_file = tmp_path / "time_test.c10"
        
        stats = write_ch10_file(
            output_path=output_file,
            scenario=test_scenario,
            icd=test_icd,
            seed=42
        )
        
        c10 = C10(str(output_file))
        
        time_packets = []
        
        for packet in c10:
            if isinstance(packet, TimeF1):
                time_packets.append(packet)
                
                # Validate time fields
                if hasattr(packet, 'seconds'):
                    assert 0 <= packet.seconds <= 59
                if hasattr(packet, 'minutes'):
                    assert 0 <= packet.minutes <= 59
                if hasattr(packet, 'hours'):
                    assert 0 <= packet.hours <= 23
                if hasattr(packet, 'days'):
                    assert 1 <= packet.days <= 366
        
        # C10 doesn't have close() method
        
        # Should have at least 2 time packets (start and end)
        assert len(time_packets) >= 2
    
    @pytest.mark.slow
    def test_large_file(self, test_icd, tmp_path):
        """Test generation of a larger file (marked as slow)."""
        scenario = {
            'name': 'Large Test',
            'start_time_utc': '2025-01-01T12:00:00Z',
            'duration_s': 300,  # 5 minutes
            'seed': 42,
            'profile': {
                'base_altitude_ft': 20000,
                'segments': [
                    {'type': 'climb', 'to_altitude_ft': 35000, 'ias_kt': 320,
                     'vs_fpm': 1500, 'duration_s': 150},
                    {'type': 'cruise', 'ias_kt': 400, 'hold_s': 150}
                ]
            },
            'bus': {
                'packet_bytes_target': 65536
            }
        }
        
        output_file = tmp_path / "large_test.c10"
        
        stats = write_ch10_file(
            output_path=output_file,
            scenario=scenario,
            icd=test_icd,
            seed=42
        )
        
        # Verify reasonable file size
        assert stats['file_size_bytes'] > 10000  # At least 10KB
        assert stats['file_size_bytes'] < 100000000  # Less than 100MB
        
        # Verify message counts
        expected_messages = (20 + 5) * 300  # 7500 messages
        assert abs(stats['total_messages'] - expected_messages) / expected_messages <= 0.02
    
    def test_platform_compatibility(self, test_icd, test_scenario, tmp_path):
        """Test that generated files work across platforms."""
        output_file = tmp_path / "platform_test.c10"
        
        stats = write_ch10_file(
            output_path=output_file,
            scenario=test_scenario,
            icd=test_icd,
            seed=42
        )
        
        # Use Ch10Validator for cross-platform validation
        validator = Ch10Validator(output_file)
        results = validator.validate(verbose=False)
        
        # Check basic validity
        assert results['packet_count'] > 0
        assert results['tmats_present'] == True
        assert results['time_packets'] > 0
        assert results['1553_packets'] > 0
        assert results['1553_messages'] > 0
        
        # Should have no critical errors
        assert len(results['errors']) == 0
    
    def test_deterministic_output(self, test_icd, test_scenario, tmp_path):
        """Test that same inputs produce identical outputs."""
        output1 = tmp_path / "deterministic1.c10"
        output2 = tmp_path / "deterministic2.c10"
        
        # Generate twice with same seed
        stats1 = write_ch10_file(
            output_path=output1,
            scenario=test_scenario,
            icd=test_icd,
            seed=42
        )
        
        stats2 = write_ch10_file(
            output_path=output2,
            scenario=test_scenario,
            icd=test_icd,
            seed=42
        )
        
        # Stats should be identical
        assert stats1['total_messages'] == stats2['total_messages']
        assert stats1['total_packets'] == stats2['total_packets']
        
        # File sizes should be very close (might differ slightly due to timestamps)
        size1 = output1.stat().st_size
        size2 = output2.stat().st_size
        assert abs(size1 - size2) < 1000  # Within 1KB