"""Tests for 1553 word encoders."""

import pytest
import struct
import math
from ch10gen.core.encode1553 import (
    bnr16, u16, i16, bcd, float32_split, float32_combine,
    build_command_word, build_status_word, add_parity
)


class TestBNR16:
    """Test BNR16 encoding with edge cases."""
    
    def test_sign_handling(self):
        """Test sign handling for positive and negative values."""
        assert bnr16(100.0) == 100
        assert bnr16(-100.0) == (-100 & 0xFFFF)
        assert bnr16(0.0) == 0
    
    def test_clamping(self):
        """Test clamping to 16-bit signed range."""
        assert bnr16(50000.0, clamp=True) == 0x7FFF  # Max positive
        assert bnr16(-50000.0, clamp=True) == 0x8000  # Max negative
        assert bnr16(32767.0, clamp=True) == 0x7FFF
        assert bnr16(-32768.0, clamp=True) == 0x8000
    
    def test_scale_offset(self):
        """Test scaling and offset operations."""
        # Scale by 0.1: 100.0 -> 1000
        assert bnr16(100.0, scale=0.1) == 1000
        
        # Offset by 50: 100 - 50 = 50
        assert bnr16(100.0, offset=50.0) == 50
        
        # Combined: (100 - 50) / 0.1 = 500
        assert bnr16(100.0, scale=0.1, offset=50.0) == 500
        
        # Scale by 2: 100 / 2 = 50
        assert bnr16(100.0, scale=2.0) == 50
    
    def test_round_to_nearest(self):
        """Test round-to-nearest behavior (default)."""
        assert bnr16(100.4) == 100
        assert bnr16(100.5) == 100  # Python's round() does banker's rounding
        assert bnr16(100.6) == 101
        assert bnr16(-100.4) == (-100 & 0xFFFF)
        assert bnr16(-100.5) == (-100 & 0xFFFF)  # Banker's rounding
        assert bnr16(-100.6) == (-101 & 0xFFFF)
        
    def test_round_away_from_zero(self):
        """Test round-away-from-zero mode."""
        assert bnr16(100.4, rounding='away_from_zero') == 100
        assert bnr16(100.5, rounding='away_from_zero') == 101  
        assert bnr16(100.6, rounding='away_from_zero') == 101
        assert bnr16(-100.4, rounding='away_from_zero') == (-100 & 0xFFFF)
        assert bnr16(-100.5, rounding='away_from_zero') == (-101 & 0xFFFF)
        assert bnr16(-100.6, rounding='away_from_zero') == (-101 & 0xFFFF)
        
    def test_truncate_mode(self):
        """Test truncate rounding mode."""
        assert bnr16(100.9, rounding='truncate') == 100
        assert bnr16(-100.9, rounding='truncate') == (-100 & 0xFFFF)
    
    def test_edge_case_vectors(self):
        """Test specific edge case vectors after scaling."""
        # Test vectors: [-32768, -1, 0, 1, 32767]
        vectors = [-32768, -1, 0, 1, 32767]
        
        for val in vectors:
            result = bnr16(val, scale=1.0)
            if val >= 0:
                assert result == val
            else:
                assert result == (val & 0xFFFF)
        
        # With scaling
        scale = 0.5
        expected = [-65536, -2, 0, 2, 65534]  # Before clamping
        clamped = [-32768, -2, 0, 2, 32767]  # After clamping
        
        for val, exp in zip(vectors, clamped):
            result = bnr16(val, scale=scale, clamp=True)
            if exp >= 0:
                assert result == exp
            else:
                assert result == (exp & 0xFFFF)


class TestU16:
    """Test unsigned 16-bit encoding."""
    
    def test_bounds(self):
        """Test unsigned bounds."""
        assert u16(0) == 0
        assert u16(65535) == 0xFFFF
        assert u16(32768) == 32768
    
    def test_clamping_negative(self):
        """Test clamping of negative values to 0."""
        assert u16(-1) == 0
        assert u16(-100) == 0
        assert u16(-65536) == 0
    
    def test_clamping_overflow(self):
        """Test clamping of values > 65535."""
        assert u16(65536) == 0xFFFF
        assert u16(100000) == 0xFFFF
    
    def test_scale_offset(self):
        """Test scaling and offset for unsigned."""
        assert u16(1000, scale=10) == 100
        assert u16(1000, offset=500) == 500
        assert u16(1000, scale=10, offset=500) == 50


class TestI16:
    """Test signed 16-bit encoding."""
    
    def test_twos_complement(self):
        """Test two's complement representation."""
        assert i16(0) == 0
        assert i16(1) == 1
        assert i16(-1) == 0xFFFF
        assert i16(32767) == 32767
        assert i16(-32768) == 0x8000
    
    def test_edge_cases(self):
        """Test edge cases for signed 16-bit."""
        # Maximum positive
        assert i16(32767) == 32767
        # Maximum negative
        assert i16(-32768) == 0x8000
        # Just beyond range
        assert i16(32768) == 32767  # Clamped
        assert i16(-32769) == 0x8000  # Clamped
    
    def test_scale_offset(self):
        """Test scaling and offset for signed."""
        assert i16(100, scale=2) == 50
        assert i16(-100, scale=2) == (-50 & 0xFFFF)
        assert i16(100, offset=50) == 50
        assert i16(-100, offset=50) == (-150 & 0xFFFF)


class TestBCD:
    """Test BCD encoding."""
    
    def test_valid_digits(self):
        """Test valid BCD encoding."""
        assert bcd(0) == 0x0000
        assert bcd(1) == 0x0001
        assert bcd(9) == 0x0009
        assert bcd(10) == 0x0010
        assert bcd(99) == 0x0099
        assert bcd(100) == 0x0100
        assert bcd(999) == 0x0999
        assert bcd(1000) == 0x1000
        assert bcd(1234) == 0x1234
        assert bcd(9999) == 0x9999
    
    def test_invalid_range(self):
        """Test invalid BCD range raises errors."""
        with pytest.raises(ValueError, match="BCD value must be 0-9999.*got -1"):
            bcd(-1)
        
        with pytest.raises(ValueError, match="BCD value must be 0-9999.*got 10000"):
            bcd(10000)
    
    def test_round_trip(self):
        """Test BCD encoding/decoding round-trip."""
        test_values = [0, 1, 10, 99, 100, 999, 1234, 5678, 9999]
        
        for val in test_values:
            encoded = bcd(val)
            # Decode BCD
            decoded = 0
            multiplier = 1
            temp = encoded
            while temp > 0:
                digit = temp & 0xF
                decoded += digit * multiplier
                multiplier *= 10
                temp >>= 4
            assert decoded == val, f"Round-trip failed for {val}"


class TestFloat32Split:
    """Test IEEE 754 float splitting."""
    
    def test_known_vectors(self):
        """Test known IEEE 754 vectors."""
        # Test 0.0
        lsw, msw = float32_split(0.0)
        assert lsw == 0x0000
        assert msw == 0x0000
        
        # Test 1.0 (0x3F800000 in IEEE 754)
        lsw, msw = float32_split(1.0)
        assert lsw == 0x0000
        assert msw == 0x3F80
        
        # Test -2.5 (0xC0200000 in IEEE 754)
        lsw, msw = float32_split(-2.5)
        assert lsw == 0x0000
        assert msw == 0xC020
    
    def test_endian_order(self):
        """Test LSW-MSW vs MSW-LSW ordering."""
        value = 123.456
        
        # LSW-MSW order
        lsw1, msw1 = float32_split(value, 'lsw_msw')
        
        # MSW-LSW order
        msw2, lsw2 = float32_split(value, 'msw_lsw')
        
        # Should be swapped
        assert lsw1 == lsw2
        assert msw1 == msw2
    
    def test_round_trip(self):
        """Test round-trip conversion."""
        test_values = [0.0, 1.0, -1.0, 123.456, -999.999, 1e-10, 1e10, 
                      float('inf'), float('-inf'), math.pi, math.e]
        
        for value in test_values:
            # Skip NaN as it doesn't compare equal to itself
            if math.isnan(value):
                continue
                
            # LSW-MSW order
            lsw, msw = float32_split(value, 'lsw_msw')
            reconstructed = float32_combine(lsw, msw, 'lsw_msw')
            
            if math.isinf(value):
                assert math.isinf(reconstructed)
                assert (value > 0) == (reconstructed > 0)
            else:
                assert abs(reconstructed - value) < abs(value * 1e-6) + 1e-10
            
            # MSW-LSW order
            msw, lsw = float32_split(value, 'msw_lsw')
            reconstructed = float32_combine(msw, lsw, 'msw_lsw')
            
            if math.isinf(value):
                assert math.isinf(reconstructed)
                assert (value > 0) == (reconstructed > 0)
            else:
                assert abs(reconstructed - value) < abs(value * 1e-6) + 1e-10
    
    def test_special_values(self):
        """Test special float values."""
        # Positive infinity
        lsw, msw = float32_split(float('inf'))
        assert msw == 0x7F80
        assert lsw == 0x0000
        
        # Negative infinity
        lsw, msw = float32_split(float('-inf'))
        assert msw == 0xFF80
        assert lsw == 0x0000
        
        # Very small number (denormalized)
        lsw, msw = float32_split(1e-40)
        reconstructed = float32_combine(lsw, msw)
        assert abs(reconstructed - 1e-40) < 1e-45 or reconstructed == 0.0


class TestCommandWord:
    """Test 1553 command word building."""
    
    def test_field_encoding(self):
        """Test correct field encoding."""
        # RT=5, Receive, SA=1, WC=16
        cmd = build_command_word(rt=5, tr=True, sa=1, wc=16)
        
        assert (cmd >> 11) & 0x1F == 5   # RT field
        assert (cmd >> 10) & 0x01 == 1   # TR field (receive)
        assert (cmd >> 5) & 0x1F == 1    # SA field
        assert cmd & 0x1F == 16          # WC field
    
    def test_word_count_32(self):
        """Test word count 32 encoded as 0."""
        cmd = build_command_word(rt=1, tr=True, sa=1, wc=32)
        assert cmd & 0x1F == 0
    
    def test_all_fields(self):
        """Test all field combinations."""
        # Test max values
        cmd = build_command_word(rt=31, tr=False, sa=31, wc=31)
        assert (cmd >> 11) & 0x1F == 31
        assert (cmd >> 10) & 0x01 == 0
        assert (cmd >> 5) & 0x1F == 31
        assert cmd & 0x1F == 31
    
    def test_invalid_parameters(self):
        """Test invalid parameters raise errors."""
        with pytest.raises(ValueError, match="Remote Terminal.*RT.*address must be 0-31.*got 32"):
            build_command_word(rt=32, tr=True, sa=1, wc=16)
        
        with pytest.raises(ValueError, match="Subaddress.*SA.*must be 0-31.*got 32"):
            build_command_word(rt=1, tr=True, sa=32, wc=16)
        
        with pytest.raises(ValueError, match="Word count.*WC.*must be 1-32.*got 0"):
            build_command_word(rt=1, tr=True, sa=1, wc=0)
        
        with pytest.raises(ValueError, match="Word count.*WC.*must be 1-32.*got 33"):
            build_command_word(rt=1, tr=True, sa=1, wc=33)


class TestStatusWord:
    """Test 1553 status word building."""
    
    def test_rt_field(self):
        """Test RT field encoding."""
        for rt in range(32):
            status = build_status_word(rt=rt)
            assert (status >> 11) & 0x1F == rt
    
    def test_flag_bits(self):
        """Test individual flag bits."""
        status = build_status_word(
            rt=10,
            message_error=True,
            instrumentation=True,
            service_request=True,
            broadcast_received=True,
            busy=True,
            subsystem_flag=True,
            dynamic_bus_control=True,
            terminal_flag=True
        )
        
        assert (status >> 11) & 0x1F == 10  # RT
        assert (status >> 10) & 0x01 == 1   # Message error
        assert (status >> 9) & 0x01 == 1    # Instrumentation
        assert (status >> 8) & 0x01 == 1    # Service request
        assert (status >> 4) & 0x01 == 1    # Broadcast received
        assert (status >> 3) & 0x01 == 1    # Busy
        assert (status >> 2) & 0x01 == 1    # Subsystem flag
        assert (status >> 1) & 0x01 == 1    # Dynamic bus control
        assert (status >> 0) & 0x01 == 1    # Terminal flag
    
    def test_no_flags(self):
        """Test with no flags set."""
        status = build_status_word(rt=5)
        assert status == (5 << 11)  # Only RT field set


class TestParity:
    """Test parity bit addition."""
    
    def test_odd_parity(self):
        """Test odd parity calculation."""
        # Word with even number of ones
        word = 0x5555  # 8 ones
        result = add_parity(word, odd=True)
        assert (result >> 16) & 0x01 == 1  # Parity bit set
        
        # Word with odd number of ones
        word = 0x5554  # 7 ones
        result = add_parity(word, odd=True)
        assert (result >> 16) & 0x01 == 0  # Parity bit not set
    
    def test_even_parity(self):
        """Test even parity calculation."""
        # Word with even number of ones
        word = 0x5555  # 8 ones
        result = add_parity(word, odd=False)
        assert (result >> 16) & 0x01 == 0  # Parity bit not set
        
        # Word with odd number of ones
        word = 0x5554  # 7 ones
        result = add_parity(word, odd=False)
        assert (result >> 16) & 0x01 == 1  # Parity bit set
    
    def test_preserves_original(self):
        """Test that original word is preserved."""
        test_words = [0x0000, 0xFFFF, 0xABCD, 0x1234]
        
        for word in test_words:
            result = add_parity(word)
            assert result & 0xFFFF == word
