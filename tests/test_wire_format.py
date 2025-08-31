"""Test MS1553 wire format to prove messages exist (or don't)."""

import pytest
import struct
import tempfile
from pathlib import Path
from contextlib import suppress


def create_raw_ms1553_packet():
    """Create a raw MS1553F1 packet with known structure."""
    
    # IRIG-106 Packet Header (24 bytes)
    sync = 0xEB25
    channel_id = 0x0210
    data_type = 0x19  # MS1553 F1
    
    # Create MS1553F1 packet body
    # CSDW (Channel Specific Data Word) - 4 bytes
    message_count = 1
    format_version = 0
    ttb_present = 0
    csdw = message_count | (format_version << 16) | (ttb_present << 20)
    
    # MS1553 Message structure (no TTB)
    # Intra-message header (8 bytes)
    block_status = 0x0000  # No errors
    gap_time = 100  # 100 * 0.1 us = 10 us
    msg_length = 8  # 4 words * 2 bytes = 8 bytes
    reserved = 0x0000
    
    # Message data (8 bytes)
    cmd_word = (5 << 11) | (1 << 10) | (1 << 5) | 2  # RT=5, Rx, SA=1, WC=2
    status_word = (5 << 11)  # RT=5, no flags
    data_word1 = 0x1234
    data_word2 = 0x5678
    
    # Build packet body
    body = struct.pack('<I', csdw)  # CSDW
    body += struct.pack('<HHHH', block_status, gap_time, msg_length, reserved)  # Message header
    body += struct.pack('<HHHH', cmd_word, status_word, data_word1, data_word2)  # Message data
    
    # Calculate lengths
    data_len = len(body)
    packet_len = 24 + data_len  # Header + body
    
    # Build header
    header = struct.pack('<HH', sync, channel_id)
    header += struct.pack('<II', packet_len, data_len)
    header += struct.pack('<BB', 0, 0)  # Data version, sequence
    header += struct.pack('<BB', data_type, 0)  # Data type at byte 14, flags at byte 15
    header += struct.pack('<H', 0)  # Header checksum
    header += struct.pack('<IH', 0, 0)  # RTC (6 bytes total)
    
    return header + body


def analyze_packet(data):
    """Analyze packet structure and extract key fields."""
    analysis = {}
    
    # Parse header
    analysis['sync'] = struct.unpack('<H', data[0:2])[0]
    analysis['channel_id'] = struct.unpack('<H', data[2:4])[0]
    analysis['packet_len'] = struct.unpack('<I', data[4:8])[0]
    analysis['data_len'] = struct.unpack('<I', data[8:12])[0]
    analysis['data_type'] = data[14]
    analysis['flags'] = data[15]
    
    # Parse MS1553 CSDW if this is 0x19
    if analysis['data_type'] == 0x19:
        csdw = struct.unpack('<I', data[24:28])[0]
        analysis['message_count'] = csdw & 0xFFFF
        
        # Parse first message header
        if analysis['message_count'] > 0:
            msg_offset = 28
            analysis['block_status'] = struct.unpack('<H', data[msg_offset:msg_offset+2])[0]
            analysis['gap_time'] = struct.unpack('<H', data[msg_offset+2:msg_offset+4])[0]
            analysis['msg_length'] = struct.unpack('<H', data[msg_offset+4:msg_offset+6])[0]
            
            # Parse command word
            cmd_offset = msg_offset + 8
            if len(data) > cmd_offset + 2:
                cmd_word = struct.unpack('<H', data[cmd_offset:cmd_offset+2])[0]
                analysis['rt'] = (cmd_word >> 11) & 0x1F
                analysis['tr'] = (cmd_word >> 10) & 0x01
                analysis['sa'] = (cmd_word >> 5) & 0x1F
                analysis['wc'] = cmd_word & 0x1F
                if analysis['wc'] == 0:
                    analysis['wc'] = 32
    
    return analysis


def test_wire_format_invariants():
    """Test that our MS1553F1 packets meet wire format invariants."""
    
    # Create raw packet
    packet_data = create_raw_ms1553_packet()
    
    # Analyze it
    analysis = analyze_packet(packet_data)
    
    print("\n📊 Wire Format Analysis:")
    print(f"  Sync: {analysis['sync']:04X} (expect EB25)")
    print(f"  Data Type: 0x{analysis['data_type']:02X} (expect 0x19)")
    print(f"  Packet Len: {analysis['packet_len']} bytes")
    print(f"  Data Len: {analysis['data_len']} bytes")
    
    # Invariant 1: Sync pattern
    assert analysis['sync'] == 0xEB25, f"Invalid sync: {analysis['sync']:04X}"
    
    # Invariant 2: Data type correct
    assert analysis['data_type'] == 0x19, f"Wrong data_type: 0x{analysis['data_type']:02X}"
    
    # Invariant 3: Length consistency
    assert analysis['packet_len'] == 24 + analysis['data_len'], \
           f"packet_len ({analysis['packet_len']}) != header + data_len ({24 + analysis['data_len']})"
    
    # Invariant 4: Message count
    assert analysis['message_count'] == 1, f"Expected 1 message, got {analysis['message_count']}"
    
    # Invariant 5: Message length word-aligned
    assert analysis['msg_length'] % 2 == 0, f"Message length {analysis['msg_length']} not word-aligned"
    
    # Invariant 6: Message content correct
    assert analysis['rt'] == 5, f"RT mismatch: {analysis['rt']}"
    assert analysis['tr'] == 1, f"TR mismatch: {analysis['tr']}"
    assert analysis['sa'] == 1, f"SA mismatch: {analysis['sa']}"
    assert analysis['wc'] == 2, f"WC mismatch: {analysis['wc']}"
    
    print("\n✅ All wire format invariants passed")
    
    # Write to file and verify it's readable
    with tempfile.NamedTemporaryFile(suffix='.c10', delete=False) as f:
        output_file = Path(f.name)
        f.write(packet_data)
    
    try:
        # Try to read with PyChapter10
        from chapter10 import C10
        
        c10 = C10(str(output_file))
        packets = list(c10)
        
        print(f"\n📖 PyChapter10 Read Results:")
        print(f"  Packets found: {len(packets)}")
        
        if packets:
            p = packets[0]
            print(f"  First packet type: {type(p).__name__}")
            print(f"  Has data_type: {hasattr(p, 'data_type')}")
            if hasattr(p, 'data_type'):
                print(f"  data_type value: 0x{p.data_type:02X}")
            
            # Try to iterate messages
            if hasattr(p, '__iter__'):
                messages = list(p)
                print(f"  Messages found via iteration: {len(messages)}")
            else:
                print(f"  Cannot iterate messages")
        
        # This is the key test: wire format is correct, but can PyChapter10 parse it?
        if len(packets) == 0:
            pytest.fail("PyChapter10 cannot read our correctly formatted packet")
        elif packets and hasattr(packets[0], 'data_type') and packets[0].data_type != 0x19:
            pytest.fail(f"PyChapter10 misidentified packet type: 0x{packets[0].data_type:02X}")
    
    finally:
        with suppress(FileNotFoundError, PermissionError):
            output_file.unlink()


def test_compare_with_pychapter10_writer():
    """Compare our raw packet with PyChapter10's writer."""
    from chapter10.ms1553 import MS1553F1
    
    # Create packet with PyChapter10
    p = MS1553F1()
    p.channel_id = 0x0210
    
    # Try different ways to set data_type
    if hasattr(p, 'packet_type'):
        p.packet_type = 0x19
    if hasattr(p, 'data_type'):
        p.data_type = 0x19
    
    # Create a message
    msg = p.Message()
    msg.ipts = 0
    msg.data = struct.pack('<HHHH', 0x2822, 0x2800, 0x1234, 0x5678)
    msg.bus = 0
    
    p.append(msg)
    
    # Get bytes
    pychapter10_bytes = bytes(p)
    
    # Analyze PyChapter10's packet
    analysis = analyze_packet(pychapter10_bytes)
    
    print("\n🔬 PyChapter10 Writer Analysis:")
    print(f"  Data Type at byte 14: 0x{analysis['data_type']:02X}")
    print(f"  Flags at byte 15: 0x{analysis['flags']:02X}")
    print(f"  Message Count: {analysis.get('message_count', 'N/A')}")
    
    # Compare with our raw packet
    our_packet = create_raw_ms1553_packet()
    our_analysis = analyze_packet(our_packet)
    
    print("\n📊 Comparison:")
    print(f"  Our data_type: 0x{our_analysis['data_type']:02X}")
    print(f"  PyChapter10 data_type: 0x{analysis['data_type']:02X}")
    print(f"  Match: {our_analysis['data_type'] == analysis['data_type']}")


def test_self_diagnosis():
    """Self-diagnosing failure output."""
    
    packet = create_raw_ms1553_packet()
    analysis = analyze_packet(packet)
    
    # Concise diagnostic output (6 lines max)
    print("\n🔍 MS1553 Packet Diagnostic:")
    print(f"  Header: type=0x{analysis['data_type']:02X}, ch={analysis['channel_id']:04X}, len={analysis['packet_len']}")
    print(f"  IPH: msg_count={analysis.get('message_count', 'N/A')}, msg_len={analysis.get('msg_length', 'N/A')}")
    print(f"  Msg1: RT={analysis.get('rt', 'N/A')}, SA={analysis.get('sa', 'N/A')}, WC={analysis.get('wc', 'N/A')}")
    print(f"  Hex (32B): {' '.join(f'{b:02X}' for b in packet[:32])}")
    
    # This format makes failures immediately debuggable in CI logs


if __name__ == "__main__":
    test_wire_format_invariants()
    print("\n" + "="*60)
    test_compare_with_pychapter10_writer()
    print("\n" + "="*60)
    test_self_diagnosis()
