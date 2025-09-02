"""Minimal TMATS builder for Chapter 10 files."""

from datetime import datetime
from typing import List, Dict, Any, Optional


class TMATSBuilder:
    """Build minimal TMATS for Chapter 10 files."""
    
    def __init__(self):
        """Initialize TMATS builder."""
        self.attributes = {}
        
        # Set required G (General Information) attributes
        self.attributes['G\\DSI\\N'] = 'ch10-1553-flightgen'  # Data source ID
        self.attributes['G\\106'] = '11'  # IRIG 106 version
        self.attributes['G\\OD'] = datetime.utcnow().strftime('%m/%d/%Y')  # Origin date
        self.attributes['G\\DST'] = 'SYNTHESIZED'  # Data source type
        
    def set_program_name(self, name: str) -> None:
        """Set program name."""
        self.attributes['G\\PN'] = name
    
    def set_test_name(self, name: str) -> None:
        """Set test name."""
        self.attributes['G\\TA'] = name
    
    def set_recorder_info(self, manufacturer: str = 'SYNTHETIC', 
                         model: str = 'CH10GEN',
                         serial: str = '000001') -> None:
        """Set recorder information."""
        self.attributes['R\\ID'] = manufacturer
        self.attributes['R\\MN'] = model
        self.attributes['R\\SN'] = serial
    
    def add_time_channel(self, channel_id: int = 0x001,
                        time_format: str = 'IRIG-B') -> None:
        """Add time data channel."""
        ch_idx = self._get_next_channel_index()
        
        self.attributes[f'R-{ch_idx}\\ID'] = f'{channel_id:03X}'
        self.attributes[f'R-{ch_idx}\\CDT'] = 'TIM'  # Channel data type
        self.attributes[f'R-{ch_idx}\\TF1'] = time_format
        self.attributes[f'R-{ch_idx}\\TIMEFMT'] = '1'  # Time format 1
    
    def add_1553_channel(self, channel_id: int = 0x002,
                        bus_name: str = 'BUS-A',
                        description: str = 'MIL-STD-1553 Bus A') -> None:
        """Add 1553 data channel."""
        ch_idx = self._get_next_channel_index()
        
        self.attributes[f'R-{ch_idx}\\ID'] = f'{channel_id:03X}'
        self.attributes[f'R-{ch_idx}\\CDT'] = '1553IN'  # Channel data type
        self.attributes[f'R-{ch_idx}\\TK1'] = bus_name
        self.attributes[f'R-{ch_idx}\\DSI'] = description
        self.attributes[f'R-{ch_idx}\\BTF'] = 'M'  # Bus traffic format (Messages)
    
    def add_bus_attributes(self, bus_name: str, channel_id: int,
                          num_messages: int = 0,
                          word_rate: float = 0.0) -> None:
        """Add bus-specific attributes."""
        bus_idx = self._get_next_bus_index()
        
        self.attributes[f'B-{bus_idx}\\ID'] = bus_name
        self.attributes[f'B-{bus_idx}\\NM'] = str(num_messages)  # Number of messages
        
        if word_rate > 0:
            self.attributes[f'B-{bus_idx}\\WR'] = f'{word_rate:.1f}'  # Word rate
    
    def add_comment(self, comment: str) -> None:
        """Add a comment to TMATS."""
        com_idx = self._get_next_comment_index()
        self.attributes[f'G\\COM-{com_idx}'] = comment
    
    def add_icd_summary(self, icd_info: Dict[str, Any]) -> None:
        """Add ICD summary information."""
        if 'messages' in icd_info:
            self.add_comment(f"ICD Messages: {icd_info['messages']}")
        
        if 'total_rate_hz' in icd_info:
            self.add_comment(f"Total Message Rate: {icd_info['total_rate_hz']:.1f} Hz")
        
        if 'bus' in icd_info:
            self.add_comment(f"Primary Bus: {icd_info['bus']}")
    
    def build(self) -> str:
        """Build TMATS string."""
        lines = []
        
        # TMATS starts with version
        lines.append('TMATS\\1.0;')
        
        # Add all attributes
        for key in sorted(self.attributes.keys()):
            value = self.attributes[key]
            lines.append(f'{key}:{value};')
        
        # TMATS ends with checksum placeholder (optional)
        lines.append('G\\SHA:0000;')
        
        # Join with CRLF per spec
        tmats_str = '\r\n'.join(lines) + '\r\n'
        
        return tmats_str
    
    def _get_next_channel_index(self) -> int:
        """Get next available channel index."""
        max_idx = 0
        for key in self.attributes.keys():
            if key.startswith('R-') and '\\' in key:
                try:
                    idx = int(key.split('-')[1].split('\\')[0])
                    max_idx = max(max_idx, idx)
                except:
                    pass
        return max_idx + 1
    
    def _get_next_bus_index(self) -> int:
        """Get next available bus index."""
        max_idx = 0
        for key in self.attributes.keys():
            if key.startswith('B-') and '\\' in key:
                try:
                    idx = int(key.split('-')[1].split('\\')[0])
                    max_idx = max(max_idx, idx)
                except:
                    pass
        return max_idx + 1
    
    def _get_next_comment_index(self) -> int:
        """Get next available comment index."""
        max_idx = 0
        for key in self.attributes.keys():
            if key.startswith('G\\COM-'):
                try:
                    idx = int(key.split('-')[1])
                    max_idx = max(max_idx, idx)
                except:
                    pass
        return max_idx + 1


def create_default_tmats(scenario_name: str = "Demo Mission",
                        icd_messages: List[str] = None,
                        total_duration_s: float = 0,
                        total_messages: int = 0) -> str:
    """Create a default TMATS configuration."""
    builder = TMATSBuilder()
    
    # Set basic info
    builder.set_program_name('CH10-1553-FLIGHTGEN')
    builder.set_test_name(scenario_name)
    builder.set_recorder_info()
    
    # Add channels
    builder.add_time_channel(channel_id=0x001)  # Time on Channel 1
    builder.add_1553_channel(channel_id=0x002, bus_name='BUS-A')  # 1553 on Channel 2
    
    # Add summary information
    if icd_messages:
        builder.add_comment(f"ICD Messages: {', '.join(icd_messages)}")
    
    if total_duration_s > 0:
        builder.add_comment(f"Recording Duration: {total_duration_s:.1f} seconds")
    
    if total_messages > 0:
        builder.add_comment(f"Total 1553 Messages: {total_messages}")
    
    builder.add_comment(f"Generated: {datetime.utcnow().isoformat()}Z")
    builder.add_comment("Synthetic flight test data with MIL-STD-1553 bus traffic")
    
    return builder.build()
