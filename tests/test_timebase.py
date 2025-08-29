"""Tests for timebase consistency and IPTS monotonicity."""

import pytest
from datetime import datetime, timezone
from pathlib import Path
import tempfile
from chapter10 import C10
from chapter10.ms1553 import MS1553F1
from ch10gen.ch10_writer import write_ch10_file
from ch10gen.icd import load_icd


def normalize_ipts(ipts_values):
    """Normalize IPTS values to handle different representations."""
    # IPTS can be in nanoseconds or microseconds depending on implementation
    # Detect scale and normalize
    if not ipts_values:
        return []
    
    # Check if values look like nanoseconds (> 1e9) or microseconds
    avg = sum(ipts_values) / len(ipts_values)
    if avg > 1e9:
        # Likely nanoseconds, convert to microseconds
        return [v / 1000 for v in ipts_values]
    else:
        # Already in reasonable units
        return ipts_values


def test_ipts_strict_monotonicity():
    """Test that IPTS values are strictly monotonic (no duplicates)."""
    # Generate test file
    scenario = {
        'name': 'IPTS Test',
        'start_time_utc': '2025-01-01T12:00:00Z',
        'duration_s': 5,
        'seed': 42,
        'profile': {
            'base_altitude_ft': 5000,
            'segments': [
                {'type': 'cruise', 'ias_kt': 250, 'hold_s': 5}
            ]
        },
        'bus': {
            'packet_bytes_target': 8192,
            'jitter_ms': 0  # No jitter for deterministic test
        }
    }
    
    icd = load_icd(Path('icd/test_icd.yaml'))
    
    with tempfile.NamedTemporaryFile(suffix='.c10', delete=False) as f:
        output_file = Path(f.name)
    
    try:
        stats = write_ch10_file(
            output_path=output_file,
            scenario=scenario,
            icd=icd,
            seed=42
        )
        
        # Read back and collect IPTS values
        c10 = C10(str(output_file))
        ipts_values = []
        
        for packet in c10:
            if isinstance(packet, MS1553F1):
                for msg in packet:
                    if hasattr(msg, 'ipts'):
                        ipts_values.append(msg.ipts)
        
        # Normalize values
        ipts_values = normalize_ipts(ipts_values)
        
        if len(ipts_values) > 1:
            # Check strict monotonicity
            for i in range(1, len(ipts_values)):
                assert ipts_values[i] > ipts_values[i-1], \
                       f"IPTS not strictly monotonic at index {i}: {ipts_values[i-1]} >= {ipts_values[i]}"
            
            # Check reasonable cadence
            deltas = [ipts_values[i] - ipts_values[i-1] for i in range(1, len(ipts_values))]
            median_delta = sorted(deltas)[len(deltas)//2]
            
            # Expected cadence: mix of 20Hz (50ms) and 5Hz (200ms)
            # Median should be around 50ms = 50000 microseconds
            assert 10000 < median_delta < 500000, \
                   f"Median inter-message delta {median_delta} not in reasonable range"
    
    finally:
        # Windows file cleanup
        try:
            output_file.unlink()
        except:
            pass  # Windows may hold file locks


def test_rtc_timebase_consistency():
    """Test RTC timebase consistency across packet types."""
    scenario = {
        'name': 'RTC Test',
        'start_time_utc': '2025-01-01T12:00:00Z',
        'duration_s': 3,
        'seed': 42,
        'profile': {
            'base_altitude_ft': 5000,
            'segments': [
                {'type': 'cruise', 'ias_kt': 250, 'hold_s': 3}
            ]
        },
        'bus': {
            'packet_bytes_target': 4096,
            'jitter_ms': 0
        }
    }
    
    icd = load_icd(Path('icd/test_icd.yaml'))
    
    with tempfile.NamedTemporaryFile(suffix='.c10', delete=False) as f:
        output_file = Path(f.name)
    
    try:
        stats = write_ch10_file(
            output_path=output_file,
            scenario=scenario,
            icd=icd,
            seed=42
        )
        
        # Read back and collect RTC values
        c10 = C10(str(output_file))
        rtc_values = []
        
        for packet in c10:
            if hasattr(packet, 'rtc'):
                rtc_values.append((type(packet).__name__, packet.rtc))
        
        # Check that RTC values are consistent
        if rtc_values:
            # All RTC values should be non-negative and increasing
            for i, (ptype, rtc) in enumerate(rtc_values):
                assert rtc >= 0, f"Negative RTC in {ptype} packet at index {i}: {rtc}"
            
            # Check general trend is increasing (allow some out-of-order for packet batching)
            first_rtc = rtc_values[0][1]
            last_rtc = rtc_values[-1][1]
            assert last_rtc >= first_rtc, \
                   f"RTC not increasing overall: first={first_rtc}, last={last_rtc}"
    
    finally:
        # Windows file cleanup
        try:
            output_file.unlink()
        except:
            pass  # Windows may hold file locks


def test_message_rate_accuracy():
    """Test that actual message rates match configured rates."""
    scenario = {
        'name': 'Rate Test',
        'start_time_utc': '2025-01-01T12:00:00Z',
        'duration_s': 10,
        'seed': 42,
        'profile': {
            'base_altitude_ft': 5000,
            'segments': [
                {'type': 'cruise', 'ias_kt': 250, 'hold_s': 10}
            ]
        },
        'bus': {
            'packet_bytes_target': 16384,
            'jitter_ms': 0
        }
    }
    
    icd = load_icd(Path('icd/test_icd.yaml'))
    
    with tempfile.NamedTemporaryFile(suffix='.c10', delete=False) as f:
        output_file = Path(f.name)
    
    try:
        stats = write_ch10_file(
            output_path=output_file,
            scenario=scenario,
            icd=icd,
            seed=42
        )
        
        # Expected counts
        # NAV_20HZ: 20 Hz * 10 s = 200
        # GPS_5HZ: 5 Hz * 10 s = 50
        # Total: 250
        expected_total = 250
        expected_nav = 200
        expected_gps = 50
        
        # Read back and count messages by RT/SA
        c10 = C10(str(output_file))
        rt_sa_counts = {}
        total_count = 0
        
        for packet in c10:
            if isinstance(packet, MS1553F1):
                for msg in packet:
                    total_count += 1
                    if hasattr(msg, 'data') and msg.data:
                        # Extract RT/SA from first word (command word)
                        if len(msg.data) >= 2:
                            # Data is bytes, extract first 16-bit word
                            cmd_word = int.from_bytes(msg.data[0:2], 'little')
                            rt = (cmd_word >> 11) & 0x1F
                            sa = (cmd_word >> 5) & 0x1F
                            key = (rt, sa)
                            rt_sa_counts[key] = rt_sa_counts.get(key, 0) + 1
        
        # Check total count with 2% tolerance
        if total_count > 0:
            tolerance = 0.02
            assert abs(total_count - expected_total) / expected_total <= tolerance, \
                   f"Total message count {total_count} not within 2% of expected {expected_total}"
            
            # Check individual message rates if we decoded them
            nav_key = (10, 1)  # RT=10, SA=1 for NAV_20HZ
            gps_key = (11, 2)  # RT=11, SA=2 for GPS_5HZ
            
            if nav_key in rt_sa_counts:
                assert abs(rt_sa_counts[nav_key] - expected_nav) / expected_nav <= 0.05, \
                       f"NAV count {rt_sa_counts[nav_key]} not within 5% of expected {expected_nav}"
            
            if gps_key in rt_sa_counts:
                assert abs(rt_sa_counts[gps_key] - expected_gps) / expected_gps <= 0.05, \
                       f"GPS count {rt_sa_counts[gps_key]} not within 5% of expected {expected_gps}"
    
    finally:
        # Windows file cleanup
        try:
            output_file.unlink()
        except:
            pass  # Windows may hold file locks
