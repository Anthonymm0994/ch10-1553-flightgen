"""Independent reader validation using c10-tools if available."""

import pytest
import subprocess
import shutil
import tempfile
from pathlib import Path
from ch10gen.ch10_writer import write_ch10_file
from ch10gen.icd import load_icd


@pytest.mark.optional
def test_c10_dump_validation():
    """Validate generated CH10 file with c10-dump if available."""
    # Check if c10-dump is available
    if not shutil.which('c10-dump'):
        pytest.skip("c10-dump not found in PATH (install c10-tools)")
    
    # Generate a test file
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Use test fixtures
        scenario = {
            'name': 'C10 Tools Test',
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
                'packet_bytes_target': 8192,
                'jitter_ms': 0
            }
        }
        
        icd = load_icd(Path('icd/test_icd.yaml'))
        output_file = tmpdir / 'test.c10'
        
        stats = write_ch10_file(
            output_path=output_file,
            scenario=scenario,
            icd=icd,
            seed=42
        )
        
        # Run c10-dump
        result = subprocess.run(
            ['c10-dump', str(output_file)],
            capture_output=True,
            text=True
        )
        
        # Check for success
        assert result.returncode == 0, f"c10-dump failed: {result.stderr}"
        
        output = result.stdout
        
        # Check for expected packet types
        assert '0x01' in output or 'TMATS' in output.upper(), "No TMATS packet found"
        assert '0x11' in output or 'TIME' in output.upper(), "No Time packets found"
        assert '0x19' in output or '1553' in output, "No 1553 packets found"
        
        # Extract message counts if available
        lines = output.split('\n')
        message_count = 0
        for line in lines:
            if '1553' in line and 'messages' in line.lower():
                # Try to extract count
                parts = line.split()
                for i, part in enumerate(parts):
                    if 'message' in part.lower() and i > 0:
                        try:
                            message_count = int(parts[i-1])
                            break
                        except:
                            pass
        
        # Expected: 20 Hz * 10s + 5 Hz * 10s = 250 messages
        expected = 250
        if message_count > 0:
            tolerance = 0.02  # 2% tolerance
            assert abs(message_count - expected) / expected <= tolerance, \
                   f"Message count {message_count} not within 2% of expected {expected}"


@pytest.mark.optional
def test_c10_errcount_validation():
    """Check for errors using c10-errcount if available."""
    # Check if c10-errcount is available
    if not shutil.which('c10-errcount'):
        pytest.skip("c10-errcount not found in PATH (install c10-tools)")
    
    # Generate a test file
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        scenario = {
            'name': 'Error Check Test',
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
                'jitter_ms': 0
            }
        }
        
        icd = load_icd(Path('icd/test_icd.yaml'))
        output_file = tmpdir / 'test.c10'
        
        stats = write_ch10_file(
            output_path=output_file,
            scenario=scenario,
            icd=icd,
            seed=42
        )
        
        # Run c10-errcount
        result = subprocess.run(
            ['c10-errcount', str(output_file)],
            capture_output=True,
            text=True
        )
        
        # Check for success
        assert result.returncode == 0, f"c10-errcount failed: {result.stderr}"
        
        output = result.stdout.lower()
        
        # Check for zero errors
        if 'error' in output and 'count' in output:
            # Try to extract error count
            if '0 error' in output or 'no error' in output or 'error count: 0' in output:
                pass  # Good
            else:
                # Check if there's a non-zero error count
                import re
                match = re.search(r'error.*?(\d+)', output)
                if match:
                    error_count = int(match.group(1))
                    assert error_count == 0, f"c10-errcount found {error_count} errors"


@pytest.mark.optional 
def test_irig106lib_validation():
    """Validate using irig106lib Python bindings if available."""
    try:
        import irig106
    except ImportError:
        pytest.skip("irig106 Python library not installed")
    
    # Generate test file
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        scenario = {
            'name': 'IRIG106 Lib Test',
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
                'jitter_ms': 0
            }
        }
        
        icd = load_icd(Path('icd/test_icd.yaml'))
        output_file = tmpdir / 'test.c10'
        
        stats = write_ch10_file(
            output_path=output_file,
            scenario=scenario,
            icd=icd,
            seed=42
        )
        
        # Open with irig106lib
        handle = irig106.open(str(output_file), irig106.FileMode.READ)
        
        packet_types = {}
        message_count = 0
        
        # Read all packets
        for packet in irig106.packet_headers(handle):
            data_type = packet.data_type
            packet_types[data_type] = packet_types.get(data_type, 0) + 1
            
            # Count 1553 messages
            if data_type == 0x19:  # 1553 F1
                # Read packet data
                data = irig106.read_data(handle, packet)
                # Parse 1553 messages (implementation specific)
                # message_count += ...
        
        irig106.close(handle)
        
        # Verify packet types
        assert 0x01 in packet_types, "No TMATS (0x01) packets"
        assert 0x11 in packet_types, "No Time (0x11) packets"  
        assert 0x19 in packet_types, "No 1553 (0x19) packets"
