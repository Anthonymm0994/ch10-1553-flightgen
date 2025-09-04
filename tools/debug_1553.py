#!/usr/bin/env python3
"""Debug script to find 1553 packets in CH10 file."""

import struct
from ch10gen.wire_reader import read_packet_header, parse_1553_csdw, parse_1553_message_pyc10

def find_1553_packets():
    """Find 1553 packets in the CH10 file."""
    with open('test_messages.ch10', 'rb') as f:
        packet_num = 0
        rt_values = set()
        sa_values = set()
        
        while packet_num < 1000:  # Check more packets
            packet_num += 1
            header = read_packet_header(f)
            if not header:
                break
            
            if header['data_type'] == 0x19:
                # Read the data
                data = f.read(header['data_len'])
                
                # Parse CSDW
                csdw_info = parse_1553_csdw(data)
                msg_count = csdw_info['msg_count']
                
                # Parse messages
                offset = csdw_info['csdw_size']
                for i in range(msg_count):
                    msg = parse_1553_message_pyc10(data, offset, i)
                    if msg:
                        rt_values.add(msg["rt"])
                        sa_values.add(msg["sa"])
                        if msg["rt"] == 11:  # GPS_5HZ
                            print(f'Found GPS message in packet #{packet_num}: RT={msg["rt"]}, SA={msg["sa"]}, TR={msg["tr"]}, WC={msg["wc"]}')
                    offset += 26  # Fixed message size
                
                if packet_num % 100 == 0:
                    print(f'Checked {packet_num} packets, RT values: {sorted(rt_values)}, SA values: {sorted(sa_values)}')
            else:
                # Skip non-1553 packet
                f.seek(header['packet_len'] - header['header_size'], 1)
        
        print(f'\nFinal results:')
        print(f'RT values found: {sorted(rt_values)}')
        print(f'SA values found: {sorted(sa_values)}')

if __name__ == "__main__":
    find_1553_packets()
