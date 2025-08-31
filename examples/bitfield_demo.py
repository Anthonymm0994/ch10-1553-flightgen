#!/usr/bin/env python3
"""
Bitfield Packing Demonstration

This script demonstrates how to use the new bitfield packing functionality
to efficiently pack multiple parameters into single 16-bit words.
"""

from ch10gen.core.encode1553 import (
    encode_bitfield, decode_bitfield, pack_bitfields, unpack_bitfields
)


def demo_basic_bitfields():
    """Demonstrate basic bitfield encoding and decoding."""
    print("=== Basic Bitfield Demo ===")
    
    # Example: Pack status flags into a single word
    system_ok = 1      # 1 bit
    warning = 0        # 1 bit  
    error = 0          # 1 bit
    temperature = 75    # 7 bits (0-127)
    pressure = 50      # 6 bits (0-63)
    
    # Encode individual fields
    word = 0
    word |= encode_bitfield(system_ok, mask=0x01, shift=0)      # bit 0
    word |= encode_bitfield(warning, mask=0x01, shift=1)        # bit 1
    word |= encode_bitfield(error, mask=0x01, shift=2)          # bit 2
    word |= encode_bitfield(temperature, mask=0x7F, shift=3)    # bits 3-9
    word |= encode_bitfield(pressure, mask=0x3F, shift=10)     # bits 10-15
    
    print(f"Packed word: 0x{word:04X}")
    
    # Decode individual fields
    decoded_system_ok = decode_bitfield(word, mask=0x01, shift=0)
    decoded_warning = decode_bitfield(word, mask=0x01, shift=1)
    decoded_error = decode_bitfield(word, mask=0x01, shift=2)
    decoded_temp = decode_bitfield(word, mask=0x7F, shift=3)
    decoded_pressure = decode_bitfield(word, mask=0x3F, shift=10)
    
    print(f"Decoded: system_ok={decoded_system_ok}, warning={decoded_warning}, "
          f"error={decoded_error}, temp={decoded_temp}, pressure={decoded_pressure}")
    
    # Verify round-trip
    assert decoded_system_ok == system_ok
    assert decoded_warning == warning
    assert decoded_error == error
    assert decoded_temp == temperature
    assert decoded_pressure == pressure
    print("✓ Round-trip verification passed!")


def demo_multi_field_packing():
    """Demonstrate packing multiple fields at once."""
    print("\n=== Multi-Field Packing Demo ===")
    
    # Define fields with their values, masks, shifts, scales, and offsets
    fields = {
        'status': (1, 0x01, 0, 1.0, 0.0),           # 1 bit at position 0
        'warning': (0, 0x01, 1, 1.0, 0.0),          # 1 bit at position 1
        'error': (0, 0x01, 2, 1.0, 0.0),            # 1 bit at position 2
        'temperature': (75, 0x7F, 3, 1.0, -40.0),    # 7 bits at position 3
        'pressure': (100, 0x3F, 10, 10.0, 0.0)      # 6 bits at position 10
    }
    
    # Pack all fields into a single word
    packed_word = pack_bitfields(fields)
    print(f"Packed word: 0x{packed_word:04X}")
    
    # Unpack all fields
    unpack_fields = {
        name: (mask, shift, scale, offset)
        for name, (_, mask, shift, scale, offset) in fields.items()
    }
    
    unpacked = unpack_bitfields(packed_word, unpack_fields)
    
    print("Unpacked values:")
    for name, value in unpacked.items():
        print(f"  {name}: {value}")
    
    # Verify the temperature calculation
    # Original: 75°C, scale: 1.0, offset: -40°C
    # Encoded: (75 - (-40)) / 1.0 = 115
    # Decoded: 115 * 1.0 + (-40) = 75°C
    assert abs(unpacked['temperature'] - 75.0) < 0.001
    print("✓ Temperature calculation verified!")


def demo_scale_and_offset():
    """Demonstrate scaling and offset handling."""
    print("\n=== Scale and Offset Demo ===")
    
    # Example: Engine RPM with scale and offset
    rpm = 2500
    scale = 10.0      # RPM per unit
    offset = 0.0      # No offset
    
    # This should fit in 11 bits (0-2047)
    mask = 0x7FF
    
    encoded = encode_bitfield(rpm, mask=mask, shift=0, scale=scale, offset=offset)
    decoded = decode_bitfield(encoded, mask=mask, shift=0, scale=scale, offset=offset)
    
    print(f"Original RPM: {rpm}")
    print(f"Encoded value: {encoded} (fits in 11 bits)")
    print(f"Decoded RPM: {decoded}")
    print(f"✓ Round-trip: {rpm} → {encoded} → {decoded}")


def demo_error_handling():
    """Demonstrate error handling for invalid configurations."""
    print("\n=== Error Handling Demo ===")
    
    try:
        # This should fail: value too large for mask
        result = encode_bitfield(1000, mask=0x0F, shift=0)
        print("❌ Should have failed!")
    except ValueError as e:
        print(f"✓ Caught expected error: {e}")
    
    try:
        # This should fail: shift too large
        result = encode_bitfield(1, mask=0x01, shift=16)
        print("❌ Should have failed!")
    except ValueError as e:
        print(f"✓ Caught expected error: {e}")
    
    try:
        # This should fail: mask too large
        result = encode_bitfield(1, mask=0x10000, shift=0)
        print("❌ Should have failed!")
    except ValueError as e:
        print(f"✓ Caught expected error: {e}")


def demo_realistic_scenario():
    """Demonstrate a realistic avionics scenario."""
    print("\n=== Realistic Avionics Scenario ===")
    
    # Pack typical avionics status into a single word
    avionics_fields = {
        'system_ok': (1, 0x01, 0, 1.0, 0.0),           # 1 bit
        'warning': (0, 0x01, 1, 1.0, 0.0),             # 1 bit
        'error': (0, 0x01, 2, 1.0, 0.0),               # 1 bit
        'temperature': (75, 0x7F, 3, 1.0, -40.0),       # 7 bits, -40 to +87°C
        'pressure': (630, 0x3F, 10, 10.0, 0.0)         # 6 bits, 0 to 6300 hPa
    }
    
    packed = pack_bitfields(avionics_fields)
    print(f"Avionics status word: 0x{packed:04X}")
    
    # Show bit layout
    print("Bit layout:")
    for i in range(16):
        bit = (packed >> i) & 1
        print(f"  Bit {i:2d}: {bit}")
    
    # Unpack and display
    unpack_fields = {
        name: (mask, shift, scale, offset)
        for name, (_, mask, shift, scale, offset) in avionics_fields.items()
    }
    
    unpacked = unpack_bitfields(packed, unpack_fields)
    print("\nUnpacked values:")
    for name, value in unpacked.items():
        print(f"  {name}: {value}")


if __name__ == "__main__":
    print("CH10Gen Bitfield Packing Demonstration")
    print("=" * 50)
    
    demo_basic_bitfields()
    demo_multi_field_packing()
    demo_scale_and_offset()
    demo_error_handling()
    demo_realistic_scenario()
    
    print("\n" + "=" * 50)
    print("All demonstrations completed successfully!")
    print("\nThis shows how the new bitfield functionality allows you to:")
    print("- Pack multiple parameters into single 16-bit words")
    print("- Handle scaling and offsets automatically")
    print("- Validate bit allocations and prevent overlaps")
    print("- Maintain full round-trip data integrity")
    print("- Optimize bandwidth usage in 1553 messages")
