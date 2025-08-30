"""
Random data generation for CH10 messages.
Populates all fields with appropriate random values for testing.
"""

import random
import struct
import math
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta


class RandomDataGenerator:
    """Generate random data for all message fields."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize random data generator.
        
        Args:
            config: Random data configuration from scenario
        """
        self.config = config or {}
        self.random_config = self.config.get('random_config', {})
        self.ranges = self.random_config.get('ranges', {})
        
        # Default ranges if not specified
        self.default_ranges = {
            'u16': {'min': 0, 'max': 65535},
            'i16': {'min': -32768, 'max': 32767},
            'bnr16': {'min': -180.0, 'max': 180.0},
            'bcd': {'min': 0, 'max': 9999},
            'discrete': {'values': [0, 1, 2, 3, 4, 5, 6, 7]},
            'status': {'values': [0, 1]},
            'float32': {'min': -1000000.0, 'max': 1000000.0},
        }
        
        # Merge with user-provided ranges
        for dtype, range_config in self.default_ranges.items():
            if dtype not in self.ranges:
                self.ranges[dtype] = range_config
        
        # Track values for increment patterns
        self.increment_values = {}
        
        # Track time for sine patterns
        self.start_time = datetime.now()
        
    def generate_value(self, field: Dict[str, Any], message_name: str = None) -> Union[int, float]:
        """
        Generate a random value for a field.
        
        Args:
            field: Field definition from ICD
            message_name: Optional message name for tracking
            
        Returns:
            Random value appropriate for the field type
        """
        field_type = field.get('type', 'u16')
        field_name = field.get('name', 'unnamed')
        
        # Handle bitfield masks
        if 'mask' in field:
            return self._generate_bitfield_value(field)
        
        # Generate based on type
        if field_type == 'u16':
            return self._generate_u16(field)
        elif field_type == 'i16':
            return self._generate_i16(field)
        elif field_type == 'bnr16':
            return self._generate_bnr16(field)
        elif field_type == 'bcd':
            return self._generate_bcd(field)
        elif field_type == 'discrete':
            return self._generate_discrete(field)
        elif field_type == 'status':
            return self._generate_status(field)
        elif field_type == 'float32':
            return self._generate_float32(field)
        else:
            # Default to u16
            return self._generate_u16(field)
    
    def _generate_bitfield_value(self, field: Dict[str, Any]) -> int:
        """Generate value for a bitfield."""
        mask = field.get('mask', 0xFFFF)
        shift = field.get('shift', 0)
        
        # Count number of bits in mask
        num_bits = bin(mask).count('1')
        
        # Generate random value that fits in the bits
        if num_bits == 1:
            # Single bit - 0 or 1
            value = random.randint(0, 1)
        else:
            # Multi-bit field
            max_value = (1 << num_bits) - 1
            value = random.randint(0, max_value)
        
        return value
    
    def _generate_u16(self, field: Dict[str, Any]) -> int:
        """Generate unsigned 16-bit value."""
        range_config = self.ranges.get('u16', {})
        min_val = field.get('min', range_config.get('min', 0))
        max_val = field.get('max', range_config.get('max', 65535))
        
        # Apply mask if present
        if 'mask' in field and field['mask'] is not None:
            mask = field['mask']
            # Limit to mask range
            max_val = min(max_val, mask) if mask > 0 else max_val
        
        return random.randint(int(min_val), int(max_val))
    
    def _generate_i16(self, field: Dict[str, Any]) -> int:
        """Generate signed 16-bit value."""
        range_config = self.ranges.get('i16', {})
        min_val = field.get('min', range_config.get('min', -32768))
        max_val = field.get('max', range_config.get('max', 32767))
        
        value = random.randint(int(min_val), int(max_val))
        
        # Ensure it fits in 16 bits signed
        if value < 0:
            value = (value + 65536) & 0xFFFF
        
        return value
    
    def _generate_bnr16(self, field: Dict[str, Any]) -> int:
        """Generate BNR16 encoded value."""
        range_config = self.ranges.get('bnr16', {})
        min_val = field.get('min', range_config.get('min', -180.0))
        max_val = field.get('max', range_config.get('max', 180.0))
        
        # Generate random float value
        value = random.uniform(min_val, max_val)
        
        # Apply scale if present
        scale = field.get('scale', 1.0)
        value = value / scale
        
        # Apply offset if present
        offset = field.get('offset', 0.0)
        value = value - offset
        
        # Convert to BNR16 format
        # This is a simplified encoding - adjust as needed
        if value < 0:
            sign = 1
            value = -value
        else:
            sign = 0
        
        # Scale to 15-bit range
        scaled = int(value * 32767 / max_val)
        scaled = min(scaled, 32767)
        
        # Combine sign and magnitude
        bnr_value = (sign << 15) | scaled
        
        return bnr_value
    
    def _generate_bcd(self, field: Dict[str, Any]) -> int:
        """Generate BCD encoded value."""
        range_config = self.ranges.get('bcd', {})
        min_val = field.get('min', range_config.get('min', 0))
        max_val = field.get('max', range_config.get('max', 9999))
        
        # Generate decimal value
        value = random.randint(min_val, max_val)
        
        # Convert to BCD
        bcd_value = 0
        shift = 0
        while value > 0:
            digit = value % 10
            bcd_value |= (digit << shift)
            shift += 4
            value //= 10
        
        return bcd_value
    
    def _generate_discrete(self, field: Dict[str, Any]) -> int:
        """Generate discrete value."""
        range_config = self.ranges.get('discrete', {})
        
        if 'values' in field:
            values = field['values']
        elif 'values' in range_config:
            values = range_config['values']
        else:
            values = [0, 1, 2, 3, 4, 5, 6, 7]
        
        return random.choice(values)
    
    def _generate_status(self, field: Dict[str, Any]) -> int:
        """Generate status bit value."""
        range_config = self.ranges.get('status', {})
        
        if 'values' in field:
            values = field['values']
        elif 'values' in range_config:
            values = range_config['values']
        else:
            values = [0, 1]
        
        return random.choice(values)
    
    def _generate_float32(self, field: Dict[str, Any]) -> float:
        """Generate 32-bit float value."""
        range_config = self.ranges.get('float32', {})
        min_val = field.get('min', range_config.get('min', -1000000.0))
        max_val = field.get('max', range_config.get('max', 1000000.0))
        
        return random.uniform(min_val, max_val)
    
    def generate_message_data(self, message: Dict[str, Any]) -> List[int]:
        """
        Generate random data for all fields in a message.
        
        Args:
            message: Message definition from ICD
            
        Returns:
            List of 16-bit words with random data
        """
        words = []
        message_name = message.get('name', 'unnamed')
        
        # Process each word
        for word_def in message.get('words', []):
            if isinstance(word_def, dict):
                word_value = 0
                
                # Check if word has bitfields
                if 'fields' in word_def:
                    # Process each bitfield
                    for field in word_def['fields']:
                        field_value = self.generate_value(field, message_name)
                        
                        # Apply mask and shift
                        mask = field.get('mask', 0xFFFF)
                        shift = field.get('shift', 0)
                        
                        # Ensure value fits in mask
                        field_value &= (mask >> shift)
                        
                        # Apply to word
                        word_value |= (field_value << shift)
                else:
                    # Single field word
                    word_value = self.generate_value(word_def, message_name)
                
                # Ensure 16-bit value
                word_value &= 0xFFFF
                words.append(word_value)
            else:
                # Simple word value
                words.append(random.randint(0, 65535))
        
        return words
    
    def generate_all_messages(self, icd: Dict[str, Any]) -> Dict[str, List[int]]:
        """
        Generate random data for all messages in an ICD.
        
        Args:
            icd: ICD definition
            
        Returns:
            Dictionary mapping message names to word lists
        """
        message_data = {}
        
        for message in icd.get('messages', []):
            message_name = message.get('name', 'unnamed')
            data = self.generate_message_data(message)
            message_data[message_name] = data
        
        return message_data
    
    def populate_all_fields(self, icd: Dict[str, Any]) -> bool:
        """
        Verify that all fields can be populated with data.
        
        Args:
            icd: ICD definition
            
        Returns:
            True if all fields can be populated
        """
        try:
            # Generate data for all messages
            message_data = self.generate_all_messages(icd)
            
            # Verify each message has data
            for message in icd.get('messages', []):
                message_name = message.get('name', 'unnamed')
                if message_name not in message_data:
                    print(f"Warning: No data generated for message {message_name}")
                    return False
                
                # Check word count
                expected_words = len(message.get('words', []))
                actual_words = len(message_data[message_name])
                if expected_words != actual_words:
                    print(f"Warning: Word count mismatch for {message_name}: expected {expected_words}, got {actual_words}")
                    return False
            
            return True
            
        except Exception as e:
            print(f"Error generating random data: {e}")
            return False


def create_random_scenario() -> Dict[str, Any]:
    """Create a default random data scenario."""
    return {
        'name': 'random_test',
        'description': 'Random test data generation',
        'duration': 10,
        'data_mode': 'random',
        'random_config': {
            'populate_all_fields': True,
            'ranges': {
                'u16': {'min': 0, 'max': 65535},
                'i16': {'min': -32768, 'max': 32767},
                'bnr16': {'min': -180.0, 'max': 180.0},
                'bcd': {'min': 0, 'max': 9999},
                'discrete': {'values': [0, 1, 2, 3, 4, 5, 6, 7]},
                'status': {'values': [0, 1]}
            }
        }
    }
