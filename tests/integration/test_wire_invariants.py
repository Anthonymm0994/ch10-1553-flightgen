"""Test wire-level invariants for CH10 files."""

import pytest
import struct
import tempfile
from pathlib import Path


@pytest.mark.unit
class TestWireInvariants:
    """Test wire-level format invariants."""
    
    def test_wrong_data_type(self):
        """Test detection of wrong data_type field."""
        # Create packet with wrong data type
        sync = 0xEB25
        channel_id = 0x0210  # MS1553 channel
        data_type = 0x01  # Wrong! Should be 0x19 for MS1553
        
        # Build header with wrong data_type
        header = struct.pack('<HH', sync, channel_id)
        header += struct.pack('<II', 44, 20)  # packet_len, data_len
        header += struct.pack('<BB', 0, 0)  # version, sequence
        header += struct.pack('<BB', data_type, 0)  # WRONG data_type at byte 14
        header += struct.pack('<H', 0)  # checksum
        header += struct.pack('<IH', 0, 0)  # RTC
        
        # Simple MS1553 body
        body = struct.pack('<I', 1)  # CSDW with count=1
        body += struct.pack('<HHHH', 0, 100, 8, 0)  # Message header
        body += struct.pack('<HHHH', 0x2822, 0x2800, 0x1234, 0x5678)  # Message data
        
        packet = header + body
        
        # Write to file
        with tempfile.NamedTemporaryFile(suffix='.c10', delete=False) as f:
            output_file = Path(f.name)
            f.write(packet)
        
        try:
            # Validate should detect wrong data_type
            from ch10gen.validate import Ch10Validator
            validator = Ch10Validator(output_file)
            result = validator.validate()
            
            # Should have error about data_type mismatch
            assert len(result['errors']) > 0
            assert any('data_type' in str(e).lower() or 'type' in str(e).lower() 
                      for e in result['errors']), \
                   f"Expected data_type error, got: {result['errors']}"
        finally:
            try:
                output_file.unlink()
            except PermissionError:
                pass  # File still in use on Windows
    
    def test_wrong_csdw_count(self):
        """Test detection of wrong CSDW message count."""
        sync = 0xEB25
        channel_id = 0x0210
        data_type = 0x19  # Correct for MS1553
        
        # Build correct header
        header = struct.pack('<HH', sync, channel_id)
        header += struct.pack('<II', 44, 20)
        header += struct.pack('<BB', 0, 0)
        header += struct.pack('<BB', data_type, 0)
        header += struct.pack('<H', 0)
        header += struct.pack('<IH', 0, 0)
        
        # Body with WRONG count
        body = struct.pack('<I', 5)  # CSDW says 5 messages but only 1 present!
        body += struct.pack('<HHHH', 0, 100, 8, 0)
        body += struct.pack('<HHHH', 0x2822, 0x2800, 0x1234, 0x5678)
        
        packet = header + body
        
        with tempfile.NamedTemporaryFile(suffix='.c10', delete=False) as f:
            output_file = Path(f.name)
            f.write(packet)
        
        try:
            from ch10gen.validate import Ch10Validator
            validator = Ch10Validator(output_file)
            result = validator.validate()
            
            # Should detect count mismatch
            assert len(result['errors']) > 0 or len(result['warnings']) > 0, \
                   "Expected CSDW count error"
        finally:
            try:
                output_file.unlink()
            except PermissionError:
                pass  # File still in use on Windows
    
    def test_bad_packet_length(self):
        """Test detection of incorrect packet length."""
        sync = 0xEB25
        channel_id = 0x0210
        data_type = 0x19
        
        # Header with WRONG packet_len
        header = struct.pack('<HH', sync, channel_id)
        header += struct.pack('<II', 100, 20)  # packet_len wrong! Should be 44
        header += struct.pack('<BB', 0, 0)
        header += struct.pack('<BB', data_type, 0)
        header += struct.pack('<H', 0)
        header += struct.pack('<IH', 0, 0)
        
        body = struct.pack('<I', 1)
        body += struct.pack('<HHHH', 0, 100, 8, 0)
        body += struct.pack('<HHHH', 0x2822, 0x2800, 0x1234, 0x5678)
        
        packet = header + body
        
        with tempfile.NamedTemporaryFile(suffix='.c10', delete=False) as f:
            output_file = Path(f.name)
            f.write(packet)
        
        try:
            # This should fail to parse correctly
            from ch10gen.validate import Ch10Validator
            validator = Ch10Validator(output_file)
            result = validator.validate()
            
            # Should have parsing error or warning
            assert result['packet_count'] == 0 or len(result['errors']) > 0, \
                   "Expected packet length error"
        finally:
            try:
                output_file.unlink()
            except PermissionError:
                pass  # File still in use on Windows
    
    def test_missing_sync_pattern(self):
        """Test detection of missing sync pattern."""
        # Create packet WITHOUT sync pattern
        bad_sync = 0x1234  # Wrong!
        channel_id = 0x0210
        
        header = struct.pack('<HH', bad_sync, channel_id)
        header += struct.pack('<II', 44, 20)
        header += struct.pack('<BB', 0, 0)
        header += struct.pack('<BB', 0x19, 0)
        header += struct.pack('<H', 0)
        header += struct.pack('<IH', 0, 0)
        
        body = struct.pack('<I', 1)
        body += struct.pack('<HHHH', 0, 100, 8, 0)
        body += struct.pack('<HHHH', 0x2822, 0x2800, 0x1234, 0x5678)
        
        packet = header + body
        
        with tempfile.NamedTemporaryFile(suffix='.c10', delete=False) as f:
            output_file = Path(f.name)
            f.write(packet)
        
        try:
            from ch10gen.validate import Ch10Validator
            validator = Ch10Validator(output_file)
            result = validator.validate()
            
            # Should not find any valid packets
            assert result['packet_count'] == 0, \
                   f"Should find no packets with bad sync, found {result['packet_count']}"
        finally:
            try:
                output_file.unlink()
            except PermissionError:
                pass  # File still in use on Windows


@pytest.mark.unit
class TestFieldPositions:
    """Test exact field positions in packets."""
    
    def test_data_type_at_byte_14(self):
        """Verify data_type is at byte offset 14."""
        sync = 0xEB25
        channel_id = 0x0210
        data_type = 0x19
        
        header = struct.pack('<HH', sync, channel_id)
        header += struct.pack('<II', 44, 20)
        header += struct.pack('<BB', 0, 0)
        header += struct.pack('<BB', data_type, 0)  # data_type at byte 14
        header += struct.pack('<H', 0)
        header += struct.pack('<IH', 0, 0)
        
        # Verify data_type is at byte 14
        assert header[14] == 0x19, f"data_type not at byte 14, got {header[14]:02x}"
    
    def test_csdw_message_count(self):
        """Verify CSDW message count is in lower 16 bits."""
        message_count = 7
        format_version = 0
        ttb_present = 0
        
        csdw = message_count | (format_version << 16) | (ttb_present << 20)
        csdw_bytes = struct.pack('<I', csdw)
        
        # Extract count from lower 16 bits
        extracted_count = struct.unpack('<I', csdw_bytes)[0] & 0xFFFF
        assert extracted_count == 7, f"CSDW count wrong, got {extracted_count}"
    
    def test_sync_pattern_endianness(self):
        """Verify sync pattern is little-endian 0xEB25."""
        sync = 0xEB25
        sync_bytes = struct.pack('<H', sync)
        
        # Should be [0x25, 0xEB] in memory (little-endian)
        assert sync_bytes[0] == 0x25, f"Sync byte 0 wrong: {sync_bytes[0]:02x}"
        assert sync_bytes[1] == 0xEB, f"Sync byte 1 wrong: {sync_bytes[1]:02x}"
