#!/usr/bin/env python3
"""
TShark-based validation test suite for CH10 files.

This is the PRIMARY validation mechanism - using Wireshark's tshark CLI
as an independent decoder to verify our CH10 outputs are correct.
"""

import os
import sys
import json
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import pytest

# Check if tshark testing is enabled
ENABLE_TSHARK = os.environ.get('WITH_TSHARK', '').lower() in ('1', 'true', 'yes')
TSHARK_PATH = os.environ.get('TSHARK', shutil.which('tshark'))
TSHARK_LUA = os.environ.get('TSHARK_LUA', '')

# Skip all tests if tshark not enabled
pytestmark = pytest.mark.skipif(
    not ENABLE_TSHARK,
    reason="TShark validation disabled. Set WITH_TSHARK=1 to enable"
)

@dataclass
class TSharkResult:
    """Parsed tshark output."""
    success: bool
    command: str
    stdout: str
    stderr: str
    messages: List[Dict[str, Any]]
    error: Optional[str] = None

class TSharkValidator:
    """Validates CH10 files using tshark as independent decoder."""
    
    def __init__(self):
        self.tshark = TSHARK_PATH
        self.lua_script = TSHARK_LUA
        
        if not self.tshark:
            pytest.skip("tshark not found in PATH")
        
        if self.lua_script and not Path(self.lua_script).exists():
            pytest.skip(f"CH10 Lua dissector not found: {self.lua_script}")
    
    def run_tshark(self, ch10_file: Path, args: List[str]) -> TSharkResult:
        """Run tshark and return parsed results."""
        cmd = [self.tshark, '-r', str(ch10_file)]
        
        if self.lua_script:
            cmd.extend(['-X', f'lua_script:{self.lua_script}'])
        
        cmd.extend(args)
        
        # Log the command for debugging
        cmd_str = ' '.join(cmd)
        print(f"Running: {cmd_str}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return TSharkResult(
                success=result.returncode == 0,
                command=cmd_str,
                stdout=result.stdout,
                stderr=result.stderr,
                messages=self._parse_output(result.stdout),
                error=result.stderr if result.returncode != 0 else None
            )
        except subprocess.TimeoutExpired:
            return TSharkResult(
                success=False,
                command=cmd_str,
                stdout='',
                stderr='Timeout',
                messages=[],
                error='TShark command timed out after 30 seconds'
            )
        except Exception as e:
            return TSharkResult(
                success=False,
                command=cmd_str,
                stdout='',
                stderr=str(e),
                messages=[],
                error=f'Failed to run tshark: {e}'
            )
    
    def _parse_output(self, output: str) -> List[Dict[str, Any]]:
        """Parse tshark output into structured data."""
        messages = []
        for line in output.strip().split('\n'):
            if not line:
                continue
            # Parse based on output format
            # This will depend on the specific tshark options used
            messages.append({'raw': line})
        return messages
    
    def validate_1553_messages(self, ch10_file: Path) -> Dict[str, Any]:
        """Extract and validate 1553 messages from CH10 file."""
        # Use tshark to extract 1553 message fields
        result = self.run_tshark(ch10_file, [
            '-Y', '1553',
            '-T', 'fields',
            '-e', 'frame.number',
            '-e', 'ch10.datatype', 
            '-e', '1553.rt',
            '-e', '1553.tr',
            '-e', '1553.sa',
            '-e', '1553.wc',
            '-e', '1553.data'
        ])
        
        if not result.success:
            pytest.fail(f"TShark failed: {result.error}")
        
        # Parse the tab-separated output
        messages = []
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            
            fields = line.split('\t')
            if len(fields) >= 6:
                messages.append({
                    'frame': fields[0],
                    'datatype': fields[1] if len(fields) > 1 else '',
                    'rt': int(fields[2]) if len(fields) > 2 and fields[2] else None,
                    'tr': fields[3] if len(fields) > 3 else '',
                    'sa': int(fields[4]) if len(fields) > 4 and fields[4] else None,
                    'wc': int(fields[5]) if len(fields) > 5 and fields[5] else None,
                    'data': fields[6] if len(fields) > 6 else ''
                })
        
        return {
            'message_count': len(messages),
            'messages': messages,
            'unique_rts': set(m['rt'] for m in messages if m['rt'] is not None),
            'unique_sas': set(m['sa'] for m in messages if m['sa'] is not None)
        }

# Test fixtures
@pytest.fixture
def validator():
    """Create a TSharkValidator instance."""
    return TSharkValidator()

@pytest.fixture
def sample_ch10_file(tmp_path):
    """Generate a sample CH10 file for testing."""
    from ch10gen.cli import build_ch10_file
    
    # Create minimal test scenario
    scenario = tmp_path / "test_scenario.yaml"
    scenario.write_text("""
scenario:
  name: "Test"
  duration_s: 1.0
flight_profile:
  segments:
    - type: "level"
      duration_s: 1.0
      altitude_ft: 10000
      airspeed_kts: 250
""")
    
    # Create minimal ICD
    icd = tmp_path / "test_icd.yaml"
    icd.write_text("""
bus: "A"
messages:
  - name: "TEST_MSG"
    rate_hz: 10
    rt: 5
    tr: "RT2BC"
    sa: 1
    wc: 2
    words:
      - name: "data1"
        encode: "u16"
        const: 0x1234
      - name: "data2"
        encode: "u16"
        const: 0x5678
""")
    
    # Generate CH10 file
    output = tmp_path / "test.ch10"
    build_ch10_file(scenario, icd, output, duration=1.0)
    
    return output

# Primary validation tests
class TestTSharkValidation:
    """Primary CH10 validation using tshark."""
    
    def test_ch10_file_readable(self, validator, sample_ch10_file):
        """Verify tshark can read our CH10 files."""
        result = validator.run_tshark(sample_ch10_file, ['-c', '10'])
        assert result.success, f"TShark failed to read CH10 file: {result.error}"
    
    def test_1553_message_count(self, validator, sample_ch10_file):
        """Verify correct number of 1553 messages."""
        data = validator.validate_1553_messages(sample_ch10_file)
        
        # We expect ~10 messages (10 Hz for 1 second)
        assert 8 <= data['message_count'] <= 12, \
            f"Expected ~10 messages, got {data['message_count']}"
    
    def test_1553_rt_sa_values(self, validator, sample_ch10_file):
        """Verify RT/SA values match our configuration."""
        data = validator.validate_1553_messages(sample_ch10_file)
        
        # Check expected RT
        assert 5 in data['unique_rts'], \
            f"Expected RT 5, got RTs: {data['unique_rts']}"
        
        # Check expected SA
        assert 1 in data['unique_sas'], \
            f"Expected SA 1, got SAs: {data['unique_sas']}"
    
    def test_1553_word_count(self, validator, sample_ch10_file):
        """Verify word counts are correct."""
        data = validator.validate_1553_messages(sample_ch10_file)
        
        for msg in data['messages']:
            if msg['wc'] is not None:
                assert msg['wc'] == 2, \
                    f"Expected WC=2, got {msg['wc']} in message {msg}"

# Secondary tests (supporting validation)
class TestBitfieldSupport:
    """Test bitfield packing (secondary to tshark validation)."""
    
    def test_bitfield_encode_decode(self):
        """Quick test of bitfield logic."""
        from ch10gen.core.encode1553 import encode_bitfield, decode_bitfield
        
        value = 42
        mask = 0x3F  # 6 bits
        shift = 4
        
        encoded = encode_bitfield(value, mask, shift)
        decoded = decode_bitfield(encoded, mask, shift)
        
        assert decoded == value

class TestBNR16Support:
    """Test BNR16 encoding (secondary to tshark validation)."""
    
    def test_bnr16_round_trip(self):
        """Quick test of BNR16 encoding."""
        from ch10gen.core.encode1553 import bnr16
        
        # Test various values
        test_values = [0, 180, -180, 359.9, -0.1]
        
        for value in test_values:
            encoded = bnr16(value, scale=0.1)
            # Just verify it produces a valid 16-bit word
            assert 0 <= encoded <= 0xFFFF

if __name__ == "__main__":
    # Run with: WITH_TSHARK=1 pytest tests/test_tshark_validation.py -v
    pytest.main([__file__, '-v'])
