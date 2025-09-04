"""Test Phase 1 compliance: Time-F1 packets, channel assignments, and validation."""

import pytest
import tempfile
import json
from pathlib import Path
from datetime import datetime
from chapter10 import C10

from ch10gen.icd import ICDDefinition, MessageDefinition, WordDefinition
from ch10gen.scenario import load_scenario
from ch10gen.ch10_writer import Ch10Writer, Ch10WriterConfig
from ch10gen.validate import validate_file
from ch10gen.flight_profile import FlightProfile


class TestPhase1Compliance:
    """Test Phase 1 compliance with IRIG-106 standard."""
    
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
                        WordDefinition(
                            name="data1",
                            src="data.field1",
                            encode="u16"
                        ),
                        WordDefinition(
                            name="data2",
                            src="data.field2",
                            encode="u16"
                        )
                    ]
                )
            ]
        )
    
    @pytest.fixture
    def simple_scenario(self):
        """Create a simple scenario for testing."""
        return {
            "config": {
                "default_mode": "random"
            },
            "random_config": {
                "populate_all_fields": True
            }
        }
    
    @pytest.fixture
    def simple_flight_profile(self):
        """Create a simple flight profile for testing."""
        return FlightProfile(seed=42)
    
    def test_time_packet_data_type_correct(self, simple_icd, simple_scenario, simple_flight_profile):
        """Test that time packets use data_type = 0x11 (Time Data, Format 1)."""
        with tempfile.NamedTemporaryFile(suffix='.ch10', delete=False) as tmp:
            filepath = Path(tmp.name)
        
        try:
            # Generate CH10 file
            writer = Ch10Writer()
            schedule = writer._build_test_schedule(simple_icd, duration_s=3.0)
            
            writer.write_file(
                filepath=filepath,
                schedule=schedule,
                flight_profile=simple_flight_profile,
                icd=simple_icd,
                start_time=datetime.utcnow(),
                scenario_name="Phase1 Test"
            )
            
            # Verify file was created
            assert filepath.exists()
            assert filepath.stat().st_size > 0
            
            # Check packet types
            c10 = C10(str(filepath))
            packets = list(c10)
            
            # Should have TMATS, time packets, and 1553 packets
            packet_types = {}
            for p in packets:
                if hasattr(p, 'data_type'):
                    dt = p.data_type
                    packet_types[dt] = packet_types.get(dt, 0) + 1
            
            # Verify correct data types
            assert 0x01 in packet_types, "TMATS packets (0x01) should be present"
            assert 0x11 in packet_types, "Time-F1 packets (0x11) should be present"
            assert 0x19 in packet_types, "1553-F1 packets (0x19) should be present"
            
            # Verify NO 0x02 packets (those are for events, not time)
            assert 0x02 not in packet_types, "No Computer-Generated packets (0x02) should be present for time"
            
            # Verify time packet count (should be ≥1 Hz for 3 seconds = 3-4 packets)
            time_packet_count = packet_types.get(0x11, 0)
            assert 3 <= time_packet_count <= 4, f"Expected 3-4 time packets for 3s duration, got {time_packet_count}"
            
        finally:
            if filepath.exists():
                filepath.unlink()
    
    def test_channel_assignments_correct(self, simple_icd, simple_scenario, simple_flight_profile):
        """Test that channel assignments follow IRIG-106 standard."""
        with tempfile.NamedTemporaryFile(suffix='.ch10', delete=False) as tmp:
            filepath = Path(tmp.name)
        
        try:
            # Generate CH10 file
            writer = Ch10Writer()
            schedule = writer._build_test_schedule(simple_icd, duration_s=2.0)
            
            writer.write_file(
                filepath=filepath,
                schedule=schedule,
                flight_profile=simple_flight_profile,
                icd=simple_icd,
                start_time=datetime.utcnow(),
                scenario_name="Channel Test"
            )
            
            # Check channel assignments
            c10 = C10(str(filepath))
            packets = list(c10)
            
            channel_assignments = {}
            for p in packets:
                if hasattr(p, 'channel_id'):
                    ch_id = p.channel_id
                    dt = getattr(p, 'data_type', 'unknown')
                    channel_assignments[ch_id] = dt
            
            # Verify channel assignments
            assert 0 in channel_assignments, "Channel 0 should be present (TMATS)"
            assert channel_assignments[0] == 0x01, "Channel 0 should contain TMATS (0x01)"
            
            assert 1 in channel_assignments, "Channel 1 should be present (Time)"
            assert channel_assignments[1] == 0x11, "Channel 1 should contain Time-F1 (0x11)"
            
            assert 2 in channel_assignments, "Channel 2 should be present (1553)"
            assert channel_assignments[2] == 0x19, "Channel 2 should contain 1553-F1 (0x19)"
            
        finally:
            if filepath.exists():
                filepath.unlink()
    
    def test_time_packet_csdw_fields(self, simple_icd, simple_scenario, simple_flight_profile):
        """Test that Time-F1 packets have proper CSDW fields."""
        with tempfile.NamedTemporaryFile(suffix='.ch10', delete=False) as tmp:
            filepath = Path(tmp.name)
        
        try:
            # Generate CH10 file
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
            
            # Check Time-F1 packet structure
            c10 = C10(str(filepath))
            packets = list(c10)
            
            time_packets = [p for p in packets if hasattr(p, 'data_type') and p.data_type == 0x11]
            assert len(time_packets) > 0, "Should have at least one Time-F1 packet"
            
            # Check first time packet
            time_packet = time_packets[0]
            
            # Verify CSDW fields are present
            assert hasattr(time_packet, 'time_format'), "Time packet should have time_format"
            assert hasattr(time_packet, 'time_source'), "Time packet should have time_source"
            assert hasattr(time_packet, 'leap'), "Time packet should have leap flag"
            
            # Verify time values are present (PyChapter10 uses different attribute names)
            assert hasattr(time_packet, 'time'), "Time packet should have time"
            
            # Verify reasonable values
            assert hasattr(time_packet, 'rtc'), "Time packet should have RTC"
            assert time_packet.rtc >= 0, "RTC should be non-negative"
            
            # Verify CSDW field values
            assert time_packet.time_format == 0, "Time format should be 0 (IRIG-B)"
            assert time_packet.time_source == 1, "Time source should be 1 (External)"
            assert time_packet.leap == 0, "Leap year flag should be set (0 or 1)"
            
        finally:
            if filepath.exists():
                filepath.unlink()
    
    def test_validation_passes_correctly(self, simple_icd, simple_scenario, simple_flight_profile):
        """Test that validation passes for the right reasons."""
        with tempfile.NamedTemporaryFile(suffix='.ch10', delete=False) as tmp:
            filepath = Path(tmp.name)
        
        try:
            # Generate CH10 file
            writer = Ch10Writer()
            schedule = writer._build_test_schedule(simple_icd, duration_s=2.0)
            
            writer.write_file(
                filepath=filepath,
                schedule=schedule,
                flight_profile=simple_flight_profile,
                icd=simple_icd,
                start_time=datetime.utcnow(),
                scenario_name="Validation Test"
            )
            
            # Run validation
            results = validate_file(filepath, verbose=False)
            
            # Verify validation passes
            assert 'errors' in results, "Validation results should contain errors field"
            assert len(results['errors']) == 0, f"Validation should pass without errors: {results['errors']}"
            
            # Verify time packets are counted correctly
            assert results['time_packets'] > 0, "Should detect time packets"
            assert results['time_packets'] >= 2, "Should detect at least 2 time packets for 2s duration"
            
            # Verify no critical warnings about missing CSDW fields
            warnings = results.get('warnings', [])
            critical_warnings = [w for w in warnings if any(x in w.lower() for x in ['missing', 'time_format', 'time_source'])]
            assert len(critical_warnings) == 0, f"Should have no critical CSDW warnings: {critical_warnings}"
            
        finally:
            if filepath.exists():
                filepath.unlink()
    
    def test_first_dynamic_packet_is_time(self, simple_icd, simple_scenario, simple_flight_profile):
        """Test that the first dynamic packet after TMATS is a time packet."""
        with tempfile.NamedTemporaryFile(suffix='.ch10', delete=False) as tmp:
            filepath = Path(tmp.name)
        
        try:
            # Generate CH10 file
            writer = Ch10Writer()
            schedule = writer._build_test_schedule(simple_icd, duration_s=1.0)
            
            writer.write_file(
                filepath=filepath,
                schedule=schedule,
                flight_profile=simple_flight_profile,
                icd=simple_icd,
                start_time=datetime.utcnow(),
                scenario_name="First Dynamic Test"
            )
            
            # Check packet order
            c10 = C10(str(filepath))
            packets = list(c10)
            
            # First packet should be TMATS
            assert packets[0].data_type == 0x01, "First packet should be TMATS (0x01)"
            
            # Second packet should be Time-F1
            assert packets[1].data_type == 0x11, "Second packet should be Time-F1 (0x11)"
            
        finally:
            if filepath.exists():
                filepath.unlink()


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
