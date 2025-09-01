"""Wire-level Chapter 10 MS1553F1 packet reader."""

import struct
from pathlib import Path
from typing import Generator, Dict, Any, Optional, BinaryIO


def read_packet_header(f: BinaryIO) -> Optional[Dict[str, Any]]:
    """Read a Chapter 10 packet header (24 bytes)."""
    header = f.read(24)
    if len(header) < 24:
        return None
    
    # Parse packet header
    sync = struct.unpack('<H', header[0:2])[0]
    if sync != 0xEB25:
        return None
    
    channel_id = struct.unpack('<H', header[2:4])[0]
    packet_len = struct.unpack('<I', header[4:8])[0]
    data_len = struct.unpack('<I', header[8:12])[0]
    
    # The irig106 library seems to put data type at byte 15
    # Standard says it should be at byte 23, but we'll check both
    data_type = header[15]  # irig106 library position
    if data_type == 0:
        data_type = header[23]  # Standard position
    
    # For MS1553F1 packets from irig106 writer, data type appears at byte 15
    # This is non-standard but we need to handle it
    
    rtc_low = struct.unpack('<I', header[12:16])[0]
    rtc_high = struct.unpack('<H', header[16:18])[0]
    rtc = (rtc_high << 32) | rtc_low
    
    return {
        'channel_id': channel_id,
        'packet_len': packet_len,
        'data_len': data_len,
        'data_type': data_type,
        'rtc': rtc,
        'header_size': 24
    }


def parse_1553_csdw(data: bytes) -> Dict[str, Any]:
    """Parse MS1553F1 Channel Specific Data Word."""
    if len(data) < 4:
        return {'msg_count': 0}
    
    csdw = struct.unpack('<I', data[0:4])[0]
    msg_count = csdw & 0xFFFF  # Lower 16 bits
    return {'msg_count': msg_count, 'csdw_size': 4}


def parse_1553_message_pyc10(data: bytes, offset: int, msg_index: int) -> Optional[Dict[str, Any]]:
    """Parse a single 1553 message from PyChapter10 format.
    
    PyChapter10 MS1553F1 format (observed):
    - 14 bytes header (IPTS and other fields)
    - Command word (2 bytes)
    - Status word (2 bytes)
    - Data words (variable based on WC)
    """
    # Minimum message size (header + command + status)
    MIN_MSG_SIZE = 18
    
    if offset + MIN_MSG_SIZE > len(data):
        return None
    
    # Extract command word at offset + 14
    if offset + 16 > len(data):
        return None
    
    cmd_word = struct.unpack('<H', data[offset+14:offset+16])[0]
    
    # Extract fields from command word
    rt_address = (cmd_word >> 11) & 0x1F
    tr_bit = (cmd_word >> 10) & 0x01
    subaddress = (cmd_word >> 5) & 0x1F
    word_count = cmd_word & 0x1F
    if word_count == 0:
        word_count = 32
    
    # Skip if not a valid RT (1-31)
    if rt_address < 1 or rt_address > 31:
        return None
    
    # Calculate actual message size based on word count
    # 14 bytes header + 2 bytes command + 2 bytes status + (WC * 2) bytes data
    actual_msg_size = 18 + (word_count * 2)
    
    # Check if we have enough data for the full message
    if offset + actual_msg_size > len(data):
        return None
    
    # Status word
    status_word = 0
    if offset + 18 <= len(data):
        status_word = struct.unpack('<H', data[offset+16:offset+18])[0]
    
    # Calculate IPTS from message index
    ipts = msg_index * 40000  # 40us between messages
    
    return {
        'ipts': ipts,
        'bus': 'A',  # PyChapter10 doesn't specify bus in message
        'rt': rt_address,
        'sa': subaddress,
        'tr': 'RT2BC' if tr_bit else 'BC2RT',
        'wc': word_count,
        'status': status_word,
        'errors': [],
        'size': actual_msg_size
    }


def read_1553_wire(
    filepath: Path,
    channel: str = 'auto',
    max_messages: int = 100000,
    rt_filter: Optional[int] = None,
    sa_filter: Optional[int] = None,
    errors_only: bool = False
) -> Generator[Dict[str, Any], None, None]:
    """Read 1553 messages directly from wire format."""
    
    # Channel mapping
    channel_map = {
        '1553A': 0x0200,
        '1553B': 0x0210,
        'auto': None
    }
    
    target_channel = channel_map.get(channel)
    if target_channel is None and channel != 'auto':
        if channel not in ['A', 'B']:
            raise ValueError(f"Invalid channel: '{channel}'. Must be 'A' or 'B'")
    
    msg_count = 0
    start_time_ns = None
    detected_channels = {}
    
    with open(filepath, 'rb') as f:
        packet_num = 0
        while msg_count < max_messages:
            packet_num += 1
            
            # Read packet header
            header = read_packet_header(f)
            if not header:
                break
            
            # Check if MS1553F1 packet (data type 0x19)
            if header['data_type'] != 0x19:
                # Skip non-1553 packet
                f.seek(header['packet_len'] - header['header_size'], 1)
                continue
            
            # Track detected channels
            channel_id = header['channel_id']
            if channel_id in [0x0200, 0x0210]:
                if channel_id not in detected_channels:
                    detected_channels[channel_id] = 0
            
            # Auto-detect channel if needed
            if channel == 'auto' and target_channel is None:
                if channel_id in [0x0200, 0x0210]:
                    target_channel = channel_id
            
            # Skip if not target channel
            if target_channel and channel_id != target_channel:
                f.seek(header['packet_len'] - header['header_size'], 1)
                continue
            
            # Read packet data
            data_to_read = header['data_len']
            packet_data = f.read(data_to_read)
            
            if len(packet_data) < data_to_read:
                break
            
            # Parse CSDW
            csdw_info = parse_1553_csdw(packet_data)
            msg_count_in_packet = csdw_info['msg_count']
            
            # Parse messages using PyChapter10 format
            offset = csdw_info['csdw_size']
            parsed_in_packet = 0
            
            for i in range(msg_count_in_packet):
                if msg_count >= max_messages:
                    return
                
                msg = parse_1553_message_pyc10(packet_data, offset, msg_count)
                if not msg:
                    # Skip this message block (use minimum size)
                    offset += 18
                    continue
                
                # Apply filters
                if rt_filter is not None and msg['rt'] != rt_filter:
                    offset += msg['size']
                    continue
                if sa_filter is not None and msg['sa'] != sa_filter:
                    offset += msg['size']
                    continue
                if errors_only and not msg['errors']:
                    offset += msg['size']
                    continue
                
                # Set start time
                if start_time_ns is None:
                    start_time_ns = msg['ipts']
                
                # Count for this channel
                if channel_id in detected_channels:
                    detected_channels[channel_id] += 1
                
                # Yield message
                yield {
                    'ipts_ns': msg['ipts'],
                    't_rel_ms': (msg['ipts'] - start_time_ns) / 1_000_000,
                    'bus': msg['bus'],
                    'rt': msg['rt'],
                    'sa': msg['sa'],
                    'tr': msg['tr'],
                    'wc': msg['wc'],
                    'status': msg['status'],
                    'errors': msg['errors']
                }
                
                msg_count += 1
                parsed_in_packet += 1
                offset += msg['size']
            
            # Skip any padding
            remaining = header['packet_len'] - header['header_size'] - data_to_read
            if remaining > 0:
                f.seek(remaining, 1)
    
    # Print channel detection info if auto mode
    if channel == 'auto' and detected_channels:
        channels_str = ', '.join(
            f"{'A' if ch == 0x0200 else 'B'}({hex(ch)})={count} msgs"
            for ch, count in detected_channels.items()
        )
        print(f"Found 1553 channels: {channels_str}")
        if target_channel:
            ch_name = 'A' if target_channel == 0x0200 else 'B'
            print(f"Using: {ch_name} (override with --channel 1553{'B' if ch_name == 'A' else 'A'})")