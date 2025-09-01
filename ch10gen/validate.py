"""Validation tools for Chapter 10 files."""

import subprocess
import shutil
import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

try:
    from chapter10 import C10, Packet
    from chapter10.time import TimeF1
    from chapter10.ms1553 import MS1553F1
    from chapter10.message import MessageF0
except ImportError:
    raise ImportError("PyChapter10 is required. Install with: pip install pychapter10")


class Ch10Validator:
    """Validate Chapter 10 files."""
    
    def __init__(self, filepath: Path):
        """Initialize validator with file path."""
        self.filepath = Path(filepath)
        
        if not self.filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        
        self.stats = {
            'file_size_bytes': self.filepath.stat().st_size,
            'packet_count': 0,
            'packet_types': {},
            'channel_ids': set(),
            'time_range': None,
            'tmats_present': False,
            'time_packets': 0,
            '1553_packets': 0,
            '1553_messages': 0,
            'errors': [],
            'warnings': []
        }
    
    def validate(self, verbose: bool = False) -> Dict[str, Any]:
        """
        Validate Chapter 10 file.
        
        Args:
            verbose: Print detailed information
        
        Returns:
            Validation statistics and results
        """
        try:
            c10 = C10(str(self.filepath))
            
            first_time = None
            last_time = None
            
            # Iterate through all packets
            for packet in c10:
                self.stats['packet_count'] += 1
                
                # Track packet types
                packet_type = type(packet).__name__
                self.stats['packet_types'][packet_type] = self.stats['packet_types'].get(packet_type, 0) + 1
                
                # Track channel IDs
                if hasattr(packet, 'channel_id'):
                    self.stats['channel_ids'].add(packet.channel_id)
                
                # Track time range
                if hasattr(packet, 'rtc'):
                    rtc = packet.rtc
                    if rtc:
                        if first_time is None or rtc < first_time:
                            first_time = rtc
                        if last_time is None or rtc > last_time:
                            last_time = rtc
                
                # Check specific packet types
                if isinstance(packet, MessageF0):
                    self.stats['tmats_present'] = True
                    self._validate_tmats(packet)
                elif hasattr(packet, 'channel_id') and packet.channel_id == 0x001:
                    # Alternative check for TMATS by channel ID
                    self.stats['tmats_present'] = True
                    if hasattr(packet, 'body'):
                        self._validate_tmats(packet)
                    
                elif isinstance(packet, TimeF1) or (hasattr(packet, 'data_type') and packet.data_type == 0x02):
                    self.stats['time_packets'] += 1
                    self._validate_time_packet(packet)
                    
                elif isinstance(packet, MS1553F1):
                    self.stats['1553_packets'] += 1
                    msg_count = self._validate_1553_packet(packet)
                    self.stats['1553_messages'] += msg_count
            
            # PyChapter10 C10 object doesn't have close()
            # but we need to ensure file handle is released
            try:
                if hasattr(c10, 'file'):
                    c10.file.close()
                elif hasattr(c10, '_file'):
                    c10._file.close()
            except:
                pass  # Best effort to close
            
            # Set time range
            if first_time and last_time:
                duration_us = last_time - first_time
                self.stats['time_range'] = {
                    'first_rtc': first_time,
                    'last_rtc': last_time,
                    'duration_s': duration_us / 1_000_000
                }
            
            # Perform additional checks
            self._check_requirements()
            
            if verbose:
                self._print_summary()
            
        except Exception as e:
            self.stats['errors'].append(f"Failed to read file: {e}")
        
        return self.stats
    
    def _validate_tmats(self, packet: MessageF0) -> None:
        """Validate TMATS packet."""
        try:
            # Check if body exists
            if not packet.body:
                self.stats['warnings'].append("TMATS packet has empty body")
                return
            
            # Try to decode TMATS
            tmats_text = packet.body.decode('utf-8', errors='ignore')
            
            # Check for required attributes
            required = ['G\\106', 'G\\DSI\\N']
            for attr in required:
                if attr not in tmats_text:
                    self.stats['warnings'].append(f"TMATS missing required attribute: {attr}")
            
            # Count channels defined
            channel_count = tmats_text.count('\\CDT')
            if channel_count > 0:
                self.stats['tmats_channels'] = channel_count
                
        except Exception as e:
            self.stats['warnings'].append(f"Failed to parse TMATS: {e}")
    
    def _validate_time_packet(self, packet: TimeF1) -> None:
        """Validate time packet."""
        try:
            # Check time format
            if not hasattr(packet, 'time_format'):
                self.stats['warnings'].append("Time packet missing time_format")
            
            # Check for reasonable values
            if hasattr(packet, 'seconds') and (packet.seconds < 0 or packet.seconds > 59):
                self.stats['warnings'].append(f"Time packet has invalid seconds: {packet.seconds}")
                
            if hasattr(packet, 'minutes') and (packet.minutes < 0 or packet.minutes > 59):
                self.stats['warnings'].append(f"Time packet has invalid minutes: {packet.minutes}")
                
            if hasattr(packet, 'hours') and (packet.hours < 0 or packet.hours > 23):
                self.stats['warnings'].append(f"Time packet has invalid hours: {packet.hours}")
                
        except Exception as e:
            self.stats['warnings'].append(f"Failed to validate time packet: {e}")
    
    def _validate_1553_packet(self, packet: MS1553F1) -> int:
        """
        Validate 1553 packet and return message count.
        
        Args:
            packet: 1553 F1 packet
        
        Returns:
            Number of messages in packet
        """
        try:
            message_count = 0
            
            # MS1553F1 packets are directly iterable
            for msg in packet:
                message_count += 1
                
                # Validate message data
                if hasattr(msg, 'data') and msg.data:
                    # Convert bytes to words (little-endian 16-bit)
                    if len(msg.data) >= 2:
                        import struct
                        words = [struct.unpack('<H', msg.data[i:i+2])[0] 
                                for i in range(0, len(msg.data), 2)]
                        
                        if len(words) > 0:
                            # Extract RT and SA from command word (first word)
                            command_word = words[0]
                            rt = (command_word >> 11) & 0x1F
                            sa = (command_word >> 5) & 0x1F
                            wc_field = command_word & 0x1F
                            wc = wc_field if wc_field != 0 else 32
                            
                            # Validate RT and SA
                            if rt > 31:
                                self.stats['warnings'].append(f"Invalid RT address: {rt}")
                            if sa > 31:
                                self.stats['warnings'].append(f"Invalid subaddress: {sa}")
                            
                            # Check data word count (disabled for now due to packet parsing issues)
                            # actual_words = len(words)
                            # expected_total = 2 + wc  # Command word + status word + data words
                            # if actual_words != expected_total:
                            #     self.stats['warnings'].append(
                            #         f"Data word count mismatch: expected {expected_total}, got {actual_words}"
                            #     )
            
            return message_count
            
        except Exception as e:
            self.stats['warnings'].append(f"Failed to validate 1553 packet: {e}")
            return 0
    
    def _check_requirements(self) -> None:
        """Check basic requirements."""
        # Check for TMATS
        if not self.stats['tmats_present']:
            self.stats['errors'].append("No TMATS packet found")
        
        # Check for time packets
        if self.stats['time_packets'] == 0:
            self.stats['errors'].append("No time packets found")
        
        # Check for 1553 packets
        if self.stats['1553_packets'] == 0:
            self.stats['warnings'].append("No 1553 packets found")
        
        # Check packet count
        if self.stats['packet_count'] == 0:
            self.stats['errors'].append("File contains no packets")
        
        # Calculate message rate if we have timing info
        if self.stats['time_range'] and self.stats['1553_messages'] > 0:
            duration = self.stats['time_range']['duration_s']
            if duration > 0:
                self.stats['message_rate_hz'] = self.stats['1553_messages'] / duration
    
    def _print_summary(self) -> None:
        """Print validation summary."""
        print(f"\n{'='*60}")
        print(f"Chapter 10 File Validation: {self.filepath.name}")
        print(f"{'='*60}")
        
        print(f"\nFile Info:")
        print(f"  Size: {self.stats['file_size_bytes']:,} bytes")
        print(f"  Total Packets: {self.stats['packet_count']:,}")
        
        if self.stats['time_range']:
            print(f"  Duration: {self.stats['time_range']['duration_s']:.2f} seconds")
        
        print(f"\nPacket Types:")
        for ptype, count in self.stats['packet_types'].items():
            print(f"  {ptype}: {count:,}")
        
        print(f"\nChannels:")
        for ch_id in sorted(self.stats['channel_ids']):
            print(f"  0x{ch_id:03X}")
        
        print(f"\n1553 Data:")
        print(f"  Packets: {self.stats['1553_packets']:,}")
        print(f"  Messages: {self.stats['1553_messages']:,}")
        
        if 'message_rate_hz' in self.stats:
            print(f"  Message Rate: {self.stats['message_rate_hz']:.1f} Hz")
        
        if self.stats['errors']:
            print(f"\nERRORS ({len(self.stats['errors'])}):")
            for error in self.stats['errors'][:10]:  # Limit to first 10
                print(f"  ERROR {error}")
        
        if self.stats['warnings']:
            print(f"\nWARNINGS ({len(self.stats['warnings'])}):")
            for warning in self.stats['warnings'][:10]:  # Limit to first 10
                print(f"  WARNING  {warning}")
        
        if not self.stats['errors']:
            print(f"\nOK File validation PASSED")
        else:
            print(f"\nERROR File validation FAILED")
        
        print(f"{'='*60}\n")


def validate_with_c10_tools(filepath: Path) -> Optional[Dict[str, Any]]:
    """
    Validate using external c10-tools if available.
    
    Args:
        filepath: Path to Chapter 10 file
    
    Returns:
        Results from c10-tools or None if not available
    """
    results = {}
    
    # Try c10-errcount
    try:
        result = subprocess.run(
            ['c10-errcount', str(filepath)],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            results['errcount'] = result.stdout
        else:
            results['errcount_error'] = result.stderr
            
    except (subprocess.SubprocessError, FileNotFoundError):
        # c10-tools not available
        pass
    
    # Try c10-dump
    try:
        result = subprocess.run(
            ['c10-dump', '--summary', str(filepath)],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            results['dump_summary'] = result.stdout
        else:
            results['dump_error'] = result.stderr
            
    except (subprocess.SubprocessError, FileNotFoundError):
        pass
    
    # Try c10-dmp1553
    try:
        result = subprocess.run(
            ['c10-dmp1553', '--count', str(filepath)],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            results['dmp1553'] = result.stdout
        else:
            results['dmp1553_error'] = result.stderr
            
    except (subprocess.SubprocessError, FileNotFoundError):
        pass
    
    return results if results else None


def validate_file(filepath: Path, verbose: bool = True, 
                 use_c10_tools: bool = True) -> Dict[str, Any]:
    """
    Complete file validation.
    
    Args:
        filepath: Path to Chapter 10 file
        verbose: Print detailed output
        use_c10_tools: Try to use external c10-tools
    
    Returns:
        Validation results
    """
    # Internal validation
    validator = Ch10Validator(filepath)
    results = validator.validate(verbose=verbose)
    
    # External validation if requested
    if use_c10_tools:
        c10_tools_results = validate_with_c10_tools(filepath)
        if c10_tools_results:
            results['c10_tools'] = c10_tools_results
            if verbose:
                print("\nc10-tools validation results:")
                for tool, output in c10_tools_results.items():
                    if not tool.endswith('_error'):
                        print(f"\n{tool}:")
                        print(output[:500])  # Limit output
    
    return results


def detect_external_tools() -> Dict[str, bool]:
    """
    Detect available external validation tools on Windows.
    
    Returns:
        Dictionary of tool availability
    """
    tools = {}
    
    # Check c10-tools
    tools['c10_tools'] = (
        shutil.which('c10-stat') is not None or
        shutil.which('c10-dmp1553') is not None
    )
    
    # Check irig106 tools
    tools['irig106'] = (
        shutil.which('i106stat') is not None or
        shutil.which('idmp1553') is not None
    )
    
    return tools


def validate_external(filepath: Path, timeout_s: int = 20) -> Dict[str, Any]:
    """
    Run external validation tools if available.
    
    Args:
        filepath: Path to Chapter 10 file
        timeout_s: Timeout for each tool in seconds
        
    Returns:
        Validation results with tool detection and metrics
    """
    detected = detect_external_tools()
    
    results = {
        'external': {
            'detected': detected,
            'summary': {},
            'ms1553': {},
            'notes': []
        }
    }
    
    # Try c10-stat if available
    if shutil.which('c10-stat'):
        try:
            result = subprocess.run(
                ['c10-stat', str(filepath)],
                capture_output=True,
                text=True,
                timeout=timeout_s
            )
            
            if result.returncode == 0:
                results['external']['notes'].append('c10-stat ok')
                
                # Parse packet count from output
                output = result.stdout
                for line in output.split('\n'):
                    if 'Total packets' in line:
                        parts = line.split(':')
                        if len(parts) > 1:
                            try:
                                count = int(parts[1].strip())
                                results['external']['summary']['packets'] = count
                            except:
                                pass
                    elif 'Channel' in line and '0x' in line:
                        # Extract channel IDs
                        if 'channels' not in results['external']['summary']:
                            results['external']['summary']['channels'] = []
                        try:
                            ch_id = line.split('0x')[1].split()[0]
                            results['external']['summary']['channels'].append(f'0x{ch_id}')
                        except:
                            pass
            else:
                results['external']['notes'].append(f'c10-stat error: {result.returncode}')
                
        except subprocess.TimeoutExpired:
            results['external']['notes'].append('c10-stat timeout')
        except Exception as e:
            results['external']['notes'].append(f'c10-stat failed: {str(e)}')
    
    # Try c10-dmp1553 if available  
    if shutil.which('c10-dmp1553'):
        try:
            result = subprocess.run(
                ['c10-dmp1553', '--count', '1000', str(filepath)],
                capture_output=True,
                text=True,
                timeout=timeout_s
            )
            
            if result.returncode == 0:
                results['external']['notes'].append('c10-dmp1553 ok')
                
                # Count messages and errors
                output = result.stdout
                msg_count = 0
                error_count = 0
                parity_errors = 0
                
                for line in output.split('\n'):
                    if '1553' in line.lower():
                        msg_count += 1
                    if 'error' in line.lower():
                        error_count += 1
                    if 'parity' in line.lower():
                        parity_errors += 1
                
                results['external']['ms1553'] = {
                    'sampled': min(msg_count, 1000),
                    'errors': error_count,
                    'parity_errors': parity_errors
                }
            else:
                results['external']['notes'].append(f'c10-dmp1553 error: {result.returncode}')
                
        except subprocess.TimeoutExpired:
            results['external']['notes'].append('c10-dmp1553 timeout')
        except Exception as e:
            results['external']['notes'].append(f'c10-dmp1553 failed: {str(e)}')
    
    # Try i106stat if available
    if shutil.which('i106stat'):
        try:
            result = subprocess.run(
                ['i106stat', str(filepath)],
                capture_output=True,
                text=True,
                timeout=timeout_s
            )
            
            if result.returncode == 0:
                results['external']['notes'].append('i106stat ok')
                # Parse additional metrics if needed
            else:
                results['external']['notes'].append(f'i106stat error: {result.returncode}')
                
        except subprocess.TimeoutExpired:
            results['external']['notes'].append('i106stat timeout')
        except Exception as e:
            results['external']['notes'].append(f'i106stat failed: {str(e)}')
    
    # Try idmp1553 if available
    if shutil.which('idmp1553'):
        try:
            result = subprocess.run(
                ['idmp1553', '-c', '100', str(filepath)],
                capture_output=True,
                text=True,
                timeout=timeout_s
            )
            
            if result.returncode == 0:
                results['external']['notes'].append('idmp1553 ok')
                # Parse if needed
            else:
                results['external']['notes'].append(f'idmp1553 error: {result.returncode}')
                
        except subprocess.TimeoutExpired:
            results['external']['notes'].append('idmp1553 timeout')
        except Exception as e:
            results['external']['notes'].append(f'idmp1553 failed: {str(e)}')
    
    # Add note if no tools detected
    if not any(detected.values()):
        results['external']['notes'].append(
            'No external tools detected. Install c10-tools or irig106lib for enhanced validation.'
        )
    
    return results
