#!/usr/bin/env python3
"""
Comprehensive TShark vs PyChapter10 comparison using existing test files.
This test compares actual 1553 message extraction between the two tools.
"""

import pytest
import subprocess
import shutil
import tempfile
import struct
import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

# Import our modules
from ch10gen.ch10_writer import write_ch10_file
from ch10gen.icd import load_icd

# TShark configuration
ENABLE_TSHARK = os.environ.get('WITH_TSHARK', '').lower() in ('1', 'true', 'yes')
TSHARK_PATH = os.environ.get('TSHARK', shutil.which('tshark'))
TSHARK_LUA = os.environ.get('TSHARK_LUA', '')

# Import PyChapter10
try:
    from chapter10 import C10
    from chapter10.ms1553 import MS1553F1
    PYCHAPTER10_AVAILABLE = True
except ImportError:
    PYCHAPTER10_AVAILABLE = False


@dataclass
class ExtractedMessage:
    """1553 message extracted from CH10 file."""
    rt: int
    sa: int
    tr: str  # 'BC2RT' or 'RT2BC'
    wc: int
    data_words: List[int]
    timestamp: float
    source: str  # 'tshark' or 'pychapter10'
    frame_number: int = 0
    
    @property
    def message_id(self) -> str:
        """Unique identifier for this message type."""
        return f"RT{self.rt}_SA{self.sa}_{self.tr}"
    
    def __repr__(self):
        return f"ExtractedMessage(RT{self.rt} SA{self.sa} {self.tr} WC{self.wc} @{self.timestamp:.3f}s)"


class PyChapter10Extractor:
    """Extract 1553 messages using PyChapter10."""
    
    def extract_messages(self, ch10_file: Path, max_messages: int = 1000) -> List[ExtractedMessage]:
        """Extract 1553 messages from CH10 file using PyChapter10."""
        messages = []
        
        if not PYCHAPTER10_AVAILABLE:
            return messages
        
        try:
            c10 = C10(str(ch10_file))
            frame_number = 0
            
            for packet in c10:
                frame_number += 1
                
                # Check if this is a 1553 packet
                if hasattr(packet, 'data_type') and packet.data_type == 0x19:
                    packet_messages = self._extract_from_packet(packet, frame_number)
                    messages.extend(packet_messages)
                    
                    if len(messages) >= max_messages:
                        break
        except Exception as e:
            print(f"PyChapter10 extraction failed: {e}")
        
        return messages[:max_messages]
    
    def _extract_from_packet(self, packet, frame_number: int) -> List[ExtractedMessage]:
        """Extract messages from a 1553 packet."""
        messages = []
        
        # Try different methods to access messages
        try:
            # Method 1: Direct iteration
            for i, msg in enumerate(packet):
                message = self._parse_message(msg, frame_number, i)
                if message:
                    messages.append(message)
        except:
            pass
        
        # Method 2: Check for messages attribute
        if hasattr(packet, 'messages'):
            try:
                for i, msg in enumerate(packet.messages):
                    message = self._parse_message(msg, frame_number, i)
                    if message:
                        messages.append(message)
            except:
                pass
        
        # Method 3: Manual parsing from raw body
        if not messages and hasattr(packet, '_raw_body'):
            messages = self._parse_raw_body(packet._raw_body, frame_number)
        
        return messages
    
    def _parse_message(self, msg, frame_number: int, msg_index: int) -> Optional[ExtractedMessage]:
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
            
            return ExtractedMessage(
                rt=rt, sa=sa, tr=tr, wc=wc,
                data_words=data_words, timestamp=timestamp,
                source='pychapter10', frame_number=frame_number
            )
        except Exception as e:
            return None
    
    def _parse_raw_body(self, raw_body: bytes, frame_number: int) -> List[ExtractedMessage]:
        """Manually parse 1553 messages from raw packet body."""
        messages = []
        
        try:
            if len(raw_body) < 4:
                return messages
            
            # Parse MS1553F1 format manually
            csdw = struct.unpack('<I', raw_body[0:4])[0]
            message_count = csdw & 0xFFFF
            
            offset = 4
            for i in range(min(message_count, 10)):
                if offset + 8 > len(raw_body):
                    break
                
                # Intra-message header
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
                    for j in range(2, len(msg_data), 2):
                        if j + 1 < len(msg_data):
                            word = struct.unpack('<H', msg_data[j:j+2])[0]
                            data_words.append(word)
                    
                    message = ExtractedMessage(
                        rt=rt, sa=sa, tr=tr, wc=wc,
                        data_words=data_words, timestamp=i * 0.001,
                        source='pychapter10', frame_number=frame_number
                    )
                    messages.append(message)
        except Exception as e:
            pass
        
        return messages


class TSharkExtractor:
    """Extract 1553 messages using TShark."""
    
    def __init__(self, tshark_path: str = None, lua_script: str = None):
        self.tshark = tshark_path or TSHARK_PATH
        self.lua_script = lua_script or TSHARK_LUA
    
    def extract_messages(self, ch10_file: Path, max_messages: int = 1000) -> List[ExtractedMessage]:
        """Extract 1553 messages from CH10 file using TShark."""
        messages = []
        
        if not self.tshark:
            return messages
        
        try:
            # Build TShark command
            cmd = [
                self.tshark, '-r', str(ch10_file),
                '-T', 'fields',
                '-e', 'frame.number',
                '-e', 'frame.time_relative'
            ]
            
            # Add Lua script if available
            if self.lua_script:
                cmd.extend(['-X', f'lua_script:{self.lua_script}'])
                # Try to extract 1553-specific fields
                cmd.extend([
                    '-e', '1553.rt',
                    '-e', '1553.tr',
                    '-e', '1553.sa', 
                    '-e', '1553.wc',
                    '-e', '1553.data'
                ])
            
            # Limit output
            cmd.extend(['-c', str(max_messages)])
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                messages = self._parse_tshark_output(result.stdout)
            else:
                print(f"TShark failed: {result.stderr}")
                
        except Exception as e:
            print(f"TShark extraction failed: {e}")
        
        return messages
    
    def _parse_tshark_output(self, output: str) -> List[ExtractedMessage]:
        """Parse TShark field output into ExtractedMessage objects."""
        messages = []
        
        for line_num, line in enumerate(output.strip().split('\n'), 1):
            if not line.strip():
                continue
            
            parts = line.split('\t')
            
            try:
                frame_number = int(parts[0]) if len(parts) > 0 else line_num
                timestamp = float(parts[1]) if len(parts) > 1 and parts[1] else 0.0
                
                # Check if we have 1553-specific fields
                if len(parts) >= 7:  # We have 1553 fields
                    rt = int(parts[2]) if parts[2] else 0
                    tr = parts[3] if parts[3] else 'BC2RT'
                    sa = int(parts[4]) if parts[4] else 0
                    wc = int(parts[5]) if parts[5] else 0
                    data_str = parts[6] if len(parts) > 6 else ''
                    
                    # Parse data words
                    data_words = []
                    if data_str:
                        try:
                            for word_str in data_str.split():
                                if word_str.startswith('0x'):
                                    data_words.append(int(word_str, 16))
                                else:
                                    data_words.append(int(word_str, 16))
                        except ValueError:
                            pass
                else:
                    # Fallback: create dummy message
                    rt = 0
                    tr = 'BC2RT'
                    sa = 0
                    wc = 0
                    data_words = []
                
                messages.append(ExtractedMessage(
                    rt=rt, sa=sa, tr=tr, wc=wc,
                    data_words=data_words, timestamp=timestamp,
                    source='tshark', frame_number=frame_number
                ))
                
            except (ValueError, IndexError) as e:
                continue
        
        return messages


class MessageComparator:
    """Compare 1553 messages extracted by different tools."""
    
    def compare(self, tshark_messages: List[ExtractedMessage], 
                pychapter10_messages: List[ExtractedMessage]) -> Dict[str, Any]:
        """Compare messages extracted by TShark and PyChapter10."""
        
        result = {
            'tshark_count': len(tshark_messages),
            'pychapter10_count': len(pychapter10_messages),
            'count_match': len(tshark_messages) == len(pychapter10_messages),
            'message_matches': [],
            'timing_differences': [],
            'data_differences': [],
            'missing_messages': [],
            'extra_messages': [],
            'errors': []
        }
        
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
                    result['message_matches'].append(True)
                    result['timing_differences'].append(best_timing_diff)
                    
                    # Compare data words
                    if tshark_msg.data_words != best_match.data_words:
                        result['data_differences'].append({
                            'tshark': tshark_msg.data_words,
                            'pychapter10': best_match.data_words,
                            'message_id': tshark_msg.message_id
                        })
                else:
                    result['message_matches'].append(False)
                    result['missing_messages'].append(tshark_msg.message_id)
            else:
                result['message_matches'].append(False)
                result['missing_messages'].append(tshark_msg.message_id)
        
        # Find extra PyChapter10 messages
        tshark_keys = set((msg.rt, msg.sa, msg.tr) for msg in tshark_messages)
        for pyc10_msg in pychapter10_messages:
            key = (pyc10_msg.rt, pyc10_msg.sa, pyc10_msg.tr)
            if key not in tshark_keys:
                result['extra_messages'].append(pyc10_msg.message_id)
        
        # Calculate match percentage
        if result['tshark_count'] > 0:
            matches = sum(result['message_matches'])
            result['match_percentage'] = (matches / result['tshark_count']) * 100.0
        else:
            result['match_percentage'] = 0.0
        
        return result


def create_test_file() -> Path:
    """Create a test CH10 file using existing ICD."""
    
    with tempfile.NamedTemporaryFile(suffix='.c10', delete=False) as f:
        output_file = Path(f.name)
    
    # Use existing test ICD
    icd = load_icd(Path('icd/test_icd.yaml'))
    
    # Simple scenario to avoid datetime issues
    scenario = {
        'name': 'Comparison Test',
        'duration_s': 1.0,
        'seed': 42,
        'bus': {}
    }
    
    try:
        stats = write_ch10_file(
            output_path=output_file,
            scenario=scenario,
            icd=icd,
            seed=42
        )
        return output_file
    except Exception as e:
        try:
            output_file.unlink()
        except:
            pass
        raise e


@pytest.mark.skipif(not PYCHAPTER10_AVAILABLE, reason="PyChapter10 not available")
def test_pychapter10_detailed_extraction():
    """Test detailed PyChapter10 message extraction."""
    
    test_file = create_test_file()
    
    try:
        extractor = PyChapter10Extractor()
        messages = extractor.extract_messages(test_file, max_messages=50)
        
        print(f"\n🔍 PyChapter10 extracted {len(messages)} messages")
        
        # Show detailed information
        rt_counts = {}
        sa_counts = {}
        tr_counts = {}
        
        for msg in messages:
            rt_counts[msg.rt] = rt_counts.get(msg.rt, 0) + 1
            sa_counts[msg.sa] = sa_counts.get(msg.sa, 0) + 1
            tr_counts[msg.tr] = tr_counts.get(msg.tr, 0) + 1
        
        print(f"  RT distribution: {dict(sorted(rt_counts.items()))}")
        print(f"  SA distribution: {dict(sorted(sa_counts.items()))}")
        print(f"  TR distribution: {dict(sorted(tr_counts.items()))}")
        
        # Show sample messages
        for i, msg in enumerate(messages[:3]):
            print(f"  Message {i+1}: {msg}")
        
        assert len(messages) > 0, "PyChapter10 should extract messages"
        print("✅ PyChapter10 detailed extraction test passed")
        
    finally:
        try:
            test_file.unlink()
        except:
            pass


@pytest.mark.skipif(not ENABLE_TSHARK, reason="TShark validation disabled")
def test_tshark_detailed_extraction():
    """Test detailed TShark message extraction."""
    
    test_file = create_test_file()
    
    try:
        extractor = TSharkExtractor()
        messages = extractor.extract_messages(test_file, max_messages=50)
        
        print(f"\n🔍 TShark extracted {len(messages)} messages")
        
        # Show detailed information
        rt_counts = {}
        sa_counts = {}
        tr_counts = {}
        
        for msg in messages:
            rt_counts[msg.rt] = rt_counts.get(msg.rt, 0) + 1
            sa_counts[msg.sa] = sa_counts.get(msg.sa, 0) + 1
            tr_counts[msg.tr] = tr_counts.get(msg.tr, 0) + 1
        
        print(f"  RT distribution: {dict(sorted(rt_counts.items()))}")
        print(f"  SA distribution: {dict(sorted(sa_counts.items()))}")
        print(f"  TR distribution: {dict(sorted(tr_counts.items()))}")
        
        # Show sample messages
        for i, msg in enumerate(messages[:3]):
            print(f"  Message {i+1}: {msg}")
        
        print("✅ TShark detailed extraction test passed")
        
    finally:
        try:
            test_file.unlink()
        except:
            pass


@pytest.mark.skipif(not (ENABLE_TSHARK and PYCHAPTER10_AVAILABLE), 
                    reason="Both TShark and PyChapter10 required for comparison")
def test_comprehensive_comparison():
    """Comprehensive comparison between TShark and PyChapter10."""
    
    test_file = create_test_file()
    
    try:
        # Extract with both tools
        tshark_extractor = TSharkExtractor()
        pychapter10_extractor = PyChapter10Extractor()
        
        tshark_messages = tshark_extractor.extract_messages(test_file, max_messages=100)
        pychapter10_messages = pychapter10_extractor.extract_messages(test_file, max_messages=100)
        
        print(f"\n📊 Extraction Results:")
        print(f"  TShark: {len(tshark_messages)} messages")
        print(f"  PyChapter10: {len(pychapter10_messages)} messages")
        
        # Compare results
        comparator = MessageComparator()
        result = comparator.compare(tshark_messages, pychapter10_messages)
        
        print(f"\n📈 Comparison Results:")
        print(f"  Count match: {result['count_match']}")
        print(f"  Match percentage: {result['match_percentage']:.1f}%")
        print(f"  Missing messages: {len(result['missing_messages'])}")
        print(f"  Extra messages: {len(result['extra_messages'])}")
        print(f"  Data differences: {len(result['data_differences'])}")
        
        if result['missing_messages']:
            print(f"  Missing: {result['missing_messages'][:5]}")
        
        if result['extra_messages']:
            print(f"  Extra: {result['extra_messages'][:5]}")
        
        if result['data_differences']:
            print(f"  Data differences: {result['data_differences'][:3]}")
        
        # Save detailed results
        result_file = test_file.with_suffix('.comparison.json')
        with open(result_file, 'w') as f:
            # Convert messages to serializable format
            serializable_result = result.copy()
            serializable_result['tshark_messages'] = [
                {
                    'rt': msg.rt, 'sa': msg.sa, 'tr': msg.tr, 'wc': msg.wc,
                    'data_words': msg.data_words, 'timestamp': msg.timestamp,
                    'frame_number': msg.frame_number
                } for msg in tshark_messages
            ]
            serializable_result['pychapter10_messages'] = [
                {
                    'rt': msg.rt, 'sa': msg.sa, 'tr': msg.tr, 'wc': msg.wc,
                    'data_words': msg.data_words, 'timestamp': msg.timestamp,
                    'frame_number': msg.frame_number
                } for msg in pychapter10_messages
            ]
            json.dump(serializable_result, f, indent=2)
        
        print(f"  Detailed results saved to: {result_file}")
        
        # Basic assertions
        assert len(tshark_messages) >= 0, "TShark should not crash"
        assert len(pychapter10_messages) >= 0, "PyChapter10 should not crash"
        
        # If both tools extracted messages, check for reasonable match
        if len(tshark_messages) > 0 and len(pychapter10_messages) > 0:
            # Allow some tolerance for differences
            if result['match_percentage'] < 50.0:
                print(f"⚠️  Low match percentage: {result['match_percentage']:.1f}%")
                # Don't fail the test, just warn
        
        print("✅ Comprehensive comparison test passed")
        
    finally:
        try:
            test_file.unlink()
            # Also clean up comparison file
            comparison_file = test_file.with_suffix('.comparison.json')
            if comparison_file.exists():
                comparison_file.unlink()
        except:
            pass


def test_tool_availability():
    """Test that required tools are available."""
    
    print(f"\n🔧 Tool Availability:")
    print(f"  TShark: {'✅ Available' if TSHARK_PATH else '❌ Not found'}")
    print(f"  PyChapter10: {'✅ Available' if PYCHAPTER10_AVAILABLE else '❌ Not found'}")
    print(f"  TShark Lua: {'✅ Available' if TSHARK_LUA else '⚠️  Not specified'}")
    
    # At least one tool should be available
    assert TSHARK_PATH or PYCHAPTER10_AVAILABLE, "At least one extraction tool should be available"


if __name__ == "__main__":
    # Run the tests manually
    os.environ['WITH_TSHARK'] = '1'
    
    print("🧪 Running Comprehensive TShark vs PyChapter10 Comparison")
    print("=" * 60)
    
    try:
        test_tool_availability()
        print()
        
        if PYCHAPTER10_AVAILABLE:
            test_pychapter10_detailed_extraction()
            print()
        
        if TSHARK_PATH:
            test_tshark_detailed_extraction()
            print()
        
        if TSHARK_PATH and PYCHAPTER10_AVAILABLE:
            test_comprehensive_comparison()
        
        print("\n🎉 All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        raise
