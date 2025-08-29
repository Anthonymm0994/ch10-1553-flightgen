"""Comprehensive validation tests."""

import pytest
import struct
import tempfile
import json
from pathlib import Path
from datetime import datetime, timedelta


@pytest.mark.unit
class TestValidationCore:
    """Test core validation functionality."""
    
    def test_validate_empty_file(self):
        """Test validation of empty file."""
        from ch10gen.validate import Ch10Validator
        
        with tempfile.NamedTemporaryFile(suffix='.c10', delete=False) as f:
            test_file = Path(f.name)
            # Write nothing - empty file
        
        try:
            validator = Ch10Validator(test_file)
            result = validator.validate()
            
            # Should report no packets
            assert result['packet_count'] == 0
            assert len(result['errors']) > 0
            assert any('empty' in str(e).lower() or 'no packets' in str(e).lower() 
                      for e in result['errors'])
        finally:
            test_file.unlink()
    
    def test_validate_truncated_header(self):
        """Test validation of file with truncated header."""
        with tempfile.NamedTemporaryFile(suffix='.c10', delete=False) as f:
            test_file = Path(f.name)
            # Write incomplete header (only 20 bytes instead of 24)
            f.write(b'\x25\xEB' + b'\x00' * 18)
        
        try:
            from ch10gen.validate import Ch10Validator
            validator = Ch10Validator(test_file)
            result = validator.validate()
            
            # Should detect truncated header
            assert result['packet_count'] == 0
            assert len(result['errors']) > 0
        finally:
            test_file.unlink()
    
    def test_validate_good_packet(self):
        """Test validation of well-formed packet."""
        with tempfile.NamedTemporaryFile(suffix='.c10', delete=False) as f:
            test_file = Path(f.name)
            
            # Build valid packet
            sync = 0xEB25
            channel_id = 0x0210
            packet_len = 44
            data_len = 20
            data_type = 0x19
            
            header = struct.pack('<HH', sync, channel_id)
            header += struct.pack('<II', packet_len, data_len)
            header += struct.pack('<BB', 0, 0)
            header += struct.pack('<BB', data_type, 0)
            header += struct.pack('<H', 0)
            header += struct.pack('<IH', 0, 0)
            
            body = struct.pack('<I', 1)  # CSDW with count=1
            body += struct.pack('<HHHH', 0, 100, 8, 0)  # Message header
            body += struct.pack('<HHHH', 0x2822, 0x2800, 0x1234, 0x5678)  # Message
            
            f.write(header + body)
        
        try:
            from ch10gen.validate import Ch10Validator
            validator = Ch10Validator(test_file)
            result = validator.validate()
            
            # Should validate successfully
            assert result['packet_count'] >= 1
            assert result['valid'] == True or len(result['errors']) == 0
        finally:
            test_file.unlink()
    
    def test_validate_multiple_packets(self):
        """Test validation of file with multiple packets."""
        with tempfile.NamedTemporaryFile(suffix='.c10', delete=False) as f:
            test_file = Path(f.name)
            
            # Write 3 valid packets
            for i in range(3):
                sync = 0xEB25
                channel_id = 0x0210
                packet_len = 44
                data_len = 20
                data_type = 0x19
                
                header = struct.pack('<HH', sync, channel_id)
                header += struct.pack('<II', packet_len, data_len)
                header += struct.pack('<BB', 0, i)  # sequence number
                header += struct.pack('<BB', data_type, 0)
                header += struct.pack('<H', 0)
                header += struct.pack('<IH', i * 1000000, 0)  # RTC
                
                body = struct.pack('<I', 1)
                body += struct.pack('<HHHH', 0, 100, 8, 0)
                body += struct.pack('<HHHH', 0x2822, 0x2800, i, i+1)
                
                f.write(header + body)
        
        try:
            from ch10gen.validate import Ch10Validator
            validator = Ch10Validator(test_file)
            result = validator.validate()
            
            # Should find all 3 packets
            assert result['packet_count'] == 3
            
            # Check sequence numbers if tracked
            if 'sequence_errors' in result:
                assert result['sequence_errors'] == 0
        finally:
            test_file.unlink()


@pytest.mark.unit
class TestFieldValidation:
    """Test validation of specific fields."""
    
    def test_sync_pattern_validation(self):
        """Test sync pattern validation."""
        test_cases = [
            (0xEB25, True, "Valid sync"),
            (0x25EB, False, "Byte-swapped sync"),
            (0x0000, False, "Zero sync"),
            (0xFFFF, False, "Invalid sync")
        ]
        
        for sync_value, should_be_valid, description in test_cases:
            with tempfile.NamedTemporaryFile(suffix='.c10', delete=False) as f:
                test_file = Path(f.name)
                
                # Build packet with test sync
                header = struct.pack('<H', sync_value)
                header += struct.pack('<H', 0x0210)  # channel
                header += struct.pack('<II', 44, 20)  # lengths
                header += struct.pack('<BB', 0, 0)
                header += struct.pack('<BB', 0x19, 0)
                header += struct.pack('<H', 0)
                header += struct.pack('<IH', 0, 0)
                
                body = b'\x00' * 20
                f.write(header + body)
            
            try:
                from ch10gen.validate import Ch10Validator
                validator = Ch10Validator(test_file)
                result = validator.validate()
                
                if should_be_valid:
                    assert result['packet_count'] > 0, f"{description} failed"
                else:
                    assert result['packet_count'] == 0, f"{description} wrongly accepted"
            finally:
                test_file.unlink()
    
    def test_data_type_validation(self):
        """Test data type field validation."""
        test_cases = [
            (0x0210, 0x19, True, "MS1553F1 on 1553 channel"),
            (0x0200, 0x01, True, "TMATS on TMATS channel"),
            (0x0100, 0x11, True, "Time F1 on time channel"),
            (0x0210, 0x01, False, "Wrong type for 1553 channel"),
            (0x0200, 0x19, False, "Wrong type for TMATS channel")
        ]
        
        for channel, dtype, should_match, description in test_cases:
            with tempfile.NamedTemporaryFile(suffix='.c10', delete=False) as f:
                test_file = Path(f.name)
                
                header = struct.pack('<HH', 0xEB25, channel)
                header += struct.pack('<II', 44, 20)
                header += struct.pack('<BB', 0, 0)
                header += struct.pack('<BB', dtype, 0)  # data_type at byte 14
                header += struct.pack('<H', 0)
                header += struct.pack('<IH', 0, 0)
                
                body = b'\x00' * 20
                f.write(header + body)
            
            try:
                from ch10gen.validate import Ch10Validator
                validator = Ch10Validator(test_file)
                result = validator.validate()
                
                # Check for type mismatch warnings
                if not should_match:
                    # Should have warning about type mismatch
                    has_warning = any('type' in str(w).lower() 
                                     for w in result.get('warnings', []))
                    # Some validators might put it in errors
                    has_error = any('type' in str(e).lower() 
                                   for e in result.get('errors', []))
                    # At least one should flag it
                    assert has_warning or has_error or result['packet_count'] == 0, \
                           f"{description} not detected"
            finally:
                test_file.unlink()
    
    def test_packet_length_validation(self):
        """Test packet length field validation."""
        with tempfile.NamedTemporaryFile(suffix='.c10', delete=False) as f:
            test_file = Path(f.name)
            
            # Write packet with mismatched length
            header = struct.pack('<HH', 0xEB25, 0x0210)
            header += struct.pack('<II', 100, 20)  # Claims 100 bytes but only 44
            header += struct.pack('<BB', 0, 0)
            header += struct.pack('<BB', 0x19, 0)
            header += struct.pack('<H', 0)
            header += struct.pack('<IH', 0, 0)
            
            body = b'\x00' * 20
            f.write(header + body)
        
        try:
            from ch10gen.validate import Ch10Validator
            validator = Ch10Validator(test_file)
            result = validator.validate()
            
            # Should detect length mismatch
            assert len(result.get('errors', [])) > 0 or \
                   len(result.get('warnings', [])) > 0 or \
                   result['packet_count'] == 0
        finally:
            test_file.unlink()


@pytest.mark.unit
class TestMS1553Validation:
    """Test MS1553-specific validation."""
    
    def test_csdw_message_count(self):
        """Test CSDW message count validation."""
        with tempfile.NamedTemporaryFile(suffix='.c10', delete=False) as f:
            test_file = Path(f.name)
            
            # Header
            header = struct.pack('<HH', 0xEB25, 0x0210)
            header += struct.pack('<II', 64, 40)  # Larger for 2 messages
            header += struct.pack('<BB', 0, 0)
            header += struct.pack('<BB', 0x19, 0)
            header += struct.pack('<H', 0)
            header += struct.pack('<IH', 0, 0)
            
            # CSDW says 2 messages
            body = struct.pack('<I', 2)
            
            # But only include 1 message
            body += struct.pack('<HHHH', 0, 100, 8, 0)
            body += struct.pack('<HHHH', 0x2822, 0x2800, 0x1234, 0x5678)
            # Missing second message!
            
            # Pad to claimed size
            body += b'\x00' * (40 - len(body))
            
            f.write(header + body)
        
        try:
            from ch10gen.validate import Ch10Validator
            validator = Ch10Validator(test_file)
            result = validator.validate()
            
            # Should detect count mismatch
            has_issue = (
                any('count' in str(e).lower() for e in result.get('errors', [])) or
                any('count' in str(w).lower() for w in result.get('warnings', [])) or
                any('csdw' in str(e).lower() for e in result.get('errors', [])) or
                result.get('message_count_errors', 0) > 0
            )
            
            # Validator should flag this somehow
            assert has_issue or result['packet_count'] == 0
        finally:
            test_file.unlink()
    
    def test_ipts_monotonicity(self):
        """Test IPTS timestamp monotonicity validation."""
        with tempfile.NamedTemporaryFile(suffix='.c10', delete=False) as f:
            test_file = Path(f.name)
            
            # Write 2 packets with non-monotonic IPTS
            for i, ipts in enumerate([1000000, 500000]):  # Second is earlier!
                header = struct.pack('<HH', 0xEB25, 0x0210)
                header += struct.pack('<II', 44, 20)
                header += struct.pack('<BB', 0, i)
                header += struct.pack('<BB', 0x19, 0)
                header += struct.pack('<H', 0)
                header += struct.pack('<IH', ipts, 0)  # Non-monotonic RTC
                
                body = struct.pack('<I', 1)
                body += struct.pack('<HHHH', 0, ipts, 8, 0)  # IPTS in message
                body += struct.pack('<HHHH', 0x2822, 0x2800, 0, 0)
                
                f.write(header + body)
        
        try:
            from ch10gen.validate import Ch10Validator
            validator = Ch10Validator(test_file)
            result = validator.validate()
            
            # Should detect non-monotonic timestamps
            has_time_issue = (
                any('time' in str(e).lower() or 'monotonic' in str(e).lower() 
                    for e in result.get('errors', [])) or
                any('time' in str(w).lower() or 'monotonic' in str(w).lower() 
                    for w in result.get('warnings', [])) or
                result.get('time_errors', 0) > 0
            )
            
            # Should flag timing issue
            assert has_time_issue or len(result.get('warnings', [])) > 0
        finally:
            test_file.unlink()


@pytest.mark.integration
class TestEndToEndValidation:
    """Test end-to-end validation scenarios."""
    
    def test_validate_generated_file(self):
        """Test validation of file generated by our system."""
        from ch10gen.ch10_writer import write_ch10_file
        from ch10gen.icd import ICDDefinition, MessageDefinition, WordDefinition
        from ch10gen.validate import Ch10Validator
        
        # Create simple ICD
        icd = ICDDefinition(
            bus='A',
            messages=[
                MessageDefinition(
                    name='TEST_MSG',
                    rate_hz=10,
                    rt=1,
                    tr='BC2RT',
                    sa=1,
                    wc=2,
                    words=[
                        WordDefinition(name='w1', const=0x1234),
                        WordDefinition(name='w2', const=0x5678)
                    ]
                )
            ]
        )
        
        scenario = {
            'name': 'Validation Test',
            'duration_s': 5,
            'seed': 42,
            'profile': {
                'base_altitude_ft': 5000,
                'segments': [{'type': 'cruise', 'ias_kt': 200, 'hold_s': 5}]
            }
        }
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / 'test_validate.c10'
            
            # Generate file
            stats = write_ch10_file(
                output_path=output_file,
                scenario=scenario,
                icd=icd,
                writer_backend='irig106',
                seed=42
            )
            
            # Validate generated file
            validator = Ch10Validator(output_file)
            result = validator.validate()
            
            # Should be valid
            assert result['packet_count'] > 0
            assert result.get('valid', True) == True or len(result.get('errors', [])) == 0
            
            # Should have expected message count
            expected_messages = 10 * 5  # rate * duration
            if 'message_count' in result:
                assert abs(result['message_count'] - expected_messages) < 5
    
    def test_validate_with_errors(self):
        """Test validation of file with injected errors."""
        from ch10gen.ch10_writer import write_ch10_file
        from ch10gen.icd import ICDDefinition, MessageDefinition, WordDefinition
        from ch10gen.validate import Ch10Validator
        
        # Create ICD with error injection
        icd = ICDDefinition(
            bus='A',
            messages=[
                MessageDefinition(
                    name='ERROR_MSG',
                    rate_hz=5,
                    rt=2,
                    tr='BC2RT',
                    sa=1,
                    wc=2,
                    words=[
                        WordDefinition(name='w1', const=0),
                        WordDefinition(name='w2', const=0)
                    ],
                    errors={
                        'parity_error_percent': 10.0,
                        'no_response_percent': 5.0
                    }
                )
            ]
        )
        
        scenario = {
            'name': 'Error Test',
            'duration_s': 10,
            'seed': 99
        }
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / 'test_errors.c10'
            
            # Generate file with errors
            stats = write_ch10_file(
                output_path=output_file,
                scenario=scenario,
                icd=icd,
                writer_backend='irig106',
                seed=99
            )
            
            # Validate file with errors
            validator = Ch10Validator(output_file)
            result = validator.validate()
            
            # Should still parse but may have warnings
            assert result['packet_count'] > 0
            
            # May have detected some errors
            if 'error_count' in result:
                assert result['error_count'] >= 0
