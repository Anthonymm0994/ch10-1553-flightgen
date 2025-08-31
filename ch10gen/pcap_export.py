"""PCAP export for 1553 data (minimal implementation using stdlib only)."""

import struct
import json
from pathlib import Path
from typing import BinaryIO
try:
    from .inspector import inspect_1553_timeline
except ImportError:
    from inspector import inspect_1553_timeline


# PCAP constants
PCAP_MAGIC = 0xa1b2c3d4
PCAP_VERSION_MAJOR = 2
PCAP_VERSION_MINOR = 4
PCAP_THISZONE = 0
PCAP_SIGFIGS = 0
PCAP_SNAPLEN = 65535
PCAP_NETWORK = 228  # DLT_USER0 for custom encapsulation

# UDP constants
UDP_PORT = 15553  # Custom port for 1553 data (must be < 65536)


def write_pcap_header(f: BinaryIO):
    """Write PCAP global header."""
    f.write(struct.pack(
        '<IHHIIII',
        PCAP_MAGIC,
        PCAP_VERSION_MAJOR,
        PCAP_VERSION_MINOR,
        PCAP_THISZONE,
        PCAP_SIGFIGS,
        PCAP_SNAPLEN,
        PCAP_NETWORK
    ))


def write_pcap_packet(f: BinaryIO, timestamp_us: int, data: bytes):
    """
    Write a PCAP packet record.
    
    Args:
        f: File handle
        timestamp_us: Timestamp in microseconds
        data: Packet data
    """
    # Ensure timestamp is within 32-bit range
    timestamp_us = min(timestamp_us, 0xFFFFFFFF * 1_000_000)
    ts_sec = min(timestamp_us // 1_000_000, 0xFFFFFFFF)
    ts_usec = timestamp_us % 1_000_000
    
    # PCAP packet header
    f.write(struct.pack(
        '<IIII',
        ts_sec,
        ts_usec,
        len(data),
        len(data)
    ))
    
    # Packet data
    f.write(data)


def create_udp_packet(src_ip: str, dst_ip: str, src_port: int, dst_port: int, payload: bytes) -> bytes:
    """
    Create a minimal UDP packet with Ethernet and IP headers.
    
    Args:
        src_ip: Source IP address
        dst_ip: Destination IP address
        src_port: Source UDP port
        dst_port: Destination UDP port
        payload: UDP payload
        
    Returns:
        Complete packet bytes
    """
    # Ethernet header (14 bytes)
    eth_dst = b'\xff\xff\xff\xff\xff\xff'  # Broadcast
    eth_src = b'\x00\x00\x00\x00\x00\x00'  # Zero MAC
    eth_type = b'\x08\x00'  # IPv4
    
    ethernet_header = eth_dst + eth_src + eth_type
    
    # IP header (20 bytes)
    version_ihl = 0x45  # IPv4, 5 words header length
    dscp_ecn = 0
    total_length = min(20 + 8 + len(payload), 65535)  # IP + UDP + payload (limit to 16-bit)
    identification = 0
    flags_fragment = 0
    ttl = 64
    protocol = 17  # UDP
    checksum = 0  # Will be recalculated by receiver
    
    # Convert IP addresses
    src_ip_bytes = bytes(map(int, src_ip.split('.')))
    dst_ip_bytes = bytes(map(int, dst_ip.split('.')))
    
    ip_header = struct.pack(
        '!BBHHHBBH4s4s',
        version_ihl,
        dscp_ecn,
        total_length,
        identification,
        flags_fragment,
        ttl,
        protocol,
        checksum,
        src_ip_bytes,
        dst_ip_bytes
    )
    
    # UDP header (8 bytes)
    udp_length = min(8 + len(payload), 65535)  # Limit to 16-bit max
    udp_checksum = 0  # Optional for IPv4
    
    udp_header = struct.pack(
        '!HHHH',
        min(src_port, 65535),
        min(dst_port, 65535),
        udp_length,
        udp_checksum
    )
    
    return ethernet_header + ip_header + udp_header + payload


def encode_1553_payload(transaction: dict) -> bytes:
    """
    Encode 1553 transaction as compact binary payload.
    
    Format (TLV-style):
    - 1 byte: version (0x01)
    - 8 bytes: timestamp (microseconds as uint64)
    - 1 byte: bus (0=A, 1=B)
    - 1 byte: RT address
    - 1 byte: subaddress
    - 1 byte: T/R (0=BC2RT, 1=RT2BC)
    - 1 byte: word count
    - 2 bytes: status
    - 1 byte: error flags
    - Variable: JSON string with additional info
    
    Args:
        transaction: Transaction dictionary from inspector
        
    Returns:
        Encoded payload bytes
    """
    # Convert timestamp to microseconds
    # Clamp to reasonable range to avoid overflow
    ipts_ns = transaction.get('ipts_ns', 0)
    if ipts_ns > 1e18:  # If unreasonably large, use relative time instead
        ipts_ns = int(transaction.get('t_rel_ms', 0) * 1_000_000)
    timestamp_us = int(ipts_ns / 1000) if ipts_ns < 1e15 else 0
    
    # Encode bus
    bus_byte = 0 if transaction['bus'] == 'A' else 1
    
    # Encode T/R
    tr_byte = 0 if transaction['tr'] == 'BC2RT' else 1
    
    # Encode error flags
    error_flags = 0
    for i, error in enumerate(transaction.get('errors', [])):
        if i < 8:  # Only 8 bits available
            error_flags |= (1 << i)
    
    # Fixed header
    # Ensure all values are within valid ranges
    try:
        header = struct.pack(
            '!BQBBBBBHb',
            0x01,  # Version
            min(timestamp_us, 0xFFFFFFFFFFFFFFFF),  # 64-bit
            bus_byte & 0xFF,  # 8-bit
            min(transaction.get('rt', 0), 31) & 0x1F,  # 5-bit RT address
            min(transaction.get('sa', 0), 31) & 0x1F,  # 5-bit subaddress
            tr_byte & 0x01,  # 1-bit
            min(transaction.get('wc', 0), 31) & 0x1F,  # 5-bit word count
            min(transaction.get('status', 0), 65535) & 0xFFFF,  # 16-bit status
            error_flags & 0xFF  # 8-bit
        )
    except struct.error as e:
        # Debug output
        print(f"Error packing: {e}")
        print(f"  timestamp_us: {timestamp_us}")
        print(f"  rt: {transaction.get('rt', 0)}")
        print(f"  sa: {transaction.get('sa', 0)}")
        print(f"  wc: {transaction.get('wc', 0)}")
        print(f"  status: {transaction.get('status', 0)}")
        raise
    
    # Additional info as JSON
    extra_info = {
        't_rel_ms': transaction['t_rel_ms'],
        'errors': transaction.get('errors', [])
    }
    extra_json = json.dumps(extra_info, separators=(',', ':'))
    
    return header + extra_json.encode('utf-8')


def export_pcap(
    filepath: Path,
    output_path: Path,
    channel: str = '1553A',
    max_messages: int = 100000,
    rt_filter: int = None,
    sa_filter: int = None,
    errors_only: bool = False,
    reader: str = 'auto'
) -> int:
    """
    Export CH10 1553 data to PCAP format.
    
    Args:
        filepath: Input CH10 file
        output_path: Output PCAP file
        channel: Channel to export
        max_messages: Maximum messages to export
        rt_filter: Filter by RT address
        sa_filter: Filter by subaddress
        errors_only: Only export errors
        reader: Reader to use ('auto', 'pyc10', 'wire')
        
    Returns:
        Number of packets written
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    count = 0
    with open(output_path, 'wb') as f:
        # Write PCAP header
        write_pcap_header(f)
        
        # Process transactions using the same timeline generator
        for transaction in inspect_1553_timeline(
            filepath, channel, max_messages, rt_filter, sa_filter, errors_only, reader
        ):
            # Create UDP packet with 1553 data
            payload = encode_1553_payload(transaction)
            
            # Source/dest IPs based on bus
            src_ip = '10.15.53.1' if transaction['bus'] == 'A' else '10.15.53.2'
            dst_ip = '10.15.53.255'  # Broadcast
            
            packet = create_udp_packet(
                src_ip, dst_ip,
                UDP_PORT, UDP_PORT,
                payload
            )
            
            # Write to PCAP
            # Use relative time if absolute time is unreasonable
            ipts_ns = transaction.get('ipts_ns', 0)
            if ipts_ns > 1e15:  # If unreasonably large, use relative time
                timestamp_us = int(transaction.get('t_rel_ms', 0) * 1000)
            else:
                timestamp_us = ipts_ns // 1000
            write_pcap_packet(f, timestamp_us, packet)
            
            count += 1
    
    if count == 0:
        # No messages found, hint to use wire reader
        print("Warning: No messages found to export. Try: ch10gen inspect --reader wire")
        return 0
    
    return count
