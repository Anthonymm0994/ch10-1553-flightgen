#!/usr/bin/env python3
"""
Custom encoding example.
Demonstrates advanced encoding techniques including bitfield packing.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from ch10gen.core.encode1553 import (
    encode_u16, encode_i16, encode_bnr16,
    encode_bitfield, pack_bitfields
)

def demonstrate_custom_encoding():
    """Show various encoding techniques."""
    
    print("Custom Encoding Techniques")
    print("="*50)
    
    # 1. Basic unsigned encoding
    print("\n1. Unsigned 16-bit encoding:")
    altitude = 25000  # feet
    encoded = encode_u16(altitude)
    print(f"   Altitude {altitude} ft -> 0x{encoded:04X}")
    
    # 2. Signed encoding
    print("\n2. Signed 16-bit encoding:")
    pitch = -15  # degrees
    encoded = encode_i16(pitch)
    print(f"   Pitch {pitch} deg -> 0x{encoded:04X}")
    
    # 3. BNR encoding with scaling
    print("\n3. Binary Number Representation (BNR):")
    heading = 270.5  # degrees
    encoded = encode_bnr16(heading, scale=1.0)
    print(f"   Heading {heading} deg -> 0x{encoded:04X}")
    
    # 4. Single bitfield
    print("\n4. Bitfield encoding:")
    # Pack a 10-bit altitude value
    altitude_100ft = 250  # 25,000 ft in 100ft units
    encoded = encode_bitfield(
        value=altitude_100ft,
        mask=0x03FF,  # 10 bits
        shift=0,
        scale=1.0
    )
    print(f"   Altitude {altitude_100ft}00 ft (10 bits) -> 0x{encoded:04X}")
    
    # 5. Multiple bitfields in one word
    print("\n5. Multi-field packing:")
    
    # System status word with multiple fields
    status_word = pack_bitfields({
        'power_on': (1, 0x0001, 0, 1.0, 0.0),      # Bit 0
        'gps_valid': (1, 0x0001, 1, 1.0, 0.0),     # Bit 1
        'ins_ready': (1, 0x0001, 2, 1.0, 0.0),     # Bit 2
        'mode': (3, 0x0007, 3, 1.0, 0.0),          # Bits 3-5 (mode 3)
        'error_count': (5, 0x001F, 6, 1.0, 0.0),   # Bits 6-10
        'reserved': (0, 0x001F, 11, 1.0, 0.0),     # Bits 11-15
    })
    
    print(f"   Status word: 0x{status_word:04X}")
    print(f"   Binary: {status_word:016b}")
    print("   Fields:")
    print("     - Power ON: Yes (bit 0)")
    print("     - GPS Valid: Yes (bit 1)")
    print("     - INS Ready: Yes (bit 2)")
    print("     - Mode: 3 (bits 3-5)")
    print("     - Error Count: 5 (bits 6-10)")
    
    # 6. Complex sensor data packing
    print("\n6. Sensor data packing:")
    
    # Temperature and pressure in one word
    temp_c = 25.5  # Celsius
    pressure_psi = 14.7  # PSI
    
    sensor_word = pack_bitfields({
        'temperature': (int((temp_c + 50) * 2), 0x00FF, 0, 1.0, 0.0),  # 8 bits, -50 to +77.5°C
        'pressure': (int(pressure_psi * 10), 0x00FF, 8, 1.0, 0.0),     # 8 bits, 0-25.5 PSI
    })
    
    print(f"   Sensor word: 0x{sensor_word:04X}")
    print(f"   Temperature: {temp_c}°C")
    print(f"   Pressure: {pressure_psi} PSI")
    
    # 7. Navigation data with scaling
    print("\n7. Scaled navigation data:")
    
    lat_deg = 37.7749  # San Francisco latitude
    # Scale to fit in 16 bits with 0.001 degree resolution
    lat_scaled = int((lat_deg + 90) * 1000)  # Range: -90 to +90 degrees
    
    # Split into two words for full precision
    lat_low = lat_scaled & 0xFFFF
    lat_high = (lat_scaled >> 16) & 0xFFFF
    
    print(f"   Latitude: {lat_deg}°")
    print(f"   Scaled value: {lat_scaled}")
    print(f"   Low word: 0x{lat_low:04X}")
    print(f"   High word: 0x{lat_high:04X}")
    
    print("\n" + "="*50)
    print("Custom encoding demonstration complete!")

def create_custom_icd():
    """Create a custom ICD with advanced encoding."""
    
    custom_icd = {
        'name': 'Custom Encoding Example',
        'bus': 'A',
        'messages': [
            {
                'name': 'SYSTEM_STATUS',
                'rate_hz': 10.0,
                'rt': 1,
                'tr': 'RT2BC',
                'sa': 1,
                'wc': 1,
                'words': [
                    {'name': 'power', 'encode': 'u16', 'mask': 0x0001, 'shift': 0, 'const': 1},
                    {'name': 'gps', 'encode': 'u16', 'mask': 0x0001, 'shift': 1, 'const': 1, 'word_index': 0},
                    {'name': 'ins', 'encode': 'u16', 'mask': 0x0001, 'shift': 2, 'const': 1, 'word_index': 0},
                    {'name': 'mode', 'encode': 'u16', 'mask': 0x0007, 'shift': 3, 'const': 3, 'word_index': 0},
                    {'name': 'errors', 'encode': 'u16', 'mask': 0x001F, 'shift': 6, 'const': 0, 'word_index': 0},
                ]
            },
            {
                'name': 'SENSOR_DATA',
                'rate_hz': 20.0,
                'rt': 2,
                'tr': 'RT2BC',
                'sa': 2,
                'wc': 2,
                'words': [
                    {'name': 'temp', 'encode': 'u16', 'mask': 0x00FF, 'shift': 0, 'src': 'sensor.temperature'},
                    {'name': 'press', 'encode': 'u16', 'mask': 0x00FF, 'shift': 8, 'src': 'sensor.pressure', 'word_index': 0},
                    {'name': 'humidity', 'encode': 'u16', 'src': 'sensor.humidity', 'word_index': 1},
                ]
            }
        ]
    }
    
    # Save to file
    import yaml
    output_path = Path(__file__).parent.parent / "icd" / "custom_encoding.yaml"
    with open(output_path, 'w') as f:
        yaml.dump(custom_icd, f, default_flow_style=False)
    
    print(f"\nCustom ICD saved to: {output_path}")
    return output_path

def main():
    """Main entry point."""
    demonstrate_custom_encoding()
    
    print("\n" + "="*50)
    print("Creating custom ICD with these encodings...")
    icd_path = create_custom_icd()
    
    print("\nYou can validate this ICD with:")
    print(f"  python -m ch10gen check-icd {icd_path}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
