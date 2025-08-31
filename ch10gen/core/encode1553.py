"""1553 word encoders (BNR/BCD/float splits) with bitfield packing support."""

import struct
from typing import Tuple, Optional, Union, Dict


def bnr16(value: float, scale: float = 1.0, offset: float = 0.0, 
          clamp: bool = True, rounding: str = 'nearest') -> int:
    """
    Encode value as BNR 16-bit (Binary Natural Representation).
    
    Args:
        value: Engineering value to encode
        scale: Scale factor
        offset: Offset value
        clamp: Whether to clamp to 16-bit signed range
        rounding: Rounding mode ('nearest', 'truncate', 'away_from_zero')
    
    Returns:
        16-bit unsigned integer
    """
    scaled = (value - offset) / scale
    
    if rounding == 'truncate':
        val = int(scaled)
    elif rounding == 'away_from_zero':
        # Round away from zero for 0.5 values (some avionics standards)
        if scaled >= 0:
            val = int(scaled + 0.5)
        else:
            val = int(scaled - 0.5)
    else:  # 'nearest' (default)
        val = int(round(scaled))
    
    if clamp:
        val = max(min(val, 0x7FFF), -0x8000)
    
    return val & 0xFFFF


def u16(value: Union[int, float], scale: float = 1.0, offset: float = 0.0) -> int:
    """
    Encode value as unsigned 16-bit integer.
    
    Args:
        value: Value to encode
        scale: Scale factor
        offset: Offset value
    
    Returns:
        16-bit unsigned integer
    """
    val = int(round((value - offset) / scale))
    return max(0, min(val, 0xFFFF)) & 0xFFFF


def i16(value: Union[int, float], scale: float = 1.0, offset: float = 0.0) -> int:
    """
    Encode value as signed 16-bit integer.
    
    Args:
        value: Value to encode
        scale: Scale factor
        offset: Offset value
    
    Returns:
        16-bit unsigned integer (two's complement)
    """
    val = int(round((value - offset) / scale))
    val = max(-32768, min(val, 32767))
    return val & 0xFFFF


def bcd(value: int) -> int:
    """
    Encode value as BCD (Binary Coded Decimal).
    
    Args:
        value: Decimal value (0-9999)
    
    Returns:
        16-bit BCD encoded value
    """
    if value < 0 or value > 9999:
        raise ValueError(f"BCD value must be 0-9999, got {value}. BCD encoding only supports 4-digit decimal values.")
    
    result = 0
    shift = 0
    
    while value > 0 and shift < 16:
        digit = value % 10
        result |= (digit << shift)
        value //= 10
        shift += 4
    
    return result & 0xFFFF


def float32_split(value: float, word_order: str = "lsw_msw") -> Tuple[int, int]:
    """
    Split IEEE 754 float into two 16-bit words.
    
    Args:
        value: Float value to encode
        word_order: "lsw_msw" or "msw_lsw"
    
    Returns:
        Tuple of two 16-bit words
    """
    # Pack as little-endian float
    b = struct.pack("<f", float(value))
    
    # Extract 16-bit words
    lsw = b[0] | (b[1] << 8)
    msw = b[2] | (b[3] << 8)
    
    if word_order == "lsw_msw":
        return (lsw, msw)
    elif word_order == "msw_lsw":
        return (msw, lsw)
    else:
        raise ValueError(f"Invalid word_order: '{word_order}'. Must be 'lsw_msw' or 'msw_lsw'")


def float32_combine(word1: int, word2: int, word_order: str = "lsw_msw") -> float:
    """
    Combine two 16-bit words into IEEE 754 float.
    
    Args:
        word1: First 16-bit word
        word2: Second 16-bit word
        word_order: "lsw_msw" or "msw_lsw"
    
    Returns:
        Float value
    """
    if word_order == "lsw_msw":
        lsw, msw = word1, word2
    elif word_order == "msw_lsw":
        msw, lsw = word1, word2
    else:
        raise ValueError(f"Invalid word_order: {word_order}")
    
    # Reconstruct bytes
    b = bytes([
        lsw & 0xFF,
        (lsw >> 8) & 0xFF,
        msw & 0xFF,
        (msw >> 8) & 0xFF
    ])
    
    # Unpack as little-endian float
    return struct.unpack("<f", b)[0]


def encode_bitfield(value: Union[int, float], mask: int, shift: int, 
                    scale: float = 1.0, offset: float = 0.0) -> int:
    """
    Encode a value into a bitfield within a 16-bit word.
    
    Args:
        value: Value to encode
        mask: Bit mask (before shifting)
        shift: Number of bits to shift left
        scale: Scale factor
        offset: Offset value
    
    Returns:
        Encoded bitfield value (shifted and masked)
    
    Raises:
        ValueError: If scaled value doesn't fit in the available bits
    """
    # Validate mask and shift
    if not (0 <= mask <= 0xFFFF):
        raise ValueError(f"Mask must be 0-65535 (16 bits), got {mask}")
    if not (0 <= shift <= 15):
        raise ValueError(f"Shift must be 0-15 bits, got {shift}")
    
    # Check that shifted mask doesn't overflow
    if mask != 0:
        # Find the highest bit set in mask
        highest_bit = mask.bit_length()
        if highest_bit + shift > 16:
            raise ValueError(f"Mask 0x{mask:04X} with shift {shift} exceeds 16 bits. The shifted value would be 0x{(mask << shift):08X} which is too large for a 16-bit word.")
    
    # Scale the value
    scaled_value = int(round((value - offset) / scale))
    
    # Calculate how many bits are available in the mask
    if mask == 0:
        return 0
    
    # Count bits in mask
    bits_available = mask.bit_length()
    max_value = (1 << bits_available) - 1
    
    # Check if value fits
    if scaled_value < 0 or scaled_value > max_value:
        raise ValueError(
            f"Value {scaled_value} doesn't fit in {bits_available} bits "
            f"(max={max_value}). Consider adjusting scale/offset or using a larger bitfield."
        )
    
    # Apply mask and shift
    return ((scaled_value & mask) << shift) & 0xFFFF


def decode_bitfield(word: int, mask: int, shift: int,
                    scale: float = 1.0, offset: float = 0.0) -> float:
    """
    Decode a bitfield from a 16-bit word.
    
    Args:
        word: 16-bit word containing the bitfield
        mask: Bit mask (before shifting)
        shift: Number of bits to shift right
        scale: Scale factor
        offset: Offset value
    
    Returns:
        Decoded value
    """
    # Extract the bitfield
    extracted = (word >> shift) & mask
    
    # Scale back to engineering units
    return extracted * scale + offset


def pack_bitfields(fields: Dict[str, Tuple[Union[int, float], int, int, float, float]]) -> int:
    """
    Pack multiple bitfields into a single 16-bit word.
    
    Args:
        fields: Dictionary of field_name -> (value, mask, shift, scale, offset)
    
    Returns:
        16-bit word with all fields packed
    
    Raises:
        ValueError: If fields overlap or values don't fit
    """
    word = 0
    used_bits = 0
    
    for field_name, (value, mask, shift, scale, offset) in fields.items():
        # Encode the field
        encoded = encode_bitfield(value, mask, shift, scale, offset)
        
        # Check for overlap
        shifted_mask = (mask << shift) & 0xFFFF
        if used_bits & shifted_mask:
            raise ValueError(f"Field '{field_name}' overlaps with previously packed fields. Bit positions {shift}-{shift + mask.bit_length() - 1} are already used.")
        
        # Pack into word
        word |= encoded
        used_bits |= shifted_mask
    
    return word & 0xFFFF


def unpack_bitfields(word: int, fields: Dict[str, Tuple[int, int, float, float]]) -> Dict[str, float]:
    """
    Unpack multiple bitfields from a single 16-bit word.
    
    Args:
        word: 16-bit word containing packed fields
        fields: Dictionary of field_name -> (mask, shift, scale, offset)
    
    Returns:
        Dictionary of field_name -> decoded value
    """
    result = {}
    
    for field_name, (mask, shift, scale, offset) in fields.items():
        result[field_name] = decode_bitfield(word, mask, shift, scale, offset)
    
    return result


def build_command_word(rt: int, tr: bool, sa: int, wc: int) -> int:
    """
    Build 1553 command word.
    
    Args:
        rt: Remote Terminal address (0-31)
        tr: True for receive (BC->RT), False for transmit (RT->BC)
        sa: Subaddress (0-31)
        wc: Word count (1-32, where 32 is encoded as 0)
    
    Returns:
        16-bit command word
    """
    if rt < 0 or rt > 31:
        raise ValueError(f"Remote Terminal (RT) address must be 0-31, got {rt}")
    if sa < 0 or sa > 31:
        raise ValueError(f"Subaddress (SA) must be 0-31, got {sa}")
    if wc < 1 or wc > 32:
        raise ValueError(f"Word count (WC) must be 1-32, got {wc}")
    
    # Encode word count (32 -> 0)
    wc_field = wc if wc < 32 else 0
    
    # Build command word: RT(5) | TR(1) | SA(5) | WC(5)
    cmd = (rt << 11) | (int(tr) << 10) | (sa << 5) | wc_field
    
    return cmd & 0xFFFF


def build_status_word(rt: int, message_error: bool = False, 
                      instrumentation: bool = False, service_request: bool = False,
                      broadcast_received: bool = False, busy: bool = False,
                      subsystem_flag: bool = False, dynamic_bus_control: bool = False,
                      terminal_flag: bool = False) -> int:
    """
    Build 1553 status word.
    
    Args:
        rt: Remote Terminal address (0-31)
        message_error: Message error flag
        instrumentation: Instrumentation flag
        service_request: Service request flag
        broadcast_received: Broadcast command received flag
        busy: Busy flag
        subsystem_flag: Subsystem flag
        dynamic_bus_control: Dynamic bus control acceptance flag
        terminal_flag: Terminal flag
    
    Returns:
        16-bit status word
    """
    if rt < 0 or rt > 31:
        raise ValueError(f"Remote Terminal (RT) address must be 0-31, got {rt}")
    
    # Build status word: RT(5) | ME(1) | I(1) | SR(1) | Reserved(3) | BCR(1) | B(1) | SF(1) | DBC(1) | TF(1)
    status = (rt << 11)
    
    if message_error:
        status |= (1 << 10)
    if instrumentation:
        status |= (1 << 9)
    if service_request:
        status |= (1 << 8)
    # Bits 7-5 are reserved
    if broadcast_received:
        status |= (1 << 4)
    if busy:
        status |= (1 << 3)
    if subsystem_flag:
        status |= (1 << 2)
    if dynamic_bus_control:
        status |= (1 << 1)
    if terminal_flag:
        status |= (1 << 0)
    
    return status & 0xFFFF


def add_parity(word: int, odd: bool = True) -> int:
    """
    Add parity bit to 1553 word.
    
    Args:
        word: 16-bit word
        odd: Use odd parity (default True for 1553)
    
    Returns:
        17-bit word with parity
    """
    # Count set bits in lower 16 bits
    ones = bin(word & 0xFFFF).count('1')
    
    # Add parity bit (bit 16)
    if odd:
        # Odd parity: total ones should be odd
        if ones % 2 == 0:
            word |= (1 << 16)
    else:
        # Even parity: total ones should be even
        if ones % 2 == 1:
            word |= (1 << 16)
    
    return word
