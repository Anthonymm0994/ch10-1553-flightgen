"""Built-in 1553 timeline inspector (no external dependencies)."""

import json
import struct
from pathlib import Path
from typing import Dict, Any, Generator, Optional, Set, List

try:
    from chapter10 import C10
    from chapter10.ms1553 import MS1553F1
    PYCHAPTER10_AVAILABLE = True
except ImportError:
    PYCHAPTER10_AVAILABLE = False

try:
    from .wire_reader import read_1553_wire
except ImportError:
    from wire_reader import read_1553_wire


def _parse_1553_status_errors(status_word: int) -> List[str]:
    """Parse 1553 status word for common error flags."""
    errors = []
    if status_word & 0x4000: errors.append("MESSAGE_ERROR")
    if status_word & 0x2000: errors.append("INSTRUMENTATION_ERROR")
    if status_word & 0x1000: errors.append("SERVICE_REQUEST")
    if status_word & 0x0800: errors.append("BROADCAST_RECEIVED")
    if status_word & 0x0400: errors.append("BUSY")
    if status_word & 0x0200: errors.append("SUBSYSTEM_FLAG")
    if status_word & 0x0100: errors.append("TERMINAL_FLAG")
    if status_word & 0x0080: errors.append("DYNAMIC_BUS_CONTROL")
    if status_word & 0x0040: errors.append("ACCEPTANCE_ERROR")
    if status_word & 0x0020: errors.append("PARITY_ERROR")
    return errors


def inspect_1553_timeline_pyc10(
    filepath: Path,
    channel: str = 'auto',
    max_messages: int = 100000,
    rt_filter: Optional[int] = None,
    sa_filter: Optional[int] = None,
    errors_only: bool = False
) -> Generator[Dict[str, Any], None, None]:
    """
    Generate 1553 transaction timeline from CH10 file using PyChapter10.
    
    Args:
        filepath: Path to CH10 file
        channel: '1553A', '1553B', or 'auto' (detect)
        max_messages: Maximum messages to process
        rt_filter: Filter by specific RT address (0-31)
        sa_filter: Filter by specific subaddress (0-31)
        errors_only: Only output messages with errors
        
    Yields:
        Timeline entries as dictionaries
    """
    if not PYCHAPTER10_AVAILABLE:
        return
        
    # Map channel names to IDs
    channel_map = {
        '1553A': 0x0200,
        '1553B': 0x0210,
        'auto': None  # Will detect from first packet
    }
    
    target_channel = channel_map.get(channel)
    if target_channel is None and channel != 'auto':
        raise ValueError(f"Invalid channel: '{channel}'. Must be 'A' or 'B'")
    
    c10 = C10(str(filepath))
    msg_count = 0
    start_time_ns = None
    detected_channels = {}
    
    try:
        for packet in c10:
            if not isinstance(packet, MS1553F1):
                continue
                
            # Track detected channels
            channel_id = packet.channel_id
            if channel_id in [0x0200, 0x0210]:
                if channel_id not in detected_channels:
                    detected_channels[channel_id] = 0
                    
            # Auto-detect channel if needed
            if channel == 'auto' and target_channel is None:
                if channel_id in [0x0200, 0x0210]:
                    target_channel = channel_id
            
            # Skip if not target channel
            if target_channel and packet.channel_id != target_channel:
                continue
            
            # Process messages in packet
            for msg in packet:
                # Extract message fields from data
                # PyChapter10 doesn't parse these, we need to extract from data bytes
                if len(msg.data) >= 4:
                    # First word is command word (little-endian)
                    command_word = struct.unpack('<H', msg.data[0:2])[0]
                    status_word = struct.unpack('<H', msg.data[2:4])[0] if len(msg.data) >= 4 else 0
                    
                    # Extract fields from command word
                    rt_address = (command_word >> 11) & 0x1F
                    tr_bit = (command_word >> 10) & 0x01
                    subaddress = (command_word >> 5) & 0x1F
                    word_count = command_word & 0x1F
                    if word_count == 0:
                        word_count = 32
                    
                    status = status_word
                else:
                    rt_address = 0
                    subaddress = 0
                    tr_bit = 0
                    word_count = 0
                    status = 0
                
                bus = getattr(msg, 'bus', 0)  # 0=A, 1=B
                
                # Apply filters
                if rt_filter is not None and rt_address != rt_filter:
                    continue
                if sa_filter is not None and subaddress != sa_filter:
                    continue
                
                # Parse error flags from status
                errors = _parse_1553_status_errors(status)
                
                # Skip if errors_only and no errors
                if errors_only and not errors:
                    continue
                
                # Get timestamp
                ipts_ns = getattr(msg, 'ipts', 0) * 1_000_000_000
                if hasattr(msg, 'ipts_ns'):
                    ipts_ns = msg.ipts_ns
                
                # Set start time on first message
                if start_time_ns is None:
                    start_time_ns = ipts_ns
                
                # Calculate relative time (ensure non-negative)
                t_rel_ms = max(0, (ipts_ns - start_time_ns) / 1_000_000)
                
                # Count for this channel
                if packet.channel_id in detected_channels:
                    detected_channels[packet.channel_id] += 1
                
                yield {
                    'ipts_ns': ipts_ns,
                    't_rel_ms': round(t_rel_ms, 3),
                    'bus': 'A' if bus == 0 else 'B',
                    'rt': rt_address,
                    'sa': subaddress,
                    'tr': 'BC2RT' if tr_bit == 0 else 'RT2BC',
                    'wc': word_count,
                    'status': status,
                    'errors': errors
                }
                
                msg_count += 1
                if msg_count >= max_messages:
                    return
                    
    finally:
        # PyChapter10 C10 object doesn't have close()
        pass
    
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


def inspect_1553_timeline(
    filepath: Path,
    channel: str = 'auto',
    max_messages: int = 100000,
    rt_filter: Optional[int] = None,
    sa_filter: Optional[int] = None,
    errors_only: bool = False,
    reader: str = 'auto'
) -> Generator[Dict[str, Any], None, None]:
    """
    Generate 1553 transaction timeline from CH10 file.
    
    Args:
        filepath: Path to CH10 file
        channel: '1553A', '1553B', or 'auto' (detect)
        max_messages: Maximum messages to process
        rt_filter: Filter by specific RT address (0-31)
        sa_filter: Filter by specific subaddress (0-31)
        errors_only: Only output messages with errors
        reader: 'auto', 'pyc10', or 'wire' reader to use
        
    Yields:
        Timeline entries as dictionaries
    """
    if reader == 'wire':
        yield from read_1553_wire(filepath, channel, max_messages, rt_filter, sa_filter, errors_only)
        print("Reader: wire")
    elif reader == 'pyc10':
        if not PYCHAPTER10_AVAILABLE:
            print("PyChapter10 not available, falling back to wire reader")
            yield from read_1553_wire(filepath, channel, max_messages, rt_filter, sa_filter, errors_only)
            print("Reader: wire (fallback)")
        else:
            print("WARNING: PyChapter10 has known parsing issues - messages show wc:0, rt:0, etc.")
            print("Consider using 'wire' reader for accurate data")
            yield from inspect_1553_timeline_pyc10(filepath, channel, max_messages, rt_filter, sa_filter, errors_only)
            print("Reader: pyc10")
    else:  # auto mode
        # Use wire reader by default since PyChapter10 has parsing issues
        # PyChapter10 shows empty messages (wc: 0, rt: 0, etc.)
        yield from read_1553_wire(filepath, channel, max_messages, rt_filter, sa_filter, errors_only)
        print("Reader: wire (default - PyChapter10 has parsing issues)")


def write_timeline(
    filepath: Path,
    output_path: Path,
    channel: str = 'auto',
    max_messages: int = 100000,
    rt_filter: Optional[int] = None,
    sa_filter: Optional[int] = None,
    errors_only: bool = False,
    reader: str = 'auto'
) -> int:
    """
    Write timeline to JSONL file.
    
    Returns:
        Number of messages written
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    count = 0
    with open(output_path, 'w') as f:
        for transaction in inspect_1553_timeline(
            filepath, channel, max_messages, rt_filter, sa_filter, errors_only, reader
        ):
            f.write(json.dumps(transaction) + '\n')
            count += 1
    
    return count