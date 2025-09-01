#!/usr/bin/env python3
"""Debug script to test wire reader parsing of GPS messages."""

import tempfile
import struct
from pathlib import Path
from ch10gen.icd import load_icd
from ch10gen.schedule import build_schedule_from_icd
from ch10gen.ch10_writer import write_ch10_file
from ch10gen.wire_reader import read_1553_wire, parse_1553_message_pyc10, parse_1553_csdw


def debug_wire_reader():
    """Debug the wire reader to see why GPS messages aren't being parsed."""
    print("=== Wire Reader Debug ===")
    
    # Load test ICD
    icd = load_icd(Path("icd/test_icd.yaml"))
    
    # Find GPS message
    gps_msg = None
    for msg in icd.messages:
        if msg.name == 'GPS_5HZ':
            gps_msg = msg
            break
    
    print(f"✅ GPS message: {gps_msg.name}")
    print(f"  RT={gps_msg.rt}, SA={gps_msg.sa}, WC={gps_msg.wc}")
    print(f"  Words: {len(gps_msg.words)}")
    for word in gps_msg.words:
        print(f"    {word.name}: encode={word.encode}, word_order={word.word_order}")
    
    # Generate a short CH10 file
    schedule = build_schedule_from_icd(icd, duration_s=1.0)  # 1 second
    
    # Find GPS messages in schedule
    gps_schedule = [msg for msg in schedule.messages if msg.message.rt == 11 and msg.message.sa == 2]
    print(f"\n✅ Schedule has {len(gps_schedule)} GPS messages")
    
    scenario = {'duration_s': 1, 'name': 'debug_wire'}
    
    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = Path(tmpdir) / "debug_wire.ch10"
        
        # Generate CH10 file
        stats = write_ch10_file(
            output_path=output_file,
            scenario=scenario,
            icd=icd,
            seed=42,
            writer_backend='irig106'
        )
        
        print(f"✅ CH10 file generated: {stats}")
        
        # Read raw file to find GPS messages
        with open(output_file, 'rb') as f:
            data = f.read()
        
        # Look for RT=11 patterns
        rt_11_pattern = b'\x00\x58'  # RT=11 in little-endian
        rt_11_positions = []
        pos = 0
        while True:
            pos = data.find(rt_11_pattern, pos)
            if pos == -1:
                break
            rt_11_positions.append(pos)
            pos += 1
        
        print(f"✅ Found {len(rt_11_positions)} RT=11 patterns in file")
        
        # Try to parse each RT=11 message
        for i, pos in enumerate(rt_11_positions[:3]):  # Check first 3
            print(f"\n🔍 Analyzing RT=11 pattern #{i} at position {pos}")
            
            # Look for the packet containing this message
            # Find the packet header before this position
            packet_start = pos
            while packet_start > 0 and data[packet_start:packet_start+2] != b'\x25\xEB':
                packet_start -= 1
            
            if packet_start > 0:
                print(f"  Found packet header at position {packet_start}")
                
                # Read packet header
                header_data = data[packet_start:packet_start+24]
                if len(header_data) == 24:
                    sync = struct.unpack('<H', header_data[0:2])[0]
                    channel_id = struct.unpack('<H', header_data[2:4])[0]
                    packet_len = struct.unpack('<I', header_data[4:8])[0]
                    data_len = struct.unpack('<I', header_data[8:12])[0]
                    data_type = header_data[15]
                    
                    print(f"  Packet: sync=0x{sync:04X}, channel=0x{channel_id:04X}, len={packet_len}, data_len={data_len}, type=0x{data_type:02X}")
                    
                    if data_type == 0x19:  # 1553 packet
                        # Read packet data
                        packet_data = data[packet_start+24:packet_start+24+data_len]
                        print(f"  Packet data length: {len(packet_data)}")
                        print(f"  Packet data (hex): {packet_data.hex()}")
                        
                        # Parse CSDW
                        csdw_info = parse_1553_csdw(packet_data)
                        print(f"  CSDW: {csdw_info}")
                        
                        # Try to parse messages
                        offset = csdw_info['csdw_size']
                        for msg_idx in range(csdw_info['msg_count']):
                            print(f"  Trying to parse message {msg_idx} at offset {offset}")
                            
                            # Check if we have enough data for minimum message
                            if offset + 18 > len(packet_data):
                                print(f"    ❌ Not enough data: need at least 18 bytes, have {len(packet_data) - offset}")
                                break
                            
                            # Show the message data (first 18 bytes for header + command + status)
                            msg_data = packet_data[offset:offset+18]
                            print(f"    Message data (hex): {msg_data.hex()}")
                            
                            # Parse command word
                            cmd_word = struct.unpack('<H', msg_data[14:16])[0]
                            rt_address = (cmd_word >> 11) & 0x1F
                            tr_bit = (cmd_word >> 10) & 0x01
                            subaddress = (cmd_word >> 5) & 0x1F
                            word_count = cmd_word & 0x1F
                            if word_count == 0:
                                word_count = 32
                            
                            print(f"    Command word: 0x{cmd_word:04X}")
                            print(f"    RT={rt_address}, TR={tr_bit}, SA={subaddress}, WC={word_count}")
                            
                            # Check if RT is valid
                            if rt_address < 1 or rt_address > 31:
                                print(f"    ❌ Invalid RT address: {rt_address}")
                                break
                            
                            msg = parse_1553_message_pyc10(packet_data, offset, msg_idx)
                            if msg:
                                print(f"    ✅ Message parsed: RT={msg['rt']}, SA={msg['sa']}, TR={msg['tr']}, WC={msg['wc']}")
                                if msg['rt'] == 11:
                                    print(f"    ✅ Found GPS message!")
                            else:
                                print(f"    ❌ Failed to parse message")
                            # Use actual message size from parsing result
                            if msg:
                                offset += msg['size']
                            else:
                                # Fallback to minimum size if parsing failed
                                offset += 18
        
        # Now try the wire reader
        print(f"\n🔄 Testing wire reader...")
        messages = list(read_1553_wire(output_file, max_messages=100))
        
        rt_values = set(msg['rt'] for msg in messages)
        print(f"❌ Wire reader found RT values: {sorted(rt_values)}")
        
        # Count GPS messages
        gps_count = sum(1 for msg in messages if msg['rt'] == 11 and msg['sa'] == 2)
        print(f"❌ Wire reader found {gps_count} GPS messages")


if __name__ == "__main__":
    debug_wire_reader()
