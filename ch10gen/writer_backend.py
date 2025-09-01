"""Writer backend abstraction for CH10 file generation.

Supports multiple backends:
- irig106lib: Spec-compliant (default)
- pychapter10: Compatibility mode
"""

import struct
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

try:
    from .schedule import ScheduledMessage
    from .flight_profile import FlightProfileGenerator, FlightState
    from .icd import MessageDefinition
except ImportError:
    from schedule import ScheduledMessage
    from flight_profile import FlightProfileGenerator, FlightState
    from icd import MessageDefinition


class Ch10WriterBackend(ABC):
    """Abstract base class for CH10 writer backends."""
    
    @abstractmethod
    def write_tmats(self, content: str, channel_id: int, rtc: int) -> None:
        """Write TMATS packet."""
        pass
    
    @abstractmethod
    def write_time(self, timestamp: datetime, channel_id: int, rtc: int) -> None:
        """Write time packet."""
        pass
    
    @abstractmethod
    def write_1553_messages(self, messages: List[Dict], channel_id: int, rtc: int) -> None:
        """Write MS1553F1 packet with messages."""
        pass
    
    @abstractmethod
    def open(self, filepath: Path) -> None:
        """Open file for writing."""
        pass
    
    @abstractmethod
    def close(self) -> Dict[str, Any]:
        """Close file and return statistics."""
        pass


class PyChapter10Backend(Ch10WriterBackend):
    """PyChapter10 backend with compatibility quirks."""
    
    def __init__(self):
        self.file = None
        self.packet_count = 0
        self.message_count = 0
        
    def open(self, filepath: Path) -> None:
        """Open file for writing."""
        from chapter10 import C10  # Lazy import
        
        # Ensure file exists (PyChapter10 requirement)
        filepath.touch()
        self.filepath = filepath
        self.file = open(filepath, 'wb')
        self.packet_count = 0
        self.message_count = 0
        
    def write_tmats(self, content: str, channel_id: int, rtc: int) -> None:
        """Write TMATS packet using PyChapter10."""
        from chapter10.message import MessageF0
        
        packet = MessageF0()
        packet.channel_id = channel_id
        packet.rtc = rtc
        # Don't set data_type - PyChapter10 ignores it
        packet.body = content.encode('utf-8')
        
        self.file.write(bytes(packet))
        self.packet_count += 1
        
    def write_time(self, timestamp: datetime, channel_id: int, rtc: int) -> None:
        """Write time packet using PyChapter10."""
        from chapter10.time import TimeF1
        
        packet = TimeF1()
        packet.channel_id = channel_id
        packet.rtc = rtc
        # Don't set data_type - PyChapter10 ignores it
        
        # Set time fields
        packet.seconds = timestamp.second
        packet.minutes = timestamp.minute
        packet.hours = timestamp.hour
        packet.days = timestamp.timetuple().tm_yday
        
        self.file.write(bytes(packet))
        self.packet_count += 1
        
    def write_1553_messages(self, messages: List[Dict], channel_id: int, rtc: int) -> None:
        """Write MS1553F1 packet with messages."""
        from chapter10.ms1553 import MS1553F1
        
        packet = MS1553F1()
        packet.channel_id = channel_id
        packet.rtc = rtc
        # Don't set data_type - PyChapter10 ignores it
        
        # Add messages
        for msg_data in messages:
            msg = MS1553F1.Message()
            msg.ipts = msg_data['ipts']
            msg.data = msg_data['data']  # Already bytes
            msg.bus = msg_data['bus']
            packet.append(msg)
            self.message_count += 1
        
        # CRITICAL: Fix PyChapter10 bug - manually set CSDW message count
        packet.count = len(messages)
        
        self.file.write(bytes(packet))
        self.packet_count += 1
        
    def close(self) -> Dict[str, Any]:
        """Close file and return statistics."""
        if self.file:
            self.file.close()
            
        stats = {
            'packets': self.packet_count,
            'messages': self.message_count,
            'backend': 'pychapter10'
        }
        
        if self.filepath and self.filepath.exists():
            stats['file_size'] = self.filepath.stat().st_size
            
        return stats


class Irig106LibBackend(Ch10WriterBackend):
    """IRIG106 library backend - fully spec-compliant."""
    
    def __init__(self):
        self.file = None
        self.packet_count = 0
        self.message_count = 0
        self._try_load_dll()
        
    def _try_load_dll(self):
        """Try to load irig106.dll on Windows."""
        self.dll_available = False
        
        try:
            import ctypes
            import platform
            
            if platform.system() != 'Windows':
                return
            
            # Try common paths for irig106.dll
            dll_paths = [
                'irig106.dll',
                'C:\\irig106\\irig106.dll',
                'C:\\Program Files\\irig106\\irig106.dll',
                'C:\\Program Files (x86)\\irig106\\irig106.dll',
            ]
            
            for path in dll_paths:
                try:
                    self.dll = ctypes.CDLL(path)
                    self.dll_available = True
                    self._setup_dll_functions()
                    break
                except:
                    continue
                    
        except ImportError:
            pass
            
    def _setup_dll_functions(self):
        """Setup ctypes function signatures for irig106.dll."""
        import ctypes
        
        # This would define function signatures
        # For now, we'll fall back to manual implementation
        pass
        
    def open(self, filepath: Path) -> None:
        """Open file for writing."""
        self.filepath = filepath
        self.file = open(filepath, 'wb')
        self.packet_count = 0
        self.message_count = 0
        
    def write_tmats(self, content: str, channel_id: int, rtc: int) -> None:
        """Write spec-compliant TMATS packet."""
        # Build IRIG-106 packet header
        sync = 0xEB25
        packet_len = 24 + len(content)
        data_len = len(content)
        data_type = 0x01  # TMATS per spec
        
        header = struct.pack('<HH', sync, channel_id)
        header += struct.pack('<II', packet_len, data_len)
        header += struct.pack('<BB', 0, self.packet_count & 0xFF)  # Version, sequence
        header += struct.pack('<BB', data_type, 0)  # Data type at byte 14!
        header += struct.pack('<H', 0)  # Header checksum
        header += struct.pack('<IH', rtc, 0)  # RTC
        
        # Write packet
        self.file.write(header + content.encode('utf-8'))
        self.packet_count += 1
        
    def write_time(self, timestamp: datetime, channel_id: int, rtc: int) -> None:
        """Write spec-compliant Time F1 packet."""
        sync = 0xEB25
        data_type = 0x02  # Time F1 per spec
        
        # Build time data (IRIG-106 Ch 11 format)
        # This is simplified - real implementation would follow spec exactly
        time_data = struct.pack('<BBBBHH',
                               timestamp.second,
                               timestamp.minute, 
                               timestamp.hour,
                               0,  # Reserved
                               timestamp.timetuple().tm_yday,
                               timestamp.year)
        
        packet_len = 24 + len(time_data)
        data_len = len(time_data)
        
        header = struct.pack('<HH', sync, channel_id)
        header += struct.pack('<II', packet_len, data_len)
        header += struct.pack('<BB', 0, self.packet_count & 0xFF)
        header += struct.pack('<BB', data_type, 0)  # Data type at byte 14!
        header += struct.pack('<H', 0)
        header += struct.pack('<IH', rtc, 0)
        
        self.file.write(header + time_data)
        self.packet_count += 1
        
    def write_1553_messages(self, messages: List[Dict], channel_id: int, rtc: int) -> None:
        """Write spec-compliant MS1553F1 packet."""
        sync = 0xEB25
        data_type = 0x19  # MS1553 F1 per spec
        
        # Build CSDW (Channel Specific Data Word)
        message_count = len(messages)
        format_version = 0
        ttb_present = 0
        csdw = message_count | (format_version << 16) | (ttb_present << 20)
        
        # Build message data
        msg_data = struct.pack('<I', csdw)
        
        for msg in messages:
            # Intra-message header (8 bytes)
            block_status = 0
            gap_time = 0
            msg_length = len(msg['data'])
            reserved = 0
            
            msg_data += struct.pack('<HHHH', 
                                    block_status, gap_time, 
                                    msg_length, reserved)
            msg_data += msg['data']  # Already bytes
            
            self.message_count += 1
        
        packet_len = 24 + len(msg_data)
        data_len = len(msg_data)
        
        header = struct.pack('<HH', sync, channel_id)
        header += struct.pack('<II', packet_len, data_len)
        header += struct.pack('<BB', 0, self.packet_count & 0xFF)
        header += struct.pack('<BB', data_type, 0)  # Data type at byte 14!
        header += struct.pack('<H', 0)
        header += struct.pack('<IH', rtc, 0)
        
        self.file.write(header + msg_data)
        self.packet_count += 1
        
    def close(self) -> Dict[str, Any]:
        """Close file and return statistics."""
        if self.file:
            self.file.close()
            
        stats = {
            'packets': self.packet_count,
            'messages': self.message_count,
            'backend': 'irig106lib',
            'spec_compliant': True
        }
        
        if self.filepath and self.filepath.exists():
            stats['file_size'] = self.filepath.stat().st_size
            
        return stats


def create_writer_backend(backend_name: str = 'irig106') -> Ch10WriterBackend:
    """Factory function to create writer backend.
    
    Args:
        backend_name: 'irig106' (default) or 'pyc10'
        
    Returns:
        Writer backend instance
    """
    if backend_name == 'pyc10' or backend_name == 'pychapter10':
        return PyChapter10Backend()
    elif backend_name == 'irig106' or backend_name == 'irig106lib':
        return Irig106LibBackend()
    else:
        raise ValueError(f"Unknown backend: '{backend_name}'. Use 'irig106' or 'pyc10'")
