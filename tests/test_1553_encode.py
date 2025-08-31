"""Tests for 1553 word encoders."""

import pytest
import struct
from ch10gen.core.encode1553 import (
    bnr16, u16, i16, bcd, float32_split, float32_combine,
    build_command_word, build_status_word, add_parity
)


class TestBNR16:
    """Test BNR16 encoding."""
    
    def test_zero(self):
        """Test encoding zero."""
        result = bnr16(0.0)
        assert result == 0
    
    def test_positive(self):
        """Test positive values."""
        result = bnr16(1000.0)
        assert result == 1000
        
        result = bnr16(32767.0)
        assert result == 32767
    
    def test_negative(self):
        """Test negative values."""
        result = bnr16(-1000.0)
        assert result == (-1000 & 0xFFFF)
        
        result = bnr16(-32768.0)
        assert result == 0x8000
    
    def test_scaling(self):
        """Test with scale and offset."""
        # Scale by 0.1
        result = bnr16(100.0, scale=0.1)
        assert result == 1000
        
        # Offset
        result = bnr16(100.0, offset=50.0)
        assert result == 50
        
        # Both
        result = bnr16(100.0, scale=0.1, offset=50.0)
        assert result == 500
    
    def test_clamping(self):
        """Test clamping to 16-bit range."""
        result = bnr16(50000.0, clamp=True)
        assert result == 0x7FFF
        
        result = bnr16(-50000.0, clamp=True)
        assert result == 0x8000
    
    def test_rounding(self):
        """Test rounding behavior."""
        result = bnr16(100.4)
        assert result == 100
        
        result = bnr16(100.5)
        assert result == 100  # Python's banker's rounding (rounds to even)
        
        result = bnr16(100.6)
        assert result == 101


class TestU16:
    """Test unsigned 16-bit encoding."""
    
    def test_zero(self):
        """Test encoding zero."""
        result = u16(0)
        assert result == 0
    
    def test_positive(self):
        """Test positive values."""
        result = u16(1000)
        assert result == 1000
        
        result = u16(65535)
        assert result == 0xFFFF
    
    def test_clamping(self):
        """Test clamping to unsigned range."""
        result = u16(-100)
        assert result == 0
        
        result = u16(70000)
        assert result == 0xFFFF
    
    def test_scaling(self):
        """Test with scale and offset."""
        result = u16(100, scale=0.1)
        assert result == 1000
        
        result = u16(100, offset=50)
        assert result == 50


class TestI16:
    """Test signed 16-bit encoding."""
    
    def test_zero(self):
        """Test encoding zero."""
        result = i16(0)
        assert result == 0
    
    def test_positive(self):
        """Test positive values."""
        result = i16(1000)
        assert result == 1000
        
        result = i16(32767)
        assert result == 32767
    
    def test_negative(self):
        """Test negative values."""
        result = i16(-1000)
        assert result == (-1000 & 0xFFFF)
        
        result = i16(-32768)
        assert result == 0x8000
    
    def test_clamping(self):
        """Test clamping to signed range."""
        result = i16(40000)
        assert result == 32767
        
        result = i16(-40000)
        assert result == 0x8000


class TestBCD:
    """Test BCD encoding."""
    
    def test_single_digit(self):
        """Test single digit values."""
        assert bcd(0) == 0x0000
        assert bcd(5) == 0x0005
        assert bcd(9) == 0x0009
    
    def test_two_digits(self):
        """Test two digit values."""
        assert bcd(10) == 0x0010
        assert bcd(25) == 0x0025
        assert bcd(99) == 0x0099
    
    def test_three_digits(self):
        """Test three digit values."""
        assert bcd(100) == 0x0100
        assert bcd(456) == 0x0456
        assert bcd(999) == 0x0999
    
    def test_four_digits(self):
        """Test four digit values."""
        assert bcd(1000) == 0x1000
        assert bcd(1234) == 0x1234
        assert bcd(9999) == 0x9999
    
    def test_invalid_range(self):
        """Test invalid range raises error."""
        with pytest.raises(ValueError):
            bcd(-1)
        
        with pytest.raises(ValueError):
            bcd(10000)


class TestFloat32Split:
    """Test IEEE 754 float splitting."""
    
    def test_zero(self):
        """Test encoding zero."""
        lsw, msw = float32_split(0.0)
        assert lsw == 0
        assert msw == 0
    
    def test_positive(self):
        """Test positive float."""
        value = 123.456
        lsw, msw = float32_split(value)
        
        # Reconstruct and verify
        reconstructed = float32_combine(lsw, msw)
        assert abs(reconstructed - value) < 0.001
    
    def test_negative(self):
        """Test negative float."""
        value = -123.456
        lsw, msw = float32_split(value)
        
        # Reconstruct and verify
        reconstructed = float32_combine(lsw, msw)
        assert abs(reconstructed - value) < 0.001
    
    def test_word_order_lsw_msw(self):
        """Test LSW-MSW word order."""
        value = 1.5
        lsw, msw = float32_split(value, word_order='lsw_msw')
        
        # Manual check against known IEEE 754 representation
        # 1.5 = 0x3FC00000 in IEEE 754
        # LSW = 0x0000, MSW = 0x3FC0
        assert lsw == 0x0000
        assert msw == 0x3FC0
    
    def test_word_order_msw_lsw(self):
        """Test MSW-LSW word order."""
        value = 1.5
        msw, lsw = float32_split(value, word_order='msw_lsw')
        
        # Should swap the words
        assert msw == 0x3FC0
        assert lsw == 0x0000
    
    def test_round_trip(self):
        """Test round-trip conversion."""
        test_values = [0.0, 1.0, -1.0, 123.456, -999.999, 1e-10, 1e10]
        
        for value in test_values:
            # LSW-MSW order
            lsw, msw = float32_split(value, 'lsw_msw')
            reconstructed = float32_combine(lsw, msw, 'lsw_msw')
            assert abs(reconstructed - value) < abs(value * 1e-6) + 1e-10
            
            # MSW-LSW order
            msw, lsw = float32_split(value, 'msw_lsw')
            reconstructed = float32_combine(msw, lsw, 'msw_lsw')
            assert abs(reconstructed - value) < abs(value * 1e-6) + 1e-10


class TestCommandWord:
    """Test 1553 command word building."""
    
    def test_basic_command(self):
        """Test basic command word."""
        # RT=5, Receive, SA=1, WC=16
        cmd = build_command_word(rt=5, tr=True, sa=1, wc=16)
        
        # Check fields
        assert (cmd >> 11) & 0x1F == 5  # RT
        assert (cmd >> 10) & 0x01 == 1  # TR (receive)
        assert (cmd >> 5) & 0x1F == 1   # SA
        assert cmd & 0x1F == 16         # WC
    
    def test_transmit_command(self):
        """Test transmit command."""
        cmd = build_command_word(rt=10, tr=False, sa=15, wc=8)
        
        assert (cmd >> 11) & 0x1F == 10  # RT
        assert (cmd >> 10) & 0x01 == 0   # TR (transmit)
        assert (cmd >> 5) & 0x1F == 15   # SA
        assert cmd & 0x1F == 8           # WC
    
    def test_word_count_32(self):
        """Test word count 32 encoded as 0."""
        cmd = build_command_word(rt=1, tr=True, sa=1, wc=32)
        assert cmd & 0x1F == 0  # WC=32 encoded as 0
    
    def test_invalid_parameters(self):
        """Test invalid parameters raise errors."""
        with pytest.raises(ValueError):
            build_command_word(rt=32, tr=True, sa=1, wc=16)  # RT > 31
        
        with pytest.raises(ValueError):
            build_command_word(rt=1, tr=True, sa=32, wc=16)  # SA > 31
        
        with pytest.raises(ValueError):
            build_command_word(rt=1, tr=True, sa=1, wc=33)  # WC > 32
        
        with pytest.raises(ValueError):
            build_command_word(rt=1, tr=True, sa=1, wc=0)  # WC < 1


class TestStatusWord:
    """Test 1553 status word building."""
    
    def test_basic_status(self):
        """Test basic status word."""
        status = build_status_word(rt=5)
        
        # Check RT field
        assert (status >> 11) & 0x1F == 5
        
        # All flags should be 0
        assert status & 0x7FF == 0
    
    def test_all_flags(self):
        """Test with all flags set."""
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
    
    def test_invalid_rt(self):
        """Test invalid RT raises error."""
        with pytest.raises(ValueError):
            build_status_word(rt=32)


class TestParity:
    """Test parity bit addition."""
    
    def test_odd_parity_even_ones(self):
        """Test odd parity with even number of ones."""
        # 0x5555 has 8 ones (even)
        result = add_parity(0x5555, odd=True)
        # Should add parity bit
        assert (result >> 16) & 0x01 == 1
    
    def test_odd_parity_odd_ones(self):
        """Test odd parity with odd number of ones."""
        # 0x5554 has 7 ones (odd)
        result = add_parity(0x5554, odd=True)
        # Should not add parity bit
        assert (result >> 16) & 0x01 == 0
    
    def test_even_parity_even_ones(self):
        """Test even parity with even number of ones."""
        # 0x5555 has 8 ones (even)
        result = add_parity(0x5555, odd=False)
        # Should not add parity bit
        assert (result >> 16) & 0x01 == 0
    
    def test_even_parity_odd_ones(self):
        """Test even parity with odd number of ones."""
        # 0x5554 has 7 ones (odd)
        result = add_parity(0x5554, odd=False)
        # Should add parity bit
        assert (result >> 16) & 0x01 == 1
    
    def test_preserves_word(self):
        """Test that original word is preserved."""
        original = 0xABCD
        result = add_parity(original)
        assert result & 0xFFFF == original
