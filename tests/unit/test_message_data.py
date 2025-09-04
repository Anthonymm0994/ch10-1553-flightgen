#!/usr/bin/env python3
"""Test GPS message data generation."""

import struct
from ch10gen.icd import load_icd
from ch10gen.core.encode1553 import build_command_word, build_status_word, float32_split
from ch10gen.ch10_writer import Ch10Writer, Ch10WriterConfig


def test_gps_message_data():
    """Test that GPS message data is generated correctly."""
    print("=== GPS Message Data Test ===")
    
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
    
    # Create a simple flight state
    class SimpleFlightState:
        def __init__(self):
            self.latitude_deg = 37.7749
            self.longitude_deg = -122.4194
            self.altitude_ft = 1000
            self.airspeed_kts = 250
            self.heading_deg = 90
    
    flight_state = SimpleFlightState()
    
    # Create CH10 writer
    config = Ch10WriterConfig()
    writer = Ch10Writer(config, writer_backend='irig106')
    
    # Build command and status words
    command_word = build_command_word(
        rt=gps_msg.rt,
        tr=gps_msg.is_receive(),
        sa=gps_msg.sa,
        wc=gps_msg.wc
    )
    
    status_word = build_status_word(
        rt=gps_msg.rt,
        message_error=False,
        instrumentation=False,
        service_request=False,
        broadcast_received=False,
        busy=False,
        subsystem_flag=False,
        dynamic_bus_control=False,
        terminal_flag=False
    )
    
    print(f"✅ Command word: 0x{command_word:04X}")
    print(f"✅ Status word: 0x{status_word:04X}")
    
    # Encode data words
    data_words = writer._encode_data_words(gps_msg, flight_state)
    print(f"✅ Data words: {data_words}")
    print(f"✅ Data word count: {len(data_words)}")
    
    # Construct message data
    message_words = [command_word, status_word] + data_words
    message_data = b''.join(struct.pack('<H', word) for word in message_words)
    
    print(f"✅ Message data length: {len(message_data)} bytes")
    print(f"✅ Message data (hex): {message_data.hex()}")
    
    # Expected message structure:
    # - 14 bytes header (not included in message_data)
    # - 2 bytes command word
    # - 2 bytes status word
    # - 8 bytes data words (WC=4 × 2 bytes each)
    # Total: 26 bytes
    
    expected_length = 2 + 2 + (gps_msg.wc * 2)
    print(f"✅ Expected length: {expected_length} bytes")
    
    if len(message_data) == expected_length:
        print("✅ Message data length is correct!")
    else:
        print(f"❌ Message data length mismatch: {len(message_data)} != {expected_length}")
    
    # Test parsing the message data
    print(f"\n🔍 Testing message parsing:")
    
    # Extract command word from message data
    cmd_word = struct.unpack('<H', message_data[0:2])[0]
    rt_address = (cmd_word >> 11) & 0x1F
    tr_bit = (cmd_word >> 10) & 0x01
    subaddress = (cmd_word >> 5) & 0x1F
    word_count = cmd_word & 0x1F
    if word_count == 0:
        word_count = 32
    
    print(f"  Parsed command word: 0x{cmd_word:04X}")
    print(f"  RT={rt_address}, TR={tr_bit}, SA={subaddress}, WC={word_count}")
    
    if rt_address == gps_msg.rt and subaddress == gps_msg.sa and word_count == gps_msg.wc:
        print("✅ Message parsing works correctly!")
    else:
        print(f"❌ Message parsing failed: RT={rt_address}!=11, SA={subaddress}!=2, WC={word_count}!=4")


if __name__ == "__main__":
    test_gps_message_data()
