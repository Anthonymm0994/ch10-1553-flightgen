"""Export CH10 data to CSV and other formats."""

import csv
import json
import struct
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from chapter10 import C10
from chapter10.ms1553 import MS1553F1

try:
    from .icd import ICDDefinition, MessageDefinition
except ImportError:
    from icd import ICDDefinition, MessageDefinition


def export_raw_1553_csv(ch10_file: Path, output_file: Path) -> int:
    """Export raw 1553 messages to CSV.
    
    Args:
        ch10_file: Input CH10 file
        output_file: Output CSV file
        
    Returns:
        Number of messages exported
    """
    c10 = C10(str(ch10_file))
    message_count = 0
    
    with open(output_file, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        
        # Write header
        writer.writerow([
            'packet_time_us', 'message_time_ns', 'channel_id',
            'bus', 'rt', 'tr', 'sa', 'wc',
            'cmd_word', 'status_word', 'data_words'
        ])
        
        # Process packets
        for packet in c10:
            if isinstance(packet, MS1553F1):
                packet_time_us = packet.rtc if hasattr(packet, 'rtc') else 0
                channel_id = packet.channel_id if hasattr(packet, 'channel_id') else 0
                
                # Try to iterate messages
                try:
                    for msg in packet:
                        if hasattr(msg, 'data') and msg.data:
                            # Parse message data
                            if len(msg.data) >= 4:
                                cmd_word = struct.unpack('<H', msg.data[0:2])[0]
                                status_word = struct.unpack('<H', msg.data[2:4])[0]
                                
                                # Extract RT/TR/SA/WC from command word
                                rt = (cmd_word >> 11) & 0x1F
                                tr = (cmd_word >> 10) & 0x01
                                sa = (cmd_word >> 5) & 0x1F
                                wc = cmd_word & 0x1F
                                if wc == 0:
                                    wc = 32
                                
                                # Extract data words
                                data_words = []
                                for i in range(4, len(msg.data), 2):
                                    if i + 1 < len(msg.data):
                                        word = struct.unpack('<H', msg.data[i:i+2])[0]
                                        data_words.append(f'{word:04X}')
                                
                                # Write row
                                writer.writerow([
                                    packet_time_us,
                                    msg.ipts if hasattr(msg, 'ipts') else 0,
                                    f'{channel_id:04X}',
                                    msg.bus if hasattr(msg, 'bus') else 0,
                                    rt, tr, sa, wc,
                                    f'{cmd_word:04X}',
                                    f'{status_word:04X}',
                                    ' '.join(data_words)
                                ])
                                
                                message_count += 1
                except:
                    # If can't iterate, try to parse packet body directly
                    pass
    
    return message_count


def export_decoded_csv(ch10_file: Path, output_file: Path, icd: ICDDefinition) -> int:
    """Export decoded 1553 messages to CSV using ICD.
    
    Args:
        ch10_file: Input CH10 file
        output_file: Output CSV file
        icd: ICD definition for decoding
        
    Returns:
        Number of messages exported
    """
    # Build RT/SA to message mapping
    message_map = {}
    for msg_def in icd.messages:
        key = (msg_def.rt, msg_def.sa, 1 if msg_def.tr == 'RT2BC' else 0)
        message_map[key] = msg_def
    
    c10 = C10(str(ch10_file))
    message_count = 0
    
    with open(output_file, 'w', newline='') as csvfile:
        # Determine all unique field names
        field_names = set()
        field_names.update(['time_us', 'message_name', 'rt', 'sa', 'tr'])
        
        for msg_def in icd.messages:
            for word_def in msg_def.words:
                field_names.add(word_def.name)
        
        writer = csv.DictWriter(csvfile, fieldnames=sorted(field_names))
        writer.writeheader()
        
        # Process packets
        for packet in c10:
            if isinstance(packet, MS1553F1):
                packet_time_us = packet.rtc if hasattr(packet, 'rtc') else 0
                
                try:
                    for msg in packet:
                        if hasattr(msg, 'data') and msg.data and len(msg.data) >= 4:
                            # Parse command word
                            cmd_word = struct.unpack('<H', msg.data[0:2])[0]
                            rt = (cmd_word >> 11) & 0x1F
                            tr = (cmd_word >> 10) & 0x01
                            sa = (cmd_word >> 5) & 0x1F
                            
                            # Find message definition
                            key = (rt, sa, tr)
                            if key in message_map:
                                msg_def = message_map[key]
                                
                                # Decode data words
                                row = {
                                    'time_us': packet_time_us,
                                    'message_name': msg_def.name,
                                    'rt': rt,
                                    'sa': sa,
                                    'tr': tr
                                }
                                
                                # Decode each word according to ICD
                                word_idx = 0
                                data_idx = 4  # Skip cmd and status words
                                
                                for word_def in msg_def.words:
                                    if data_idx + 1 < len(msg.data):
                                        word_value = struct.unpack('<H', msg.data[data_idx:data_idx+2])[0]
                                        
                                        # Decode based on encoding type
                                        if word_def.encode == 'bnr16':
                                            # BNR decoding
                                            if word_value & 0x8000:
                                                # Negative
                                                decoded = -(65536 - word_value) * (word_def.scale or 1.0)
                                            else:
                                                decoded = word_value * (word_def.scale or 1.0)
                                            decoded += word_def.offset or 0.0
                                            row[word_def.name] = decoded
                                        else:
                                            # Raw value
                                            row[word_def.name] = word_value
                                        
                                        data_idx += 2
                                        word_idx += 1
                                
                                writer.writerow(row)
                                message_count += 1
                except:
                    pass
    
    return message_count


def export_metrics_json(stats: Dict[str, Any], output_file: Optional[Path] = None) -> Dict[str, Any]:
    """Export metrics to JSON.
    
    Args:
        stats: Basic CH10 statistics
        output_file: Optional output file path
        
    Returns:
        Metrics dictionary
    """
    metrics = {
        'timestamp': datetime.utcnow().isoformat(),
        'ch10_stats': stats
    }
    
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(metrics, f, indent=2)
    
    return metrics
