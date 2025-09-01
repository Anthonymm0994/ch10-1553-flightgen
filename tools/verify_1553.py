#!/usr/bin/env python3
"""
Comprehensive 1553 message validation tool based on IRIG-106 standards.
This tool validates CH10 format compliance and proper command word parsing.
"""

import struct
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple

try:
    from chapter10 import C10
    from chapter10.ms1553 import MS1553F1
    PYCHAPTER10_AVAILABLE = True
except ImportError:
    PYCHAPTER10_AVAILABLE = False
    print("WARNING: PyChapter10 not available. Install with: pip install pychapter10")


def parse_cmd(word: int) -> Tuple[int, int, int, int]:
    """
    Parse 1553 command word according to MIL-STD-1553 standard.
    
    Command word format: [RT:5][TR:1][SA:5][WC/MC:5]
    """
    rt = (word >> 11) & 0x1F
    tr = (word >> 10) & 0x01  # 0=BC->RT (Receive), 1=RT->BC (Transmit)
    sa = (word >> 5) & 0x1F
    wc = word & 0x1F
    return rt, tr, sa, wc


def data_words(sa: int, wc: int) -> int:
    """
    Calculate actual data word count per IRIG-106 handbook algorithm.
    
    Mode code handling + WC wrap:
    - SA=0 or SA=31 (mode codes): 1 word if WC bit 4 set, else 0
    - Other SA: 32 words if WC=0, else WC
    """
    if sa in (0, 31):  # mode code
        return 1 if (wc & 0x10) else 0
    return 32 if wc == 0 else wc


def validate_message_structure(msg, msg_index: int) -> Dict[str, Any]:
    """
    Validate a single 1553 message structure according to IRIG-106.
    
    Returns validation results with expected vs actual values.
    """
    if len(msg.data) < 2:
        return {
            'valid': False,
            'error': 'Message too short (less than 2 bytes)',
            'msg_index': msg_index
        }
    
    # Parse command word (little-endian, first 16 bits)
    cmd0 = struct.unpack_from("<H", msg.data, 0)[0]
    rt, tr, sa, wc = parse_cmd(cmd0)
    
    # Calculate expected data words
    dwords = data_words(sa, wc)
    
    # Calculate expected message structure
    # Non-RT2RT: 1 command + data_words + 1 status
    # RT2RT: 2 commands + data_words + 2 status
    cmds = 2 if msg.rt2rt else 1
    stats = 2 if msg.rt2rt else (0 if rt == 31 else 1)
    expected_bytes = 2 * (cmds + stats + dwords)
    
    # Check message length
    length_ok = (msg.length == expected_bytes)
    
    # Parse error flags
    flags = {
        'LE': msg.le,    # Length Error
        'SE': msg.se,    # Sync Error  
        'WE': msg.we,    # Word Error
        'TO': msg.timeout,  # Timeout
        'ME': msg.me,    # Message Error
        'FE': msg.fe     # Format Error
    }
    
    # Check for critical errors
    critical_errors = [k for k, v in flags.items() if v]
    
    return {
        'valid': length_ok and not critical_errors,
        'msg_index': msg_index,
        'bus': msg.bus,
        'rt': rt,
        'tr': tr,
        'sa': sa,
        'wc': wc,
        'rt2rt': msg.rt2rt,
        'len_bytes': msg.length,
        'expected_bytes': expected_bytes,
        'length_ok': length_ok,
        'flags': flags,
        'critical_errors': critical_errors,
        'gap': msg.gap_time,
        'cmd_word_hex': f"0x{cmd0:04X}"
    }


def verify_ch10_file(filepath: Path) -> Dict[str, Any]:
    """
    Comprehensive CH10 file verification.
    
    Returns detailed validation results.
    """
    if not PYCHAPTER10_AVAILABLE:
        return {
            'error': 'PyChapter10 not available',
            'valid': False
        }
    
    results = {
        'file': str(filepath),
        'valid': True,
        'packets': 0,
        'messages': 0,
        'channels': {},
        'message_details': [],
        'errors': []
    }
    
    try:
        c10 = C10(str(filepath))
        for pkt in c10:
            if not isinstance(pkt, MS1553F1):
                continue
            
            results['packets'] += 1
            
            # Track channel info
            channel_id = pkt.channel_id
            if channel_id not in results['channels']:
                results['channels'][channel_id] = {
                    'packets': 0,
                    'messages': 0,
                    'name': 'A' if channel_id == 0x0200 else 'B' if channel_id == 0x0210 else f'Unknown({hex(channel_id)})'
                }
            
            results['channels'][channel_id]['packets'] += 1
            
            # Validate CSDW
            if hasattr(pkt, 'count'):
                expected_count = pkt.count
                actual_count = len(list(pkt))
                
                if expected_count != actual_count:
                    results['errors'].append(
                        f"Packet {results['packets']}: CSDW count mismatch - "
                        f"declared {expected_count}, actual {actual_count}"
                    )
                    results['valid'] = False
            
            # Process each message
            for i, msg in enumerate(pkt):
                results['messages'] += 1
                results['channels'][channel_id]['messages'] += 1
                
                # Validate message structure
                msg_result = validate_message_structure(msg, results['messages'])
                results['message_details'].append(msg_result)
                
                if not msg_result['valid']:
                    results['valid'] = False
                    if 'error' in msg_result:
                        results['errors'].append(f"Message {results['messages']}: {msg_result['error']}")
                    else:
                        results['errors'].append(
                            f"Message {results['messages']}: Length mismatch - "
                            f"expected {msg_result['expected_bytes']}, got {msg_result['len_bytes']}"
                        )
                
                if msg_result.get('critical_errors'):
                    results['errors'].append(
                        f"Message {results['messages']}: Critical errors - {msg_result['critical_errors']}"
                    )
                    results['valid'] = False
                    
    except Exception as e:
        results['error'] = f"Failed to read file: {e}"
        results['valid'] = False
    
    return results


def print_verification_results(results: Dict[str, Any]):
    """Print formatted verification results."""
    print(f"\n=== CH10 File Verification: {results['file']} ===")
    print(f"Valid: {'✓' if results['valid'] else '✗'}")
    
    if 'error' in results:
        print(f"Error: {results['error']}")
        return
    
    print(f"Packets: {results['packets']}")
    print(f"Messages: {results['messages']}")
    
    print("\nChannels:")
    for ch_id, info in results['channels'].items():
        print(f"  {info['name']} ({hex(ch_id)}): {info['packets']} packets, {info['messages']} messages")
    
    if results['errors']:
        print(f"\nErrors ({len(results['errors'])}):")
        for error in results['errors']:
            print(f"  - {error}")
    
    # Show sample message details
    if results['message_details']:
        print(f"\nSample Messages (first 5):")
        for i, msg in enumerate(results['message_details'][:5]):
            status = "✓" if msg['valid'] else "✗"
            print(f"  {i+1:2d}. {status} RT={msg['rt']:2d} SA={msg['sa']:2d} "
                  f"WC={msg['wc']:2d} TR={msg['tr']} RT2RT={msg['rt2rt']} "
                  f"Len={msg['len_bytes']:3d}/{msg['expected_bytes']:3d} "
                  f"Cmd={msg['cmd_word_hex']}")
            
            if msg.get('critical_errors'):
                print(f"      Errors: {msg['critical_errors']}")


def main():
    """Main verification function."""
    if len(sys.argv) != 2:
        print("Usage: python verify_1553.py <ch10_file>")
        sys.exit(1)
    
    filepath = Path(sys.argv[1])
    if not filepath.exists():
        print(f"Error: File not found: {filepath}")
        sys.exit(1)
    
    results = verify_ch10_file(filepath)
    print_verification_results(results)
    
    if not results['valid']:
        sys.exit(1)


if __name__ == "__main__":
    main()
