#!/usr/bin/env python3
"""
Generate large test ICDs with complex bitfield patterns for testing.
This creates ICDs with many messages and complex mask/shift combinations.
"""

import yaml
import random
from pathlib import Path
from typing import Dict, List, Any

class TestICDGenerator:
    """Generate test ICDs with complex bitfield patterns."""
    
    def __init__(self):
        self.total_bitfields = 0
        self.bitfield_patterns = [
            # Single bit fields - mask is unshifted, shift positions it
            {'mask': 0x0001, 'shift': 0},   # Bit 0
            {'mask': 0x0001, 'shift': 1},   # Bit 1
            {'mask': 0x0001, 'shift': 2},   # Bit 2
            {'mask': 0x0001, 'shift': 3},   # Bit 3
            {'mask': 0x0001, 'shift': 4},   # Bit 4
            {'mask': 0x0001, 'shift': 5},   # Bit 5
            {'mask': 0x0001, 'shift': 6},   # Bit 6
            {'mask': 0x0001, 'shift': 7},   # Bit 7
            {'mask': 0x0001, 'shift': 8},   # Bit 8
            {'mask': 0x0001, 'shift': 9},   # Bit 9
            {'mask': 0x0001, 'shift': 10},  # Bit 10
            {'mask': 0x0001, 'shift': 11},  # Bit 11
            {'mask': 0x0001, 'shift': 12},  # Bit 12
            {'mask': 0x0001, 'shift': 13},  # Bit 13
            {'mask': 0x0001, 'shift': 14},  # Bit 14
            {'mask': 0x0001, 'shift': 15},  # Bit 15
            
            # Multi-bit fields
            {'mask': 0x0003, 'shift': 0},   # 2 bits at position 0
            {'mask': 0x000F, 'shift': 0},   # 4 bits at position 0
            {'mask': 0x00FF, 'shift': 0},   # 8 bits at position 0
            {'mask': 0x03FF, 'shift': 0},   # 10 bits at position 0
            {'mask': 0x0FFF, 'shift': 0},   # 12 bits at position 0
            {'mask': 0x3FFF, 'shift': 0},   # 14 bits at position 0
            {'mask': 0x7FFF, 'shift': 0},   # 15 bits at position 0
            
            # Shifted multi-bit fields (mask is unshifted, shift positions it)
            {'mask': 0x000F, 'shift': 4},   # 4 bits at position 4
            {'mask': 0x000F, 'shift': 8},   # 4 bits at position 8
            {'mask': 0x000F, 'shift': 12},  # 4 bits at position 12
            {'mask': 0x000F, 'shift': 6},   # 4 bits at position 6
            {'mask': 0x001F, 'shift': 8},   # 5 bits at position 8
            {'mask': 0x001F, 'shift': 10},  # 5 bits at position 10 (5+10=15, OK)
            
            # Complex patterns
            {'mask': 0x5555, 'shift': 0},   # Alternating bits (odd)
            {'mask': 0xAAAA, 'shift': 0},   # Alternating bits (even)
            {'mask': 0x3333, 'shift': 0},   # Every 2 bits pattern
            {'mask': 0xCCCC, 'shift': 0},   # Every 2 bits pattern (shifted)
        ]
        
        self.field_types = [
            'u16',      # Unsigned 16-bit
            'i16',      # Signed 16-bit
            'bnr16',    # Binary coded
            'bcd',      # Binary coded decimal
        ]
        
    def generate_complex_word(self, word_num: int, num_fields: int = None) -> List[Dict[str, Any]]:
        """Generate a word with complex bitfield patterns."""
        if num_fields is None:
            num_fields = random.randint(1, 8)  # 1-8 fields per word
        
        fields = []
        
        # Track used bits to avoid overlaps
        used_bits = 0
        available_patterns = self.bitfield_patterns.copy()
        random.shuffle(available_patterns)
        
        for field_idx in range(num_fields):
            if not available_patterns:
                break
                
            # Find a pattern that doesn't overlap
            for pattern in available_patterns:
                mask = pattern['mask']
                shift = pattern['shift']
                
                # Check if bits are available (mask shifted to actual position)
                shifted_mask = mask << shift
                if (used_bits & shifted_mask) == 0:
                    field = {
                        'name': f'field_{word_num}_{field_idx}',
                        'encode': 'u16',
                        'mask': mask,
                        'shift': shift,
                        'word_index': word_num,
                        'const': 0  # Required by ICD loader
                    }
                    
                    # Add scaling for some fields
                    if random.random() > 0.7:
                        field['scale'] = random.choice([0.1, 0.01, 0.001, 10, 100])
                    
                    # Add offset for some fields
                    if random.random() > 0.8:
                        field['offset'] = random.choice([-100, -50, -10, 10, 50, 100])
                    
                    fields.append(field)
                    used_bits |= shifted_mask  # Mark the shifted position as used
                    available_patterns.remove(pattern)
                    self.total_bitfields += 1  # Track bitfield count
                    break
        
        return fields
    
    def generate_message(self, msg_num: int, sub_address: int, num_words: int = None) -> Dict[str, Any]:
        """Generate a message with multiple words."""
        if num_words is None:
            num_words = random.randint(1, 32)  # 1-32 words per message
        
        message = {
            'name': f'TEST_MSG_{msg_num:04d}_RT{(msg_num % 31) + 1}_SA{sub_address}',
            'rt': (msg_num % 31) + 1,  # RT address 1-31
            'tr': random.choice(['BC2RT', 'RT2BC']),  # Transfer type
            'sa': sub_address,  # Subaddress
            'wc': num_words,  # Word count
            'rate_hz': random.choice([1, 5, 10, 20, 50, 100]),  # Hz
            'words': []
        }
        
        for word_num in range(num_words):
            # Vary the complexity
            if random.random() > 0.3:
                # Complex word with multiple fields
                fields = self.generate_complex_word(word_num)
                message['words'].extend(fields)  # Add all fields for this word
                self.total_bitfields += len(fields)
            else:
                # Simple word with single field
                word = {
                    'name': f'word_{word_num}',
                    'encode': random.choice(self.field_types),
                    'const': 0  # Required by ICD loader
                }
                
                # Add some attributes
                if random.random() > 0.5:
                    word['scale'] = random.choice([0.1, 0.01, 0.001, 10, 100])
                if random.random() > 0.7:
                    word['offset'] = random.choice([-100, -50, -10, 10, 50, 100])
            
                message['words'].append(word)
        
        return message
    
    def generate_icd(self, num_messages: int, name: str = None) -> Dict[str, Any]:
        """Generate a complete ICD with specified number of messages."""
        if name is None:
            name = f'test_icd_{num_messages}_messages'
        
        icd = {
            'name': name,
            'bus': 'B',  # Default to bus B
            'description': f'Test ICD with {num_messages} messages for validation',
            'version': '1.0.0',
            'messages': []
        }
        
        # Track used RT/SA combinations
        used_combinations = set()
        
        for msg_num in range(num_messages):
            # Calculate unique RT/SA
            rt = (msg_num % 31) + 1
            sa = ((msg_num // 31) % 30) + 1
            
            # Ensure uniqueness
            attempts = 0
            while (rt, sa) in used_combinations and attempts < 1000:
                sa = (sa % 30) + 1
                if sa == 1:
                    rt = (rt % 31) + 1
                attempts += 1
            
            used_combinations.add((rt, sa))
            
            # Override RT in message generation
            message = self.generate_message(msg_num, sa)
            message['rt'] = rt  # Override with unique RT
            icd['messages'].append(message)
        
        return icd
    
    def estimate_line_count(self, icd: Dict[str, Any]) -> int:
        """Estimate the number of lines in the YAML output."""
        # Rough estimate based on structure
        lines = 10  # Header lines
        
        for message in icd['messages']:
            lines += 5  # Message header
            for word in message.get('words', []):
                if isinstance(word, dict):
                    lines += 3  # Word header
                    if 'fields' in word:
                        lines += len(word['fields']) * 5  # Each field ~5 lines
                    else:
                        lines += 2  # Simple word
        
        return lines
    
    def save_icd(self, icd: Dict[str, Any], filename: str = None):
        """Save ICD to YAML file."""
        if filename is None:
            filename = f"{icd['name']}.yaml"
        
        output_dir = Path(__file__).parent.parent / 'icd' / 'test'
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_path = output_dir / filename
        
        with open(output_path, 'w') as f:
            yaml.dump(icd, f, default_flow_style=False, sort_keys=False, indent=2)
        
        line_count = self.estimate_line_count(icd)
        print(f"Generated ICD saved to: {output_path}")
        print(f"Estimated lines: {line_count:,}")
        print(f"Messages: {len(icd['messages'])}")
        
        total_words = sum(len(msg.get('words', [])) for msg in icd['messages'])
        print(f"Total words: {total_words}")
        
        total_fields = 0
        for msg in icd['messages']:
            for word in msg.get('words', []):
                if isinstance(word, dict) and 'fields' in word:
                    total_fields += len(word['fields'])
        print(f"Total bitfields: {total_fields}")
        
        return output_path


def main():
    """Generate test ICDs of various sizes."""
    generator = TestICDGenerator()
    
    # Generate small test ICD (for quick testing)
    print("\n=== Generating Small Test ICD ===")
    small_icd = generator.generate_icd(10)
    generator.save_icd(small_icd, 'test_small.yaml')
    
    # Generate medium test ICD
    print("\n=== Generating Medium Test ICD ===")
    medium_icd = generator.generate_icd(50)
    generator.save_icd(medium_icd, 'test_medium.yaml')
    
    # Generate large test ICD (100+ messages, ~8000 lines)
    print("\n=== Generating Large Test ICD ===")
    large_icd = generator.generate_icd(150)
    generator.save_icd(large_icd, 'test_large.yaml')
    
    # Generate extra large test ICD (200+ messages, ~10000+ lines)
    print("\n=== Generating Extra Large Test ICD ===")
    xlarge_icd = generator.generate_icd(250)
    generator.save_icd(xlarge_icd, 'test_xlarge.yaml')
    
    print("\n✅ All test ICDs generated successfully!")
    print("Test ICDs are saved in: icd/test/")


if __name__ == '__main__':
    main()
