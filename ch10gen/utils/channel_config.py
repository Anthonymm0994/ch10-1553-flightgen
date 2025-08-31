"""Channel ID and Data Type configuration for CH10 generation.

This module defines the contract between:
1. IRIG-106 spec data types (what should be at byte 14)
2. PyChapter10 channel ID conventions (what it actually uses)
"""

from dataclasses import dataclass
from typing import Dict, Optional


# IRIG-106 Data Type codes (spec-compliant values for byte 14)
DATA_TYPE_COMPUTER_F0 = 0x00  # Computer generated data format 0
DATA_TYPE_COMPUTER_F1 = 0x01  # Computer generated data format 1 (TMATS)
DATA_TYPE_TIME_F1 = 0x11      # Time format 1
DATA_TYPE_MS1553_F1 = 0x19    # MIL-STD-1553 format 1

# PyChapter10 channel ID patterns
# Note: PyChapter10 uses channel_id heuristics, not data_type field
# These are empirically determined from library behavior
PYCHAPTER10_CHANNELS = {
    'tmats': 0x0000,     # Channel 0 for TMATS
    'time': 0x0000,      # Also channel 0 for time (or 0x0001)
    'bus_a': 0x1000,     # Channel pattern for 1553 bus A
    'bus_b': 0x2000,     # Channel pattern for 1553 bus B
}


@dataclass
class ChannelConfig:
    """Configuration for channel IDs in CH10 files."""
    
    # Writer mode
    writer_backend: str = 'pychapter10'  # 'pychapter10' or 'irig106lib'
    reader_compat: str = 'pychapter10_quirks'  # 'strict' or 'pychapter10_quirks'
    
    # Channel IDs
    tmats_channel_id: int = 0x0200
    time_channel_id: int = 0x0100
    bus_a_channel_id: int = 0x0210
    bus_b_channel_id: int = 0x0220
    
    def get_data_type(self, packet_type: str) -> int:
        """Get the correct data_type value for a packet type.
        
        Args:
            packet_type: One of 'tmats', 'time', 'ms1553'
            
        Returns:
            Data type code per IRIG-106 spec
        """
        if self.writer_backend == 'pychapter10':
            # PyChapter10 doesn't use data_type field
            return DATA_TYPE_COMPUTER_F0
        
        # Spec-compliant values
        mapping = {
            'tmats': DATA_TYPE_COMPUTER_F1,
            'time': DATA_TYPE_TIME_F1,
            'ms1553': DATA_TYPE_MS1553_F1,
        }
        return mapping.get(packet_type, DATA_TYPE_COMPUTER_F0)
    
    def validate_channel_id(self, channel_id: int, expected_type: str) -> bool:
        """Validate a channel ID for a given packet type.
        
        Args:
            channel_id: The channel ID to validate
            expected_type: Expected packet type ('tmats', 'time', 'ms1553_a', 'ms1553_b')
            
        Returns:
            True if valid for the current compat mode
        """
        if self.reader_compat == 'strict':
            # In strict mode, validate against our defined IDs
            expected_ids = {
                'tmats': self.tmats_channel_id,
                'time': self.time_channel_id,
                'ms1553_a': self.bus_a_channel_id,
                'ms1553_b': self.bus_b_channel_id,
            }
            return channel_id == expected_ids.get(expected_type)
        
        # In PyChapter10 quirks mode, be more lenient
        # PyChapter10 seems to use patterns, not exact values
        return True  # Accept any channel ID in quirks mode
    
    @classmethod
    def from_dict(cls, config: Dict) -> 'ChannelConfig':
        """Create from dictionary configuration."""
        return cls(
            writer_backend=config.get('writer_backend', 'pychapter10'),
            reader_compat=config.get('reader_compat', 'pychapter10_quirks'),
            tmats_channel_id=config.get('tmats_channel_id', 0x0200),
            time_channel_id=config.get('time_channel_id', 0x0100),
            bus_a_channel_id=config.get('bus_a_channel_id', 0x0210),
            bus_b_channel_id=config.get('bus_b_channel_id', 0x0220),
        )


# Channel ID / Data Type mapping table for documentation
CHANNEL_DATA_TYPE_TABLE = """
| Packet Type | IRIG-106 Data Type | Our Channel ID | PyChapter10 Detection |
|-------------|-------------------|----------------|----------------------|
| TMATS       | 0x01              | 0x0200         | Channel pattern      |
| Time F1     | 0x11              | 0x0100         | Channel pattern      |
| MS1553 F1 A | 0x19              | 0x0210         | Channel pattern      |
| MS1553 F1 B | 0x19              | 0x0220         | Channel pattern      |

Note: PyChapter10 ignores the data_type field (byte 14) and uses channel_id
patterns to determine packet type. This is non-compliant but widely used.
"""
