"""
Comprehensive tests for float32_split encoding/decoding.
Tests both encoding and decoding with different word orders and endianness.
"""

import pytest
import struct
from ch10gen.core.encode1553 import float32_split, float32_combine


class TestFloat32Split:
    """Test float32_split encoding."""
    
    def test_basic_encoding_lsw_msw(self):
        """Test basic float32 encoding with lsw_msw order."""
        value = 123.456
        lsw, msw = float32_split(value, "lsw_msw")
        
        # Verify we get two 16-bit words
        assert 0 <= lsw <= 0xFFFF
        assert 0 <= msw <= 0xFFFF
        
        # Verify round-trip
        decoded = float32_combine(lsw, msw, "lsw_msw")
        assert abs(decoded - value) < 1e-5
    
    def test_basic_encoding_msw_lsw(self):
        """Test basic float32 encoding with msw_lsw order."""
        value = 123.456
        msw, lsw = float32_split(value, "msw_lsw")
        
        # Verify we get two 16-bit words
        assert 0 <= lsw <= 0xFFFF
        assert 0 <= msw <= 0xFFFF
        
        # Verify round-trip
        decoded = float32_combine(msw, lsw, "msw_lsw")
        assert abs(decoded - value) < 1e-5
    
    def test_negative_values(self):
        """Test encoding of negative float values."""
        value = -123.456
        lsw, msw = float32_split(value, "lsw_msw")
        
        decoded = float32_combine(lsw, msw, "lsw_msw")
        assert abs(decoded - value) < 1e-5
    
    def test_zero_value(self):
        """Test encoding of zero."""
        value = 0.0
        lsw, msw = float32_split(value, "lsw_msw")
        
        decoded = float32_combine(lsw, msw, "lsw_msw")
        assert decoded == 0.0
    
    def test_very_small_values(self):
        """Test encoding of very small float values."""
        value = 1e-6
        lsw, msw = float32_split(value, "lsw_msw")
        
        decoded = float32_combine(lsw, msw, "lsw_msw")
        assert abs(decoded - value) < 1e-5
    
    def test_very_large_values(self):
        """Test encoding of very large float values."""
        value = 1e6
        lsw, msw = float32_split(value, "lsw_msw")
        
        decoded = float32_combine(lsw, msw, "lsw_msw")
        assert abs(decoded - value) < 1e-5
    
    def test_infinity(self):
        """Test encoding of infinity."""
        import math
        value = float('inf')
        lsw, msw = float32_split(value, "lsw_msw")
        
        decoded = float32_combine(lsw, msw, "lsw_msw")
        assert math.isinf(decoded)
        assert decoded > 0
    
    def test_negative_infinity(self):
        """Test encoding of negative infinity."""
        import math
        value = float('-inf')
        lsw, msw = float32_split(value, "lsw_msw")
        
        decoded = float32_combine(lsw, msw, "lsw_msw")
        assert math.isinf(decoded)
        assert decoded < 0
    
    def test_nan(self):
        """Test encoding of NaN."""
        import math
        value = float('nan')
        lsw, msw = float32_split(value, "lsw_msw")
        
        decoded = float32_combine(lsw, msw, "lsw_msw")
        assert math.isnan(decoded)
    
    def test_invalid_word_order(self):
        """Test that invalid word order raises ValueError."""
        with pytest.raises(ValueError, match="Invalid word_order"):
            float32_split(123.456, "invalid")
    
    def test_word_order_consistency(self):
        """Test that different word orders produce different results."""
        value = 123.456
        
        lsw1, msw1 = float32_split(value, "lsw_msw")
        msw2, lsw2 = float32_split(value, "msw_lsw")
        
        # The words should be different
        assert (lsw1, msw1) != (msw2, lsw2)
        
        # But both should decode to the same value
        decoded1 = float32_combine(lsw1, msw1, "lsw_msw")
        decoded2 = float32_combine(msw2, lsw2, "msw_lsw")
        
        assert abs(decoded1 - decoded2) < 1e-5
        assert abs(decoded1 - value) < 1e-5


class TestFloat32Combine:
    """Test float32_combine decoding."""
    
    def test_basic_decoding_lsw_msw(self):
        """Test basic float32 decoding with lsw_msw order."""
        # Create known float32 bytes
        value = 123.456
        b = struct.pack("<f", value)
        lsw = b[0] | (b[1] << 8)
        msw = b[2] | (b[3] << 8)
        
        decoded = float32_combine(lsw, msw, "lsw_msw")
        assert abs(decoded - value) < 1e-5
    
    def test_basic_decoding_msw_lsw(self):
        """Test basic float32 decoding with msw_lsw order."""
        # Create known float32 bytes
        value = 123.456
        b = struct.pack("<f", value)
        msw = b[2] | (b[3] << 8)
        lsw = b[0] | (b[1] << 8)
        
        decoded = float32_combine(msw, lsw, "msw_lsw")
        assert abs(decoded - value) < 1e-5
    
    def test_invalid_word_order(self):
        """Test that invalid word order raises ValueError."""
        with pytest.raises(ValueError, match="Invalid word_order"):
            float32_combine(0x1234, 0x5678, "invalid")
    
    def test_edge_case_words(self):
        """Test decoding with edge case word values."""
        # Test with all zeros
        decoded = float32_combine(0, 0, "lsw_msw")
        assert decoded == 0.0
        
        # Test with all ones
        decoded = float32_combine(0xFFFF, 0xFFFF, "lsw_msw")
        # Should be NaN or some other special value
        import math
        assert math.isnan(decoded) or math.isinf(decoded)


class TestFloat32RoundTrip:
    """Test round-trip encoding/decoding."""
    
    @pytest.mark.parametrize("value", [
        0.0, 1.0, -1.0, 123.456, -123.456,
        1e-6, -1e-6, 1e6, -1e6,
        float('inf'), float('-inf'), float('nan')
    ])
    @pytest.mark.parametrize("word_order", ["lsw_msw", "msw_lsw"])
    def test_round_trip(self, value, word_order):
        """Test round-trip encoding/decoding for various values."""
        import math
        
        if word_order == "lsw_msw":
            word1, word2 = float32_split(value, word_order)
            decoded = float32_combine(word1, word2, word_order)
        else:  # msw_lsw
            word1, word2 = float32_split(value, word_order)
            decoded = float32_combine(word1, word2, word_order)
        
        if math.isnan(value):
            assert math.isnan(decoded)
        elif math.isinf(value):
            assert math.isinf(decoded)
            assert (decoded > 0) == (value > 0)
        else:
            assert abs(decoded - value) < 1e-5
    
    def test_gps_like_values(self):
        """Test with GPS-like coordinate values."""
        # Typical GPS coordinates
        lat = 37.7749  # San Francisco latitude
        lon = -122.4194  # San Francisco longitude
        alt = 100.5  # Altitude in meters
        
        for value in [lat, lon, alt]:
            for word_order in ["lsw_msw", "msw_lsw"]:
                if word_order == "lsw_msw":
                    word1, word2 = float32_split(value, word_order)
                    decoded = float32_combine(word1, word2, word_order)
                else:
                    word1, word2 = float32_split(value, word_order)
                    decoded = float32_combine(word1, word2, word_order)
                
                assert abs(decoded - value) < 1e-5


class TestFloat32ICDCompatibility:
    """Test compatibility with different ICD float32 specifications."""
    
    def test_icd_word_order_variations(self):
        """Test that our implementation handles different ICD word order specifications."""
        value = 123.456
        
        # Some ICDs might specify word order differently
        # Test that our implementation is consistent
        lsw, msw = float32_split(value, "lsw_msw")
        
        # Verify the bytes are in the expected order
        b = struct.pack("<f", value)
        expected_lsw = b[0] | (b[1] << 8)
        expected_msw = b[2] | (b[3] << 8)
        
        assert lsw == expected_lsw
        assert msw == expected_msw
    
    def test_manual_byte_construction(self):
        """Test manual construction of float32 from bytes."""
        value = 123.456
        b = struct.pack("<f", value)
        
        # Extract words manually
        lsw = b[0] | (b[1] << 8)
        msw = b[2] | (b[3] << 8)
        
        # Reconstruct bytes
        reconstructed = bytes([
            lsw & 0xFF,
            (lsw >> 8) & 0xFF,
            msw & 0xFF,
            (msw >> 8) & 0xFF
        ])
        
        # Should match original
        assert reconstructed == b
        
        # Should decode to same value
        decoded = struct.unpack("<f", reconstructed)[0]
        assert abs(decoded - value) < 1e-5
