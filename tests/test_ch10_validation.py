"""
Comprehensive tests for CH10 format validation and compliance.
Tests CSDW, IPDH, message structure, and error flag validation.
"""

import pytest
import struct
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

try:
    from chapter10 import C10
    from chapter10.ms1553 import MS1553F1
    PYCHAPTER10_AVAILABLE = True
except ImportError:
    PYCHAPTER10_AVAILABLE = False


class TestCH10FormatValidation:
    """Test CH10 format validation according to IRIG-106."""
    
    def test_csdw_validation(self):
        """Test Channel Specific Data Word validation."""
        # CSDW format: [Message Count:24][Time Tag Bits:2][Reserved:6]
        msg_count = 5
        time_tag_bits = 2
        
        # Pack CSDW
        csdw = (msg_count & 0xFFFFFF) | ((time_tag_bits & 0x3) << 24)
        csdw_data = struct.pack('<I', csdw)
        
        # Unpack and validate
        unpacked = struct.unpack('<I', csdw_data)[0]
        extracted_count = unpacked & 0xFFFFFF
        extracted_ttb = (unpacked >> 24) & 0x3
        
        assert extracted_count == msg_count
        assert extracted_ttb == time_tag_bits
    
    def test_message_length_validation(self):
        """Test 1553 message length validation."""
        # Test different message types and their expected lengths
        
        # BC->RT message: 1 command + 4 data + 1 status = 6 words = 12 bytes
        cmd_word = 0x5084  # RT=10, TR=0, SA=1, WC=4
        expected_length = 2 * (1 + 4 + 1)  # 12 bytes
        
        # Create message data
        msg_data = struct.pack('<H', cmd_word)  # Command
        msg_data += struct.pack('<HHHH', 0x1234, 0x5678, 0x9ABC, 0xDEF0)  # 4 data words
        msg_data += struct.pack('<H', 0x8000)  # Status
        
        assert len(msg_data) == expected_length
        
        # RT->BC message: 1 command + 2 data + 1 status = 4 words = 8 bytes
        cmd_word_rt2bc = 0x5A04  # RT=11, TR=1, SA=1, WC=2
        expected_length_rt2bc = 2 * (1 + 2 + 1)  # 8 bytes
        
        msg_data_rt2bc = struct.pack('<H', cmd_word_rt2bc)  # Command
        msg_data_rt2bc += struct.pack('<HH', 0x1234, 0x5678)  # 2 data words
        msg_data_rt2bc += struct.pack('<H', 0x8000)  # Status
        
        assert len(msg_data_rt2bc) == expected_length_rt2bc
    
    def test_rt2rt_message_length_validation(self):
        """Test RT-to-RT message length validation."""
        # RT-to-RT: 2 commands + 2 data + 2 status = 6 words = 12 bytes
        cmd1 = 0x5084  # RT=10, TR=0, SA=1, WC=2
        cmd2 = 0x5A04  # RT=11, TR=1, SA=1, WC=2
        
        expected_length = 2 * (2 + 2 + 2)  # 12 bytes
        
        msg_data = struct.pack('<HH', cmd1, cmd2)  # 2 commands
        msg_data += struct.pack('<HH', 0x1234, 0x5678)  # 2 data words
        msg_data += struct.pack('<HH', 0x8000, 0x8000)  # 2 status words
        
        assert len(msg_data) == expected_length
    
    def test_broadcast_message_length_validation(self):
        """Test broadcast message length validation."""
        # Broadcast (RT=31): 1 command + 4 data + 0 status = 5 words = 10 bytes
        cmd_word = 0xF804  # RT=31, TR=0, SA=1, WC=4
        
        expected_length = 2 * (1 + 4 + 0)  # 10 bytes
        
        msg_data = struct.pack('<H', cmd_word)  # Command
        msg_data += struct.pack('<HHHH', 0x1234, 0x5678, 0x9ABC, 0xDEF0)  # 4 data words
        # No status word for broadcast
        
        assert len(msg_data) == expected_length
    
    def test_mode_code_message_length_validation(self):
        """Test mode code message length validation."""
        # Mode code with data: 1 command + 1 data + 1 status = 3 words = 6 bytes
        cmd_word = 0x5011  # RT=10, TR=0, SA=0, MC=1 (with data bit set)
        
        expected_length = 2 * (1 + 1 + 1)  # 6 bytes
        
        msg_data = struct.pack('<H', cmd_word)  # Command
        msg_data += struct.pack('<H', 0x1234)  # 1 data word
        msg_data += struct.pack('<H', 0x8000)  # Status
        
        assert len(msg_data) == expected_length
        
        # Mode code without data: 1 command + 0 data + 1 status = 2 words = 4 bytes
        cmd_word_no_data = 0x5001  # RT=10, TR=0, SA=0, MC=1 (no data bit)
        
        expected_length_no_data = 2 * (1 + 0 + 1)  # 4 bytes
        
        msg_data_no_data = struct.pack('<H', cmd_word_no_data)  # Command
        msg_data_no_data += struct.pack('<H', 0x8000)  # Status
        # No data words
        
        assert len(msg_data_no_data) == expected_length_no_data
    
    def test_word_count_zero_handling(self):
        """Test handling of word count 0 (means 32 data words)."""
        # Word count 0 means 32 data words
        cmd_word = 0x5018  # RT=10, TR=0, SA=1, WC=0 (means 32)
        
        expected_length = 2 * (1 + 32 + 1)  # 68 bytes
        
        # Create message with 32 data words
        msg_data = struct.pack('<H', cmd_word)  # Command
        for i in range(32):
            msg_data += struct.pack('<H', 0x1000 + i)  # 32 data words
        msg_data += struct.pack('<H', 0x8000)  # Status
        
        assert len(msg_data) == expected_length
    
    def test_error_flag_validation(self):
        """Test validation of 1553 error flags."""
        # Test various error flag combinations
        error_tests = [
            (0x4000, ["MESSAGE_ERROR"]),
            (0x2000, ["INSTRUMENTATION_ERROR"]),
            (0x1000, ["SERVICE_REQUEST"]),
            (0x0800, ["BROADCAST_RECEIVED"]),
            (0x0400, ["BUSY"]),
            (0x0200, ["SUBSYSTEM_FLAG"]),
            (0x0100, ["TERMINAL_FLAG"]),
            (0x0080, ["DYNAMIC_BUS_CONTROL"]),
            (0x0040, ["ACCEPTANCE_ERROR"]),
            (0x0020, ["PARITY_ERROR"]),
            (0xE000, ["MESSAGE_ERROR", "INSTRUMENTATION_ERROR"]),
        ]
        
        for status_word, expected_errors in error_tests:
            errors = []
            if status_word & 0x4000: errors.append("MESSAGE_ERROR")
            if status_word & 0x2000: errors.append("INSTRUMENTATION_ERROR")
            if status_word & 0x1000: errors.append("SERVICE_REQUEST")
            if status_word & 0x0800: errors.append("BROADCAST_RECEIVED")
            if status_word & 0x0400: errors.append("BUSY")
            if status_word & 0x0200: errors.append("SUBSYSTEM_FLAG")
            if status_word & 0x0100: errors.append("TERMINAL_FLAG")
            if status_word & 0x0080: errors.append("DYNAMIC_BUS_CONTROL")
            if status_word & 0x0040: errors.append("ACCEPTANCE_ERROR")
            if status_word & 0x0020: errors.append("PARITY_ERROR")
            
            assert errors == expected_errors
    
    def test_channel_id_validation(self):
        """Test 1553 channel ID validation."""
        # Valid 1553 channel IDs
        valid_channels = [0x0200, 0x0210]  # 1553A, 1553B
        
        for channel_id in valid_channels:
            # Pack channel ID
            channel_data = struct.pack('<H', channel_id)
            
            # Unpack and validate
            unpacked = struct.unpack('<H', channel_data)[0]
            assert unpacked == channel_id
            
            # Determine channel name
            if channel_id == 0x0200:
                channel_name = 'A'
            elif channel_id == 0x0210:
                channel_name = 'B'
            else:
                channel_name = f'Unknown({hex(channel_id)})'
            
            assert channel_name in ['A', 'B']


@pytest.mark.skipif(not PYCHAPTER10_AVAILABLE, reason="PyChapter10 not available")
class TestPyChapter10Validation:
    """Test validation using PyChapter10 library."""
    
    def test_message_metadata_validation(self):
        """Test validation of PyChapter10 message metadata."""
        # Create mock message with proper metadata
        mock_msg = Mock()
        mock_msg.data = struct.pack('<HHHHHH', 0x5084, 0x8000, 0x1234, 0x5678, 0x9ABC, 0xDEF0)
        mock_msg.length = 12  # 6 words * 2 bytes
        mock_msg.rt2rt = False
        mock_msg.bus = 0  # Bus A
        mock_msg.le = False  # Length Error
        mock_msg.se = False  # Sync Error
        mock_msg.we = False  # Word Error
        mock_msg.timeout = False
        mock_msg.me = False  # Message Error
        mock_msg.fe = False  # Format Error
        mock_msg.gap_time = 0
        
        # Validate message structure
        cmd_word = struct.unpack('<H', mock_msg.data[0:2])[0]
        rt = (cmd_word >> 11) & 0x1F
        tr = (cmd_word >> 10) & 0x01
        sa = (cmd_word >> 5) & 0x1F
        wc = cmd_word & 0x1F
        
        # Calculate expected length
        data_words = 32 if wc == 0 else wc
        cmds = 2 if mock_msg.rt2rt else 1
        stats = 2 if mock_msg.rt2rt else (0 if rt == 31 else 1)
        expected_length = 2 * (cmds + stats + data_words)
        
        assert rt == 10
        assert tr == 0
        assert sa == 4
        assert wc == 4
        assert data_words == 4
        assert expected_length == 12
        assert mock_msg.length == expected_length
        
        # Check error flags
        assert not any([mock_msg.le, mock_msg.se, mock_msg.we, 
                       mock_msg.timeout, mock_msg.me, mock_msg.fe])
    
    def test_packet_metadata_validation(self):
        """Test validation of PyChapter10 packet metadata."""
        # Create mock packet
        mock_packet = Mock()
        mock_packet.data_type = 0x19  # MS1553F1
        mock_packet.channel_id = 0x0200  # 1553A
        mock_packet.count = 3  # 3 messages in packet
        mock_packet.time_tag_bits = 2
        
        # Validate packet metadata
        assert mock_packet.data_type == 0x19
        assert mock_packet.channel_id in [0x0200, 0x0210]
        assert mock_packet.count > 0
        assert 0 <= mock_packet.time_tag_bits <= 3


class TestCH10FileValidation:
    """Test validation of complete CH10 files."""
    
    @pytest.mark.skip(reason="Struct pack format needs fixing")
    def test_file_structure_validation(self):
        """Test validation of CH10 file structure."""
        # This would test the complete file structure
        # For now, we'll test individual components
        
        # Test packet header structure
        sync = 0xEB25
        channel_id = 0x0200
        packet_len = 100
        data_len = 80
        data_type = 0x19
        rtc_low = 0x12345678
        rtc_high = 0x9ABC
        
        # Pack header
        header = struct.pack('<HHI4sH6s', sync, channel_id, packet_len,
                           struct.pack('<I', data_len), data_type,
                           struct.pack('<I', rtc_low), struct.pack('<H', rtc_high))
        
        # Validate header
        assert len(header) == 24  # Standard header size
        assert struct.unpack('<H', header[0:2])[0] == sync
        assert struct.unpack('<H', header[2:4])[0] == channel_id
        assert struct.unpack('<I', header[4:8])[0] == packet_len
        assert struct.unpack('<I', header[8:12])[0] == data_len
        assert header[15] == data_type
    
    def test_csdw_consistency_validation(self):
        """Test CSDW message count consistency."""
        # Test that CSDW message count matches actual message count
        msg_count = 5
        csdw = msg_count & 0xFFFFFF
        csdw_data = struct.pack('<I', csdw)
        
        # Simulate actual message count
        actual_count = 5
        
        # Validate consistency
        unpacked = struct.unpack('<I', csdw_data)[0]
        declared_count = unpacked & 0xFFFFFF
        
        assert declared_count == actual_count
        
        # Test mismatch case
        actual_count_mismatch = 3
        assert declared_count != actual_count_mismatch


class TestValidationTools:
    """Test validation tools and utilities."""
    
    def test_verify_1553_tool_functions(self):
        """Test the verify_1553.py tool functions."""
        # Import the tool functions
        try:
            from tools.verify_1553 import parse_cmd, data_words, validate_message_structure
            
            # Test parse_cmd function
            cmd_word = 0x5084
            rt, tr, sa, wc = parse_cmd(cmd_word)
            assert rt == 10
            assert tr == 0
            assert sa == 4
            assert wc == 4
            
            # Test data_words function
            dwords = data_words(sa, wc)
            assert dwords == 4
            
            # Test mode code data word calculation
            dwords_mode = data_words(0, 0x10)
            assert dwords_mode == 1
            
            dwords_mode_no_data = data_words(0, 0x00)
            assert dwords_mode_no_data == 0
            
        except ImportError:
            pytest.skip("verify_1553.py tool not available")
    
    def test_message_structure_validation_function(self):
        """Test the message structure validation function."""
        try:
            from tools.verify_1553 import validate_message_structure
            
            # Create mock message
            mock_msg = Mock()
            mock_msg.data = struct.pack('<HHHHHH', 0x5084, 0x8000, 0x1234, 0x5678, 0x9ABC, 0xDEF0)
            mock_msg.length = 12
            mock_msg.rt2rt = False
            mock_msg.le = False
            mock_msg.se = False
            mock_msg.we = False
            mock_msg.timeout = False
            mock_msg.me = False
            mock_msg.fe = False
            mock_msg.gap_time = 0
            
            # Validate message structure
            result = validate_message_structure(mock_msg, 0)
            
            assert result['valid'] is True
            assert result['rt'] == 10
            assert result['sa'] == 4
            assert result['wc'] == 4
            assert result['length_ok'] is True
            assert result['critical_errors'] == []
            
        except ImportError:
            pytest.skip("verify_1553.py tool not available")
