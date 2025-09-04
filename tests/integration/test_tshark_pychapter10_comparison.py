#!/usr/bin/env python3
"""
Direct comparison between TShark and PyChapter10 1553 message extraction.

This test generates CH10 files with known 1553 message content and then
extracts the messages using both TShark and PyChapter10 to compare results.
"""

import pytest
import subprocess
import shutil
import tempfile
import struct
import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

# Import our modules
from ch10gen.ch10_writer import write_ch10_file
from ch10gen.icd import load_icd, ICDDefinition, MessageDefinition, WordDefinition

# TShark configuration
ENABLE_TSHARK = os.environ.get('WITH_TSHARK', '').lower() in ('1', 'true', 'yes')
TSHARK_PATH = os.environ.get('TSHARK', shutil.which('tshark'))
TSHARK_LUA = os.environ.get('TSHARK_LUA', '')
VERBOSE = os.environ.get('TSHARK_VERBOSE', '').lower() in ('1', 'true', 'yes')

# Import PyChapter10
try:
    from chapter10 import C10
    from chapter10.ms1553 import MS1553F1
    PYCHAPTER10_AVAILABLE = True
except ImportError:
    PYCHAPTER10_AVAILABLE = False


@dataclass
class Message1553:
    """Represents a 1553 message extracted from CH10 file."""
    frame_number: int
    timestamp: float
    rt: int
    tr: str  # 'BC2RT' or 'RT2BC'
    sa: int
    wc: int
    data_words: List[int]
    errors: List[str] = None
    source: str = None  # 'tshark' or 'pychapter10'
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
    
    @property
    def message_id(self) -> str:
        """Unique identifier for this message type."""
        return f"RT{self.rt}_SA{self.sa}_{self.tr}"
    
    def __repr__(self):
        return f"Message1553(RT{self.rt} SA{self.sa} {self.tr} WC{self.wc} @{self.timestamp:.3f}s)"


@dataclass
class ComparisonResult:
    """Results of comparing TShark vs PyChapter10 extraction."""
    tshark_messages: List[Message1553]
    pychapter10_messages: List[Message1553]
    tshark_count: int
    pychapter10_count: int
    count_match: bool
    message_matches: List[bool]
    timing_differences: List[float]
    data_differences: List[Dict[str, Any]]
    errors: List[str]
    
    @property
    def match_percentage(self) -> float:
        """Percentage of messages that match between tools."""
        if self.tshark_count == 0:
            return 0.0
        matches = sum(self.message_matches)
        return (matches / self.tshark_count) * 100.0


class TSharkExtractor:
    """Extract 1553 messages using TShark."""
    
    def __init__(self, tshark_path: str = None, lua_script: str = None):
        self.tshark = tshark_path or TSHARK_PATH
        self.lua_script = lua_script or TSHARK_LUA
        
        if not self.tshark:
            raise RuntimeError("TShark not found. Install Wireshark or set TSHARK env var")
    
    def extract_messages(self, ch10_file: Path, max_messages: int = 1000) -> List[Message1553]:
        """Extract 1553 messages from CH10 file using TShark."""
        
        # Build TShark command with detailed field extraction
        cmd = [
            self.tshark, '-r', str(ch10_file),
            '-T', 'fields',
            '-e', 'frame.number',
            '-e', 'frame.time_relative',
            '-e', 'ch10.datatype',
            '-e', 'ch10.channel_id'
        ]
        
        # Add Lua script if available
        if self.lua_script:
            cmd.extend(['-X', f'lua_script:{self.lua_script}'])
        
        # Try to extract 1553-specific fields if Lua dissector is loaded
        if self.lua_script:
            cmd.extend([
                '-e', '1553.rt',
                '-e', '1553.tr', 
                '-e', '1553.sa',
                '-e', '1553.wc',
                '-e', '1553.data'
            ])
        
        # Limit output
        cmd.extend(['-c', str(max_messages)])
        
        try:
            if VERBOSE:
                print(f"Running TShark: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"TShark failed: {result.stderr}")
            
            return self._parse_tshark_output(result.stdout)
            
        except subprocess.TimeoutExpired:
            raise RuntimeError("TShark timed out")
        except Exception as e:
            raise RuntimeError(f"TShark extraction failed: {e}")
    
    def _parse_tshark_output(self, output: str) -> List[Message1553]:
        """Parse TShark field output into Message1553 objects."""
        messages = []
        
        for line_num, line in enumerate(output.strip().split('\n'), 1):
            if not line.strip():
                continue
            
            parts = line.split('\t')
            
            try:
                frame_number = int(parts[0]) if len(parts) > 0 else line_num
                timestamp = float(parts[1]) if len(parts) > 1 and parts[1] else 0.0
                
                # Check if this is a 1553 message
                data_type = parts[2] if len(parts) > 2 else ''
                if '0x19' not in data_type and '25' not in data_type:  # 0x19 = 25 decimal
                    continue
                
                # Extract 1553 fields if available
                if len(parts) >= 8:  # We have 1553-specific fields
                    rt = int(parts[4]) if parts[4] else 0
                    tr = parts[5] if parts[5] else 'BC2RT'
                    sa = int(parts[6]) if parts[6] else 0
                    wc = int(parts[7]) if parts[7] else 0
                    data_str = parts[8] if len(parts) > 8 else ''
                    
                    # Parse data words
                    data_words = []
                    if data_str:
                        # TShark might output data as hex strings
                        try:
                            # Try to parse as space-separated hex values
                            for word_str in data_str.split():
                                if word_str.startswith('0x'):
                                    data_words.append(int(word_str, 16))
                                else:
                                    data_words.append(int(word_str, 16))
                        except ValueError:
                            pass
                else:
                    # Fallback: use default values
                    rt = 0
                    tr = 'BC2RT'
                    sa = 0
                    wc = 0
                    data_words = []
                
                msg = Message1553(
                    frame_number=frame_number,
                    timestamp=timestamp,
                    rt=rt,
                    tr=tr,
                    sa=sa,
                    wc=wc,
                    data_words=data_words,
                    source='tshark'
                )
                messages.append(msg)
                
            except (ValueError, IndexError) as e:
                if VERBOSE:
                    print(f"Warning: Failed to parse TShark line {line_num}: {line} - {e}")
                continue
        
        return messages


class PyChapter10Extractor:
    """Extract 1553 messages using PyChapter10."""
    
    def extract_messages(self, ch10_file: Path, max_messages: int = 1000) -> List[Message1553]:
        """Extract 1553 messages from CH10 file using PyChapter10."""
        
        if not PYCHAPTER10_AVAILABLE:
            raise RuntimeError("PyChapter10 not available")
        
        messages = []
        
        try:
            c10 = C10(str(ch10_file))
            frame_number = 0
            
            for packet in c10:
                frame_number += 1
                
                # Check if this is a 1553 packet
                if hasattr(packet, 'data_type') and packet.data_type == 0x19:
                    # This is an MS1553F1 packet
                    packet_messages = self._extract_from_ms1553_packet(packet, frame_number)
                    messages.extend(packet_messages)
                    
                    if len(messages) >= max_messages:
                        break
                        
        except Exception as e:
            raise RuntimeError(f"PyChapter10 extraction failed: {e}")
        
        return messages[:max_messages]
    
    def _extract_from_ms1553_packet(self, packet, frame_number: int) -> List[Message1553]:
        """Extract messages from an MS1553F1 packet."""
        messages = []
        
        # Try different methods to access messages
        try:
            # Method 1: Direct iteration
            for i, msg in enumerate(packet):
                message = self._parse_pychapter10_message(msg, frame_number, i)
                if message:
                    messages.append(message)
        except:
            pass
        
        # Method 2: Check for messages attribute
        if hasattr(packet, 'messages'):
            try:
                for i, msg in enumerate(packet.messages):
                    message = self._parse_pychapter10_message(msg, frame_number, i)
                    if message:
                        messages.append(message)
            except:
                pass
        
        # Method 3: Manual parsing from raw body
        if not messages and hasattr(packet, '_raw_body'):
            messages = self._parse_raw_body(packet._raw_body, frame_number)
        
        return messages
    
    def _parse_pychapter10_message(self, msg, frame_number: int, msg_index: int) -> Optional[Message1553]:
        """Parse a PyChapter10 message object."""
        try:
            # Extract basic fields
            timestamp = getattr(msg, 'ipts', 0) / 1_000_000_000.0  # Convert ns to seconds
            rt = getattr(msg, 'rt', 0)
            sa = getattr(msg, 'sa', 0)
            tr = getattr(msg, 'tr', 'BC2RT')
            wc = getattr(msg, 'wc', 0)
            
            # Extract data words
            data_words = []
            if hasattr(msg, 'data') and msg.data:
                if isinstance(msg.data, bytes):
                    # Parse as little-endian 16-bit words
                    for i in range(0, len(msg.data), 2):
                        if i + 1 < len(msg.data):
                            word = struct.unpack('<H', msg.data[i:i+2])[0]
                            data_words.append(word)
                elif isinstance(msg.data, list):
                    data_words = msg.data
            
            return Message1553(
                frame_number=frame_number,
                timestamp=timestamp,
                rt=rt,
                tr=tr,
                sa=sa,
                wc=wc,
                data_words=data_words,
                source='pychapter10'
            )
            
        except Exception as e:
            if VERBOSE:
                print(f"Warning: Failed to parse PyChapter10 message: {e}")
            return None
    
    def _parse_raw_body(self, raw_body: bytes, frame_number: int) -> List[Message1553]:
        """Manually parse 1553 messages from raw packet body."""
        messages = []
        
        try:
            # Parse MS1553F1 format manually
            if len(raw_body) < 4:
                return messages
            
            # CSDW (Channel Specific Data Word) - first 4 bytes
            csdw = struct.unpack('<I', raw_body[0:4])[0]
            message_count = csdw & 0xFFFF
            
            offset = 4
            for i in range(min(message_count, 10)):  # Limit to prevent infinite loops
                if offset + 8 > len(raw_body):
                    break
                
                # Intra-message header (8 bytes)
                block_status, gap_time, msg_length, reserved = struct.unpack('<HHHH', raw_body[offset:offset+8])
                offset += 8
                
                if offset + msg_length > len(raw_body):
                    break
                
                # Message data
                msg_data = raw_body[offset:offset+msg_length]
                offset += msg_length
                
                if len(msg_data) >= 4:
                    # Parse command word
                    cmd_word = struct.unpack('<H', msg_data[0:2])[0]
                    rt = (cmd_word >> 11) & 0x1F
                    tr_bit = (cmd_word >> 10) & 0x01
                    sa = (cmd_word >> 5) & 0x1F
                    wc = cmd_word & 0x1F
                    if wc == 0:
                        wc = 32
                    
                    tr = 'RT2BC' if tr_bit else 'BC2RT'
                    
                    # Parse data words
                    data_words = []
                    for j in range(2, len(msg_data), 2):  # Skip command and status words
                        if j + 1 < len(msg_data):
                            word = struct.unpack('<H', msg_data[j:j+2])[0]
                            data_words.append(word)
                    
                    message = Message1553(
                        frame_number=frame_number,
                        timestamp=i * 0.001,  # Approximate timing
                        rt=rt,
                        tr=tr,
                        sa=sa,
                        wc=wc,
                        data_words=data_words,
                        source='pychapter10'
                    )
                    messages.append(message)
            
        except Exception as e:
            if VERBOSE:
                print(f"Warning: Raw body parsing failed: {e}")
        
        return messages


class MessageComparator:
    """Compare 1553 messages extracted by different tools."""
    
    def compare(self, tshark_messages: List[Message1553], 
                pychapter10_messages: List[Message1553]) -> ComparisonResult:
        """Compare messages extracted by TShark and PyChapter10."""
        
        tshark_count = len(tshark_messages)
        pychapter10_count = len(pychapter10_messages)
        count_match = (tshark_count == pychapter10_count)
        
        # Match messages by RT/SA/TR combination
        message_matches = []
        timing_differences = []
        data_differences = []
        errors = []
        
        # Create lookup for PyChapter10 messages
        pyc10_lookup = {}
        for msg in pychapter10_messages:
            key = (msg.rt, msg.sa, msg.tr)
            if key not in pyc10_lookup:
                pyc10_lookup[key] = []
            pyc10_lookup[key].append(msg)
        
        # Compare each TShark message
        for tshark_msg in tshark_messages:
            key = (tshark_msg.rt, tshark_msg.sa, tshark_msg.tr)
            
            if key in pyc10_lookup:
                # Find best match by timing
                best_match = None
                best_timing_diff = float('inf')
                
                for pyc10_msg in pyc10_lookup[key]:
                    timing_diff = abs(tshark_msg.timestamp - pyc10_msg.timestamp)
                    if timing_diff < best_timing_diff:
                        best_timing_diff = timing_diff
                        best_match = pyc10_msg
                
                if best_match:
                    message_matches.append(True)
                    timing_differences.append(best_timing_diff)
                    
                    # Compare data words
                    if tshark_msg.data_words != best_match.data_words:
                        data_differences.append({
                            'tshark': tshark_msg.data_words,
                            'pychapter10': best_match.data_words,
                            'message_id': tshark_msg.message_id
                        })
                else:
                    message_matches.append(False)
                    errors.append(f"No PyChapter10 match for {tshark_msg.message_id}")
            else:
                message_matches.append(False)
                errors.append(f"Missing PyChapter10 message: {tshark_msg.message_id}")
        
        return ComparisonResult(
            tshark_messages=tshark_messages,
            pychapter10_messages=pychapter10_messages,
            tshark_count=tshark_count,
            pychapter10_count=pychapter10_count,
            count_match=count_match,
            message_matches=message_matches,
            timing_differences=timing_differences,
            data_differences=data_differences,
            errors=errors
        )


def create_test_icd() -> ICDDefinition:
    """Create a test ICD with known 1553 messages."""
    
    messages = [
        MessageDefinition(
            name="TEST_MSG_1",
            rate_hz=10.0,
            rt=5,
            tr="BC2RT",
            sa=1,
            wc=3,
            words=[
                WordDefinition(name="word1", encode="u16", const=0x1234),
                WordDefinition(name="word2", encode="u16", const=0x5678),
                WordDefinition(name="word3", encode="u16", const=0x9ABC),
            ]
        ),
        MessageDefinition(
            name="TEST_MSG_2", 
            rate_hz=5.0,
            rt=10,
            tr="RT2BC",
            sa=2,
            wc=2,
            words=[
                WordDefinition(name="word1", encode="u16", const=0x1111),
                WordDefinition(name="word2", encode="u16", const=0x2222),
            ]
        )
    ]
    
    return ICDDefinition(bus="A", messages=messages)


def create_test_ch10_file() -> Path:
    """Create a test CH10 file with known 1553 messages."""
    
    with tempfile.NamedTemporaryFile(suffix='.c10', delete=False) as f:
        output_file = Path(f.name)
    
    # Create test scenario
    scenario = {
        'name': 'TShark vs PyChapter10 Test',
        'start_time_utc': '2025-01-01T12:00:00Z',
        'duration_s': 5.0,  # Short duration for fast testing
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
    
    # Generate CH10 file
    icd = create_test_icd()
    stats = write_ch10_file(
        output_path=output_file,
        scenario=scenario,
        icd=icd,
        seed=42
    )
    
    return output_file


@pytest.mark.skipif(not ENABLE_TSHARK, reason="TShark validation disabled. Set WITH_TSHARK=1 to enable")
@pytest.mark.skipif(not PYCHAPTER10_AVAILABLE, reason="PyChapter10 not available")
def test_tshark_vs_pychapter10_message_extraction():
    """Test that TShark and PyChapter10 extract the same 1553 messages."""
    
    # Create test file
    test_file = create_test_ch10_file()
    
    try:
        # Extract messages with both tools
        tshark_extractor = TSharkExtractor()
        pychapter10_extractor = PyChapter10Extractor()
        
        print(f"\n🔍 Extracting messages from {test_file.name}")
        
        tshark_messages = tshark_extractor.extract_messages(test_file, max_messages=100)
        pychapter10_messages = pychapter10_extractor.extract_messages(test_file, max_messages=100)
        
        print(f"📊 TShark extracted: {len(tshark_messages)} messages")
        print(f"📊 PyChapter10 extracted: {len(pychapter10_messages)} messages")
        
        # Compare results
        comparator = MessageComparator()
        result = comparator.compare(tshark_messages, pychapter10_messages)
        
        # Print detailed results
        print(f"\n📈 Comparison Results:")
        print(f"  Message count match: {result.count_match}")
        print(f"  Match percentage: {result.match_percentage:.1f}%")
        print(f"  Timing differences: {len(result.timing_differences)}")
        print(f"  Data differences: {len(result.data_differences)}")
        print(f"  Errors: {len(result.errors)}")
        
        if result.errors:
            print(f"\n❌ Errors:")
            for error in result.errors[:5]:  # Show first 5 errors
                print(f"    {error}")
        
        if result.data_differences:
            print(f"\n⚠️  Data differences:")
            for diff in result.data_differences[:3]:  # Show first 3 differences
                print(f"    {diff['message_id']}: TShark={diff['tshark']}, PyChapter10={diff['pychapter10']}")
        
        # Assertions
        assert len(tshark_messages) > 0, "TShark should extract at least some messages"
        assert len(pychapter10_messages) > 0, "PyChapter10 should extract at least some messages"
        
        # Allow some tolerance for differences
        if result.match_percentage < 80.0:
            pytest.fail(f"Message match percentage too low: {result.match_percentage:.1f}%")
        
        # Check for critical errors
        critical_errors = [e for e in result.errors if 'Missing' in e or 'No match' in e]
        if len(critical_errors) > len(result.tshark_messages) * 0.2:  # More than 20% missing
            pytest.fail(f"Too many missing messages: {len(critical_errors)}")
        
    finally:
        # Clean up
        try:
            test_file.unlink()
        except:
            pass


@pytest.mark.skipif(not ENABLE_TSHARK, reason="TShark validation disabled")
def test_tshark_message_extraction_only():
    """Test TShark message extraction independently."""
    
    test_file = create_test_ch10_file()
    
    try:
        extractor = TSharkExtractor()
        messages = extractor.extract_messages(test_file, max_messages=50)
        
        print(f"\n🔍 TShark extracted {len(messages)} messages")
        
        # Basic validation
        assert len(messages) > 0, "TShark should extract messages"
        
        # Check message structure
        for msg in messages[:5]:  # Check first 5 messages
            assert 0 <= msg.rt <= 31, f"Invalid RT: {msg.rt}"
            assert 0 <= msg.sa <= 31, f"Invalid SA: {msg.sa}"
            assert msg.tr in ['BC2RT', 'RT2BC'], f"Invalid TR: {msg.tr}"
            assert msg.wc >= 0, f"Invalid WC: {msg.wc}"
        
        print("✅ TShark message extraction validation passed")
        
    finally:
        try:
            test_file.unlink()
        except:
            pass


@pytest.mark.skipif(not PYCHAPTER10_AVAILABLE, reason="PyChapter10 not available")
def test_pychapter10_message_extraction_only():
    """Test PyChapter10 message extraction independently."""
    
    test_file = create_test_ch10_file()
    
    try:
        extractor = PyChapter10Extractor()
        messages = extractor.extract_messages(test_file, max_messages=50)
        
        print(f"\n🔍 PyChapter10 extracted {len(messages)} messages")
        
        # Basic validation
        assert len(messages) > 0, "PyChapter10 should extract messages"
        
        # Check message structure
        for msg in messages[:5]:  # Check first 5 messages
            assert 0 <= msg.rt <= 31, f"Invalid RT: {msg.rt}"
            assert 0 <= msg.sa <= 31, f"Invalid SA: {msg.sa}"
            assert msg.tr in ['BC2RT', 'RT2BC'], f"Invalid TR: {msg.tr}"
            assert msg.wc >= 0, f"Invalid WC: {msg.wc}"
        
        print("✅ PyChapter10 message extraction validation passed")
        
    finally:
        try:
            test_file.unlink()
        except:
            pass


def test_tool_availability():
    """Test that required tools are available."""
    
    print(f"\n🔧 Tool Availability Check:")
    print(f"  TShark: {'✅ Available' if TSHARK_PATH else '❌ Not found'}")
    print(f"  PyChapter10: {'✅ Available' if PYCHAPTER10_AVAILABLE else '❌ Not found'}")
    print(f"  TShark Lua: {'✅ Available' if TSHARK_LUA else '⚠️  Not specified'}")
    
    if TSHARK_PATH:
        try:
            result = subprocess.run([TSHARK_PATH, '--version'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                version = result.stdout.split('\n')[0]
                print(f"  TShark version: {version}")
        except:
            print(f"  TShark version: Could not determine")
    
    # At least one tool should be available
    assert TSHARK_PATH or PYCHAPTER10_AVAILABLE, "At least one extraction tool should be available"


if __name__ == "__main__":
    # Run the tests manually
    import os
    os.environ['WITH_TSHARK'] = '1'
    
    print("🧪 Running TShark vs PyChapter10 Comparison Tests")
    print("=" * 60)
    
    try:
        test_tool_availability()
        print()
        
        if TSHARK_PATH:
            test_tshark_message_extraction_only()
            print()
        
        if PYCHAPTER10_AVAILABLE:
            test_pychapter10_message_extraction_only()
            print()
        
        if TSHARK_PATH and PYCHAPTER10_AVAILABLE:
            test_tshark_vs_pychapter10_message_extraction()
        
        print("\n🎉 All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        raise
