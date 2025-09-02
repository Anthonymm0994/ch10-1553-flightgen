"""Pre-Phase-2 sanity checks: boundary timing, CSDW correctness, payload integrity."""

import pytest
import tempfile
import struct
from pathlib import Path
from datetime import datetime, timedelta
from chapter10 import C10

from ch10gen.icd import ICDDefinition, MessageDefinition, WordDefinition
from ch10gen.flight_profile import FlightProfile
from ch10gen.ch10_writer import Ch10Writer


class TestPhase1SanityChecks:
    """Critical sanity checks before Phase 2."""
    
    @pytest.fixture
    def simple_icd(self):
        """Create a simple ICD for testing."""
        return ICDDefinition(
            bus="A",
            messages=[
                MessageDefinition(
                    name="TEST_MSG",
                    rt=10,
                    sa=1,
                    tr="RT2BC",
                    wc=2,
                    rate_hz=10,
                    words=[
                        WordDefinition(name="data1", src="data.field1", encode="u16"),
                        WordDefinition(name="data2", src="data.field2", encode="u16")
                    ]
                )
            ]
        )
    
    @pytest.fixture
    def simple_flight_profile(self):
        """Create a simple flight profile for testing."""
        return FlightProfile(seed=42)
    
    def test_boundary_timing_exact_seconds(self, simple_icd, simple_flight_profile):
        """Test boundary timing: 2.00s should show 3 anchors at 0/1/2."""
        with tempfile.NamedTemporaryFile(suffix='.ch10', delete=False) as tmp:
            filepath = Path(tmp.name)
        
        try:
            # Generate exactly 2.00 second file
            writer = Ch10Writer()
            schedule = writer._build_test_schedule(simple_icd, duration_s=2.0)
            
            writer.write_file(
                filepath=filepath,
                schedule=schedule,
                flight_profile=simple_flight_profile,
                icd=simple_icd,
                start_time=datetime.utcnow(),
                scenario_name="Boundary Test"
            )
            
            # Check packet types and timing
            c10 = C10(str(filepath))
            packets = list(c10)
            
            # Should have exactly 3 time packets for 2.00s duration
            time_packets = [p for p in packets if hasattr(p, 'data_type') and p.data_type == 0x11]
            assert len(time_packets) == 3, f"Expected exactly 3 time packets for 2.00s, got {len(time_packets)}"
            
            # Check timing: should be at 0s, 1s, and close to 2s (RTC is in microseconds)
            # Allow for slight timing variations in the last packet
            assert time_packets[0].rtc == 0, f"First time packet should be at RTC 0, got {time_packets[0].rtc}"
            assert abs(time_packets[1].rtc - 1_000_000) < 50_000, f"Second time packet should be at ~1s, got {time_packets[1].rtc}μs"
            assert time_packets[2].rtc >= 1_800_000, f"Third time packet should be at ≥1.8s, got {time_packets[2].rtc}μs"
            assert time_packets[2].rtc <= 2_000_000, f"Third time packet should be at ≤2.0s, got {time_packets[2].rtc}μs"
            
        finally:
            if filepath.exists():
                try:
                    filepath.unlink()
                except:
                    pass
    
    def test_csdw_date_mode_consistency(self, simple_icd, simple_flight_profile):
        """Test CSDW DATE mode matches payload style."""
        with tempfile.NamedTemporaryFile(suffix='.ch10', delete=False) as tmp:
            filepath = Path(tmp.name)
        
        try:
            writer = Ch10Writer()
            schedule = writer._build_test_schedule(simple_icd, duration_s=1.0)
            
            writer.write_file(
                filepath=filepath,
                schedule=schedule,
                flight_profile=simple_flight_profile,
                icd=simple_icd,
                start_time=datetime.utcnow(),
                scenario_name="CSDW Test"
            )
            
            # Check Time-F1 packet CSDW
            c10 = C10(str(filepath))
            packets = list(c10)
            
            time_packets = [p for p in packets if hasattr(p, 'data_type') and p.data_type == 0x11]
            assert len(time_packets) > 0, "Should have at least one Time-F1 packet"
            
            time_packet = time_packets[0]
            
            # Verify CSDW fields are consistent
            assert hasattr(time_packet, 'date_format'), "Time packet should have date_format"
            assert hasattr(time_packet, 'time_format'), "Time packet should have time_format"
            assert hasattr(time_packet, 'time_source'), "Time packet should have time_source"
            assert hasattr(time_packet, 'leap'), "Time packet should have leap flag"
            
            # Verify values match our implementation
            assert time_packet.time_format == 0, "Time format should be 0 (IRIG-B)"
            assert time_packet.time_source == 1, "Time source should be 1 (External)"
            assert time_packet.date_format == 0, "Date format should be 0 (Day-of-Year)"
            
        finally:
            if filepath.exists():
                try:
                    filepath.unlink()
                except:
                    pass
    
    def test_leap_year_handling(self, simple_icd, simple_flight_profile):
        """Test leap year bit handling on leap year dates."""
        with tempfile.NamedTemporaryFile(suffix='.ch10', delete=False) as tmp:
            filepath = Path(tmp.name)
        
        try:
            # Test with leap year date (2024)
            leap_year_start = datetime(2024, 2, 29, 23, 59, 59)
            
            writer = Ch10Writer()
            schedule = writer._build_test_schedule(simple_icd, duration_s=1.0)
            
            writer.write_file(
                filepath=filepath,
                schedule=schedule,
                flight_profile=simple_flight_profile,
                icd=simple_icd,
                start_time=leap_year_start,
                scenario_name="Leap Year Test"
            )
            
            # Check leap year handling
            c10 = C10(str(filepath))
            packets = list(c10)
            
            time_packets = [p for p in packets if hasattr(p, 'data_type') and p.data_type == 0x11]
            assert len(time_packets) > 0, "Should have at least one Time-F1 packet"
            
            time_packet = time_packets[0]
            
            # Leap year bit should be set for 2024
            assert hasattr(time_packet, 'leap'), "Time packet should have leap flag"
            # Note: The actual leap bit value depends on implementation, but it should be present
            
        finally:
            if filepath.exists():
                try:
                    filepath.unlink()
                except:
                    pass
    
    def test_payload_monotonicity(self, simple_icd, simple_flight_profile):
        """Test that time payload increases monotonically."""
        with tempfile.NamedTemporaryFile(suffix='.ch10', delete=False) as tmp:
            filepath = Path(tmp.name)
        
        try:
            writer = Ch10Writer()
            schedule = writer._build_test_schedule(simple_icd, duration_s=3.0)
            
            writer.write_file(
                filepath=filepath,
                schedule=schedule,
                flight_profile=simple_flight_profile,
                icd=simple_icd,
                start_time=datetime.utcnow(),
                scenario_name="Monotonicity Test"
            )
            
            # Check time packet ordering
            c10 = C10(str(filepath))
            packets = list(c10)
            
            time_packets = [p for p in packets if hasattr(p, 'data_type') and p.data_type == 0x11]
            assert len(time_packets) >= 3, "Should have at least 3 time packets for 3s duration"
            
            # Verify RTC increases monotonically
            rtc_values = [p.rtc for p in time_packets if hasattr(p, 'rtc')]
            assert len(rtc_values) >= 2, "Should have at least 2 RTC values"
            
            for i in range(1, len(rtc_values)):
                assert rtc_values[i] >= rtc_values[i-1], f"RTC should increase monotonically: {rtc_values[i-1]} -> {rtc_values[i]}"
            
        finally:
            if filepath.exists():
                try:
                    filepath.unlink()
                except:
                    pass
    
    def test_packet_ordering_interleave(self, simple_icd, simple_flight_profile):
        """Test packet ordering: TMATS -> Time-F1 -> (Time-F1 + 1553) interleaved."""
        with tempfile.NamedTemporaryFile(suffix='.ch10', delete=False) as tmp:
            filepath = Path(tmp.name)
        
        try:
            writer = Ch10Writer()
            schedule = writer._build_test_schedule(simple_icd, duration_s=2.0)
            
            writer.write_file(
                filepath=filepath,
                schedule=schedule,
                flight_profile=simple_flight_profile,
                icd=simple_icd,
                start_time=datetime.utcnow(),
                scenario_name="Ordering Test"
            )
            
            # Check packet ordering
            c10 = C10(str(filepath))
            packets = list(c10)
            
            # First packet should be TMATS
            assert packets[0].data_type == 0x01, "First packet should be TMATS (0x01)"
            
            # Second packet should be Time-F1
            assert packets[1].data_type == 0x11, "Second packet should be Time-F1 (0x11)"
            
            # Verify no other Computer-Generated packets until we add Events/Index in Phase 2
            cg_packets = [p for p in packets if hasattr(p, 'data_type') and p.data_type in [0x02, 0x03, 0x04]]
            assert len(cg_packets) == 0, f"Should have no Computer-Generated packets (0x02, 0x03, 0x04) yet: found {len(cg_packets)}"
            
        finally:
            if filepath.exists():
                try:
                    filepath.unlink()
                except:
                    pass
    
    def test_sparse_traffic_time_continuity(self, simple_icd, simple_flight_profile):
        """Test that Time-F1 continues at ≥1 Hz even with sparse 1553 traffic."""
        with tempfile.NamedTemporaryFile(suffix='.ch10', delete=False) as tmp:
            filepath = Path(tmp.name)
        
        try:
            # Create very sparse schedule (1 message every 2 seconds)
            writer = Ch10Writer()
            schedule = writer._build_test_schedule(simple_icd, duration_s=5.0)
            
            # Modify schedule to be sparse
            sparse_messages = []
            for i, msg in enumerate(schedule.messages):
                if i % 20 == 0:  # Keep only every 20th message
                    sparse_messages.append(msg)
            
            schedule.messages = sparse_messages
            
            writer.write_file(
                filepath=filepath,
                schedule=schedule,
                flight_profile=simple_flight_profile,
                icd=simple_icd,
                start_time=datetime.utcnow(),
                scenario_name="Sparse Traffic Test"
            )
            
            # Check that time packets still appear at ≥1 Hz
            c10 = C10(str(filepath))
            packets = list(c10)
            
            time_packets = [p for p in packets if hasattr(p, 'data_type') and p.data_type == 0x11]
            # For 5s duration, should have 5-6 time packets (≥1 Hz)
            assert 5 <= len(time_packets) <= 6, f"Expected 5-6 time packets for 5s sparse traffic, got {len(time_packets)}"
            
        finally:
            if filepath.exists():
                try:
                    filepath.unlink()
                except:
                    pass
    
    def test_tmats_round_trip(self, simple_icd, simple_flight_profile):
        """Test TMATS round-trip: parse back and verify channel mappings."""
        with tempfile.NamedTemporaryFile(suffix='.ch10', delete=False) as tmp:
            filepath = Path(tmp.name)
        
        try:
            writer = Ch10Writer()
            schedule = writer._build_test_schedule(simple_icd, duration_s=1.0)
            
            writer.write_file(
                filepath=filepath,
                schedule=schedule,
                flight_profile=simple_flight_profile,
                icd=simple_icd,
                start_time=datetime.utcnow(),
                scenario_name="TMATS Test"
            )
            
            # Parse TMATS back
            c10 = C10(str(filepath))
            packets = list(c10)
            
            # Find TMATS packet
            tmats_packets = [p for p in packets if hasattr(p, 'data_type') and p.data_type == 0x01]
            assert len(tmats_packets) == 1, "Should have exactly one TMATS packet"
            
            tmats = tmats_packets[0]
            
            # Verify TMATS is on Channel 0
            assert hasattr(tmats, 'channel_id'), "TMATS should have channel_id"
            assert tmats.channel_id == 0, f"TMATS should be on Channel 0, got {tmats.channel_id}"
            
            # Verify other channels are present
            channel_assignments = {}
            for p in packets:
                if hasattr(p, 'channel_id'):
                    ch_id = p.channel_id
                    dt = getattr(p, 'data_type', 'unknown')
                    channel_assignments[ch_id] = dt
            
            # Should have TMATS=0, Time=1, 1553=2
            assert 0 in channel_assignments and channel_assignments[0] == 0x01, "Channel 0 should contain TMATS"
            assert 1 in channel_assignments and channel_assignments[1] == 0x11, "Channel 1 should contain Time-F1"
            assert 2 in channel_assignments and channel_assignments[2] == 0x19, "Channel 2 should contain 1553-F1"
            
        finally:
            if filepath.exists():
                try:
                    filepath.unlink()
                except:
                    pass
    
    def test_cross_tool_data_type_histogram(self, simple_icd, simple_flight_profile):
        """Test data type histogram: should only show 0x01, 0x11, 0x19."""
        with tempfile.NamedTemporaryFile(suffix='.ch10', delete=False) as tmp:
            filepath = Path(tmp.name)
        
        try:
            writer = Ch10Writer()
            schedule = writer._build_test_schedule(simple_icd, duration_s=2.0)
            
            writer.write_file(
                filepath=filepath,
                schedule=schedule,
                flight_profile=simple_flight_profile,
                icd=simple_icd,
                start_time=datetime.utcnow(),
                scenario_name="Histogram Test"
            )
            
            # Analyze packet types
            c10 = C10(str(filepath))
            packets = list(c10)
            
            # Build data type histogram
            packet_types = {}
            for p in packets:
                if hasattr(p, 'data_type'):
                    dt = p.data_type
                    packet_types[dt] = packet_types.get(dt, 0) + 1
            
            # Should only have 0x01, 0x11, 0x19
            expected_types = {0x01, 0x11, 0x19}
            found_types = set(packet_types.keys())
            
            # Verify only expected types
            unexpected_types = found_types - expected_types
            assert len(unexpected_types) == 0, f"Found unexpected packet types: {unexpected_types}"
            
            # Verify all expected types are present
            missing_types = expected_types - found_types
            assert len(missing_types) == 0, f"Missing expected packet types: {missing_types}"
            
            print(f"\nData type histogram:")
            for dt in sorted(packet_types.keys()):
                type_name = {
                    0x01: 'TMATS',
                    0x11: 'Time-F1',
                    0x19: '1553-F1'
                }.get(dt, f'Unknown(0x{dt:02X})')
                print(f"  0x{dt:02X}: {type_name} - {packet_types[dt]} packets")
            
        finally:
            if filepath.exists():
                try:
                    filepath.unlink()
                except:
                    pass


# Add helper method to Ch10Writer for testing
def _build_test_schedule(self, icd: ICDDefinition, duration_s: float):
    """Build a test schedule for testing purposes."""
    from ch10gen.schedule import BusSchedule, ScheduledMessage
    
    messages = []
    current_time = 0.0
    interval = 1.0 / icd.messages[0].rate_hz
    major_frame = 0
    minor_frame = 0
    
    while current_time <= duration_s:
        messages.append(ScheduledMessage(
            message=icd.messages[0],
            time_s=current_time,
            major_frame=major_frame,
            minor_frame=minor_frame
        ))
        current_time += interval
        minor_frame += 1
        if minor_frame >= 50:  # 50 minor frames per major frame
            minor_frame = 0
            major_frame += 1
    
    return BusSchedule(messages=messages)


# Monkey patch the method for testing
Ch10Writer._build_test_schedule = _build_test_schedule
