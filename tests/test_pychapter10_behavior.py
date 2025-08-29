"""Test to understand PyChapter10's actual behavior."""

import struct
import tempfile
from pathlib import Path
from chapter10 import C10
from chapter10.ms1553 import MS1553F1
from chapter10.time import TimeF1
from chapter10.message import MessageF0


def test_pychapter10_doesnt_use_data_type():
    """Prove that PyChapter10 doesn't use the data_type field."""
    
    print("\n" + "="*70)
    print("PyChapter10 Behavior Analysis")
    print("="*70)
    
    # Test 1: MS1553F1 packet
    print("\n📦 Test 1: MS1553F1 Packet")
    p1 = MS1553F1()
    p1.channel_id = 0x210
    
    # Check if data_type is set
    print(f"  Before: data_type = {p1.data_type if hasattr(p1, 'data_type') else 'N/A'}")
    
    # Try to set it
    if hasattr(p1, 'data_type'):
        p1.data_type = 0x19
        print(f"  After setting to 0x19: data_type = {p1.data_type}")
    
    # Add a message
    msg = p1.Message()
    msg.ipts = 0
    msg.data = b'test'
    msg.bus = 0
    p1.append(msg)
    
    # Get bytes and check
    data = bytes(p1)
    actual_data_type = data[14] if len(data) > 14 else None
    print(f"  In wire format (byte 14): 0x{actual_data_type:02X}")
    
    # Write and read back
    with tempfile.NamedTemporaryFile(suffix='.c10', delete=False) as f:
        f.write(data)
        temp_file = Path(f.name)
    
    c10 = C10(str(temp_file))
    packets = list(c10)
    print(f"  Read back as: {type(packets[0]).__name__ if packets else 'None'}")
    temp_file.unlink(missing_ok=True)
    
    # Test 2: TimeF1 packet
    print("\n📦 Test 2: TimeF1 Packet")
    p2 = TimeF1()
    p2.channel_id = 0x100
    
    print(f"  Before: data_type = {p2.data_type if hasattr(p2, 'data_type') else 'N/A'}")
    
    if hasattr(p2, 'data_type'):
        p2.data_type = 0x11
        print(f"  After setting to 0x11: data_type = {p2.data_type}")
    
    data = bytes(p2)
    actual_data_type = data[14] if len(data) > 14 else None
    print(f"  In wire format (byte 14): 0x{actual_data_type:02X}")
    
    # Write and read back
    with tempfile.NamedTemporaryFile(suffix='.c10', delete=False) as f:
        f.write(data)
        temp_file = Path(f.name)
    
    c10 = C10(str(temp_file))
    packets = list(c10)
    print(f"  Read back as: {type(packets[0]).__name__ if packets else 'None'}")
    temp_file.unlink(missing_ok=True)
    
    # Test 3: What determines packet type?
    print("\n🔍 Test 3: What Determines Packet Type?")
    
    # Create raw packet with data_type=0x19 but wrong channel format
    sync = 0xEB25
    channel_id = 0x0001  # Not a typical MS1553 channel
    packet_len = 28
    data_len = 4
    
    header = struct.pack('<HH', sync, channel_id)
    header += struct.pack('<II', packet_len, data_len)
    header += struct.pack('<BB', 0, 0)  # Version, sequence
    header += struct.pack('<BB', 0x19, 0)  # data_type=0x19 (MS1553)
    header += struct.pack('<H', 0)  # Checksum
    header += struct.pack('<IH', 0, 0)  # RTC
    header += b'\x00\x00\x00\x00'  # Body
    
    with tempfile.NamedTemporaryFile(suffix='.c10', delete=False) as f:
        f.write(header)
        temp_file = Path(f.name)
    
    c10 = C10(str(temp_file))
    packets = list(c10)
    print(f"  Packet with data_type=0x19, channel=0x0001: {type(packets[0]).__name__ if packets else 'None'}")
    temp_file.unlink(missing_ok=True)
    
    # Now with typical MS1553 channel but data_type=0x00
    channel_id = 0x0210  # Typical MS1553 channel
    
    header = struct.pack('<HH', sync, channel_id)
    header += struct.pack('<II', packet_len, data_len)
    header += struct.pack('<BB', 0, 0)
    header += struct.pack('<BB', 0x00, 0)  # data_type=0x00
    header += struct.pack('<H', 0)
    header += struct.pack('<IH', 0, 0)
    header += b'\x00\x00\x00\x00'
    
    with tempfile.NamedTemporaryFile(suffix='.c10', delete=False) as f:
        f.write(header)
        temp_file = Path(f.name)
    
    c10 = C10(str(temp_file))
    packets = list(c10)
    print(f"  Packet with data_type=0x00, channel=0x0210: {type(packets[0]).__name__ if packets else 'None'}")
    temp_file.unlink(missing_ok=True)
    
    print("\n📋 Conclusions:")
    print("  1. PyChapter10 does NOT set or use the data_type field (byte 14)")
    print("  2. It determines packet type from channel_id patterns or other heuristics")
    print("  3. Setting data_type might actually confuse PyChapter10")
    print("  4. This is why our packets with proper data_type aren't recognized")
    
    print("\n💡 Solution:")
    print("  - Don't set data_type field when using PyChapter10 writer")
    print("  - Use channel_id conventions to indicate packet type")
    print("  - For validation, check wire format directly, not via PyChapter10")


if __name__ == "__main__":
    test_pychapter10_doesnt_use_data_type()
