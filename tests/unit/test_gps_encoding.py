#!/usr/bin/env python3
"""Test GPS message encoding."""

from ch10gen.icd import load_icd
from ch10gen.core.encode1553 import float32_split
from ch10gen.ch10_writer import Ch10Writer, Ch10WriterConfig


def test_gps_encoding():
    """Test that GPS messages are encoded correctly."""
    print("=== GPS Encoding Test ===")
    
    # Load test ICD
    icd = load_icd('icd/test_icd.yaml')
    
    # Find GPS message
    gps_msg = None
    for msg in icd.messages:
        if msg.name == 'GPS_5HZ':
            gps_msg = msg
            break
    
    print(f"✅ GPS message: {gps_msg.name}")
    print(f"  RT={gps_msg.rt}, SA={gps_msg.sa}, WC={gps_msg.wc}")
    print(f"  Words: {len(gps_msg.words)}")
    
    # Check each word
    total_data_words = 0
    for i, word in enumerate(gps_msg.words):
        print(f"  Word {i}: {word.name}, encode={word.encode}")
        if word.encode == 'float32_split':
            total_data_words += 2
        else:
            total_data_words += 1
    
    print(f"  Total data words generated: {total_data_words}")
    print(f"  Expected (WC): {gps_msg.wc}")
    
    if total_data_words == gps_msg.wc:
        print("✅ Word count matches!")
    else:
        print(f"❌ Word count mismatch: {total_data_words} != {gps_msg.wc}")
    
    # Test float32_split encoding
    print(f"\n🔍 Testing float32_split encoding:")
    lat_value = 37.7749
    lon_value = -122.4194
    
    lat_w1, lat_w2 = float32_split(lat_value, 'lsw_msw')
    lon_w1, lon_w2 = float32_split(lon_value, 'lsw_msw')
    
    print(f"  lat={lat_value} -> [{lat_w1}, {lat_w2}]")
    print(f"  lon={lon_value} -> [{lon_w1}, {lon_w2}]")
    
    # Test message encoding
    print(f"\n🔍 Testing message encoding:")
    
    # Create a simple flight state
    class SimpleFlightState:
        def __init__(self):
            self.latitude_deg = lat_value
            self.longitude_deg = lon_value
            self.altitude_ft = 1000
            self.airspeed_kts = 250
            self.heading_deg = 90
    
    flight_state = SimpleFlightState()
    
    # Create CH10 writer
    config = Ch10WriterConfig()
    writer = Ch10Writer(config, writer_backend='irig106')
    
    # Encode GPS message
    data_words = writer._encode_data_words(gps_msg, flight_state)
    print(f"  Encoded data words: {data_words}")
    print(f"  Data word count: {len(data_words)}")
    
    if len(data_words) == gps_msg.wc:
        print("✅ Message encoding works correctly!")
    else:
        print(f"❌ Message encoding failed: {len(data_words)} != {gps_msg.wc}")


if __name__ == "__main__":
    test_gps_encoding()
