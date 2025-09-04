"""Tests for bitfield packing and unpacking functionality."""

import pytest
from ch10gen.core.encode1553 import (
    encode_bitfield, decode_bitfield, pack_bitfields, unpack_bitfields
)


class TestBitfieldEncoding:
    """Test individual bitfield encoding and decoding."""
    
    def test_basic_bitfield_encoding(self):
        """Test basic bitfield encoding with mask and shift."""
        # 4-bit field starting at bit 0
        result = encode_bitfield(5, mask=0x0F, shift=0, scale=1.0, offset=0.0)
        assert result == 0x0005
        
        # 4-bit field starting at bit 4
        result = encode_bitfield(3, mask=0x0F, shift=4, scale=1.0, offset=0.0)
        assert result == 0x0030
        
        # 4-bit field starting at bit 8
        result = encode_bitfield(7, mask=0x0F, shift=8, scale=1.0, offset=0.0)
        assert result == 0x0700
    
    def test_bitfield_with_scale_and_offset(self):
        """Test bitfield encoding with scale and offset."""
        # Value 25.5 with scale 0.5 and offset 0.0 should fit in 6 bits
        result = encode_bitfield(25.5, mask=0x3F, shift=2, scale=0.5, offset=0.0)
        # 25.5 / 0.5 = 51, which fits in 6 bits (max 63)
        assert result == (51 << 2) & 0xFFFF
    
    def test_bitfield_validation(self):
        """Test that bitfield encoding validates value ranges."""
        # 4-bit field can only hold 0-15
        with pytest.raises(ValueError, match="doesn't fit in 4 bits"):
            encode_bitfield(20, mask=0x0F, shift=0)
        
        # 3-bit field can only hold 0-7
        with pytest.raises(ValueError, match="doesn't fit in 3 bits"):
            encode_bitfield(10, mask=0x07, shift=0)
    
    def test_edge_cases(self):
        """Test edge cases for bitfield encoding."""
        # Zero mask
        result = encode_bitfield(42, mask=0, shift=0)
        assert result == 0
        
        # Maximum value for 4 bits
        result = encode_bitfield(15, mask=0x0F, shift=0)
        assert result == 0x000F
        
        # Zero value
        result = encode_bitfield(0, mask=0x0F, shift=4)
        assert result == 0x0000
    
    def test_shift_overflow_validation(self):
        """Test that shift + mask doesn't exceed 16 bits."""
        # This should work: 4 bits at position 12
        result = encode_bitfield(5, mask=0x0F, shift=12)
        assert result == 0x5000
        
        # This should fail: 4 bits at position 13 would overflow
        with pytest.raises(ValueError, match="exceeds 16 bits"):
            encode_bitfield(5, mask=0x0F, shift=13)


class TestBitfieldDecoding:
    """Test individual bitfield decoding."""
    
    def test_basic_bitfield_decoding(self):
        """Test basic bitfield decoding."""
        word = 0x1234
        
        # Extract 4 bits at position 0
        result = decode_bitfield(word, mask=0x0F, shift=0, scale=1.0, offset=0.0)
        assert result == 4.0
        
        # Extract 4 bits at position 4
        result = decode_bitfield(word, mask=0x0F, shift=4, scale=1.0, offset=0.0)
        assert result == 3.0
        
        # Extract 4 bits at position 8
        result = decode_bitfield(word, mask=0x0F, shift=8, scale=1.0, offset=0.0)
        assert result == 2.0
        
        # Extract 4 bits at position 12
        result = decode_bitfield(word, mask=0x0F, shift=12, scale=1.0, offset=0.0)
        assert result == 1.0
    
    def test_decode_with_scale_and_offset(self):
        """Test bitfield decoding with scale and offset."""
        word = 0x0050  # 5 at position 4
        
        result = decode_bitfield(word, mask=0x0F, shift=4, scale=0.5, offset=10.0)
        # (5 * 0.5) + 10.0 = 12.5
        assert result == 12.5
    
    def test_round_trip_encoding_decoding(self):
        """Test that encode -> decode restores the original value."""
        original_value = 42.5
        mask = 0x7F  # 7 bits
        shift = 3
        scale = 0.5
        offset = 10.0
        
        # Encode
        encoded = encode_bitfield(original_value, mask, shift, scale, offset)
        
        # Decode
        decoded = decode_bitfield(encoded, mask, shift, scale, offset)
        
        # Should be very close (within floating point precision)
        assert abs(decoded - original_value) < 0.001


class TestMultiFieldPacking:
    """Test packing multiple fields into a single word."""
    
    def test_pack_two_fields(self):
        """Test packing two non-overlapping fields."""
        fields = {
            'status': (3, 0x0F, 0, 1.0, 0.0),      # 4 bits at position 0
            'count': (42, 0x7F, 4, 1.0, 0.0)        # 7 bits at position 4
        }
        
        result = pack_bitfields(fields)
        
        # status: 3 << 0 = 3
        # count: 42 << 4 = 672
        # total: 3 | 672 = 675
        assert result == 675
        
        # Verify individual fields
        assert (result & 0x0F) == 3      # status
        assert ((result >> 4) & 0x7F) == 42  # count
    
    def test_pack_three_fields(self):
        """Test packing three fields with gaps."""
        fields = {
            'flag1': (1, 0x01, 0, 1.0, 0.0),       # 1 bit at position 0
            'flag2': (1, 0x01, 2, 1.0, 0.0),        # 1 bit at position 2
            'value': (25, 0x1F, 8, 1.0, 0.0)        # 5 bits at position 8
        }
        
        result = pack_bitfields(fields)
        
        # flag1: 1 << 0 = 1
        # flag2: 1 << 2 = 4
        # value: 25 << 8 = 6400
        # total: 1 | 4 | 6400 = 6405
        assert result == 6405
    
    def test_pack_with_scale_and_offset(self):
        """Test packing fields with different scales and offsets."""
        fields = {
            'temp': (20.5, 0x3F, 0, 0.5, -10.0),   # 6 bits, scale 0.5, offset -10
            'pressure': (1000, 0x1FF, 6, 10.0, 0.0) # 9 bits, scale 10, offset 0
        }
        
        result = pack_bitfields(fields)
        
        # temp: (25.5 - (-10)) / 0.5 = 71, but 71 doesn't fit in 6 bits (max=63)
        # Let's use a value that fits: 25.5 - (-10) = 35.5, 35.5 / 0.5 = 71
        # But 71 > 63, so we need a smaller value
        # Let's use 20.5: (20.5 - (-10)) / 0.5 = 61, which fits in 6 bits
        
        # pressure: 1000 / 10 = 100, fits in 9 bits
        expected_temp = 61  # (20.5 - (-10)) / 0.5 = 61
        expected_pressure = 100
        
        assert (result & 0x3F) == expected_temp
        assert ((result >> 6) & 0x1FF) == expected_pressure
    
    def test_pack_overlapping_fields_rejected(self):
        """Test that overlapping fields are rejected."""
        fields = {
            'field1': (1, 0x0F, 0, 1.0, 0.0),      # 4 bits at position 0
            'field2': (2, 0x0F, 2, 1.0, 0.0)       # 4 bits at position 2 (overlaps!)
        }
        
        with pytest.raises(ValueError, match="overlaps"):
            pack_bitfields(fields)
    
    def test_pack_fields_exceeding_word_size(self):
        """Test that fields exceeding 16 bits are rejected."""
        fields = {
            'field1': (1, 0x0F, 0, 1.0, 0.0),      # 4 bits at position 0
            'field2': (1, 0x0F, 13, 1.0, 0.0)      # 4 bits at position 13 (overflow!)
        }
        
        with pytest.raises(ValueError, match="exceeds 16 bits"):
            pack_bitfields(fields)


class TestMultiFieldUnpacking:
    """Test unpacking multiple fields from a single word."""
    
    def test_unpack_two_fields(self):
        """Test unpacking two fields."""
        word = 0x1234
        fields = {
            'low': (0x0F, 0, 1.0, 0.0),     # 4 bits at position 0
            'high': (0x0F, 4, 1.0, 0.0)     # 4 bits at position 4
        }
        
        result = unpack_bitfields(word, fields)
        
        assert result['low'] == 4.0
        assert result['high'] == 3.0
    
    def test_unpack_with_scale_and_offset(self):
        """Test unpacking with scale and offset."""
        word = 0x0050  # 5 at position 4
        fields = {
            'value': (0x0F, 4, 0.5, 10.0)  # 4 bits at position 4, scale 0.5, offset 10
        }
        
        result = unpack_bitfields(word, fields)
        assert result['value'] == 12.5
    
    def test_unpack_round_trip(self):
        """Test pack -> unpack round trip."""
        original_fields = {
            'status': (3, 0x0F, 0, 1.0, 0.0),
            'count': (42, 0x7F, 4, 1.0, 0.0)
        }
        
        # Pack
        packed = pack_bitfields(original_fields)
        
        # Unpack (need to convert to unpack format)
        unpack_fields = {
            name: (mask, shift, scale, offset)
            for name, (_, mask, shift, scale, offset) in original_fields.items()
        }
        
        unpacked = unpack_bitfields(packed, unpack_fields)
        
        # Should match original values
        assert unpacked['status'] == 3.0
        assert unpacked['count'] == 42.0


class TestBitfieldEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_zero_mask(self):
        """Test behavior with zero mask."""
        result = encode_bitfield(42, mask=0, shift=0)
        assert result == 0
        
        result = decode_bitfield(0x1234, mask=0, shift=0)
        assert result == 0.0
    
    def test_maximum_shift(self):
        """Test maximum valid shift (15)."""
        # 1 bit at position 15
        result = encode_bitfield(1, mask=0x01, shift=15)
        assert result == 0x8000
        
        # Decode
        decoded = decode_bitfield(result, mask=0x01, shift=15)
        assert decoded == 1.0
    
    def test_invalid_shift(self):
        """Test that invalid shifts are caught."""
        with pytest.raises(ValueError, match="Shift must be 0-15"):
            encode_bitfield(1, mask=0x01, shift=16)
    
    def test_invalid_mask(self):
        """Test that invalid masks are caught."""
        with pytest.raises(ValueError, match="Mask must be 0-65535"):
            encode_bitfield(1, mask=0x10000, shift=0)
    
    def test_negative_values_rejected(self):
        """Test that negative values are rejected when they don't fit."""
        # 4-bit unsigned field can't hold negative values
        with pytest.raises(ValueError, match="doesn't fit in 4 bits"):
            encode_bitfield(-1, mask=0x0F, shift=0)


class TestBitfieldIntegration:
    """Test bitfield functionality in realistic scenarios."""
    
    def test_avionics_status_word(self):
        """Test packing typical avionics status bits."""
        fields = {
            'system_ok': (1, 0x01, 0, 1.0, 0.0),           # 1 bit
            'warning': (0, 0x01, 1, 1.0, 0.0),             # 1 bit
            'error': (0, 0x01, 2, 1.0, 0.0),               # 1 bit
            'temperature': (75, 0x7F, 3, 1.0, -40.0),       # 7 bits, 3-9
            'pressure': (1000, 0x1FF, 10, 10.0, 0.0)       # 9 bits, 10-18 (but 18 > 15!)
        }
        
        # This should fail because pressure field exceeds 16 bits
        with pytest.raises(ValueError, match="exceeds 16 bits"):
            pack_bitfields(fields)
    
    def test_valid_avionics_status_word(self):
        """Test packing avionics status bits that fit properly."""
        fields = {
            'system_ok': (1, 0x01, 0, 1.0, 0.0),           # 1 bit
            'warning': (0, 0x01, 1, 1.0, 0.0),             # 1 bit
            'error': (0, 0x01, 2, 1.0, 0.0),               # 1 bit
            'temperature': (75, 0x7F, 3, 1.0, -40.0),       # 7 bits, 3-9
            'pressure': (630, 0x3F, 10, 10.0, 0.0)         # 6 bits, 10-15 (fits! max=63)
        }
        
        result = pack_bitfields(fields)
        
        # Verify individual fields
        assert (result & 0x01) == 1      # system_ok
        assert ((result >> 1) & 0x01) == 0  # warning
        assert ((result >> 2) & 0x01) == 0  # error
        assert ((result >> 3) & 0x7F) == 115  # temperature: (75 - (-40)) = 115
        assert ((result >> 10) & 0x3F) == 63  # pressure: 630 / 10 = 63
    
    def test_engine_parameters(self):
        """Test packing engine parameter fields."""
        fields = {
            'rpm': (2500, 0x7FF, 0, 10.0, 0.0),           # 11 bits, 0-10
            'temperature': (200, 0x1FF, 11, 1.0, 0.0),     # 9 bits, 11-19 (but 19 > 15!)
            'oil_pressure': (1, 0x01, 15, 1.0, 0.0)       # 1 bit, 15
        }
        
        # This should fail because temperature field exceeds 16 bits
        with pytest.raises(ValueError, match="exceeds 16 bits"):
            pack_bitfields(fields)
    
    def test_valid_engine_parameters(self):
        """Test packing engine parameters that fit properly."""
        fields = {
            'rpm': (2500, 0x7FF, 0, 10.0, 0.0),           # 11 bits, 0-10
            'temperature': (30, 0x1F, 11, 1.0, 0.0),       # 5 bits, 11-15 (fits! max=31)
        }
        
        result = pack_bitfields(fields)
        
        # Verify fields
        assert (result & 0x7FF) == 250  # rpm: 2500 / 10 = 250
        assert ((result >> 11) & 0x1F) == 30  # temperature
