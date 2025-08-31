"""ICD (Interface Control Document) definitions and validation."""

import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, field


@dataclass
class WordDefinition:
    """Definition of a single word in a message."""
    name: str
    encode: str  # u16, i16, bnr16, bcd, float32_split
    src: Optional[str] = None  # Source path for dynamic values
    const: Optional[Union[int, float]] = None  # Constant value
    scale: float = 1.0
    offset: float = 0.0
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    word_order: Optional[str] = None  # For float32_split: 'lsw_msw' or 'msw_lsw'
    rounding: str = 'nearest'  # Rounding mode for bnr16 encoding
    mask: Optional[int] = None  # Bit mask for bitfield packing (0x0000-0xFFFF)
    shift: Optional[int] = None  # Bit shift for bitfield packing (0-15)
    word_index: Optional[int] = None  # Which word this field belongs to (for multi-field words)
    
    def validate(self) -> List[str]:
        """Validate word definition and return list of errors."""
        errors = []
        
        # Must have either src or const
        if self.src is None and self.const is None:
            errors.append("Word must have either 'src' or 'const'")
        
        # Validate encoding
        valid_encodings = ['u16', 'i16', 'bnr16', 'bcd', 'float32_split']
        if self.encode not in valid_encodings:
            errors.append("invalid encoding")
        
        # Validate float32_split specific requirements
        if self.encode == 'float32_split':
            if self.word_order not in ['lsw_msw', 'msw_lsw']:
                errors.append("invalid word_order")
            # float32_split cannot use mask/shift
            if self.mask is not None or self.shift is not None:
                errors.append("float32_split cannot use mask/shift")
        
        # Validate BNR16 doesn't use mask/shift (full word only)
        if self.encode == 'bnr16' and (self.mask is not None or self.shift is not None):
            errors.append("bnr16 must use full word (no mask/shift)")
        
        # Validate mask and shift for bitfield packing
        if self.mask is not None or self.shift is not None:
            # Both must be present for bitfield packing
            if self.mask is None or self.shift is None:
                errors.append("Both mask and shift must be specified for bitfield packing")
            else:
                # Validate mask range
                if not (0 <= self.mask <= 0xFFFF):
                    errors.append(f"Mask must be 0-65535, got {self.mask}")
                
                # Validate shift range
                if not (0 <= self.shift <= 15):
                    errors.append(f"Shift must be 0-15, got {self.shift}")
                
                # Check that shifted mask doesn't overflow
                if self.mask != 0:
                    # Find the highest bit set in mask
                    highest_bit = self.mask.bit_length()
                    if highest_bit + self.shift > 16:
                        errors.append(f"Mask 0x{self.mask:04X} with shift {self.shift} exceeds 16 bits")
        
        return errors
    
    def get_word_count(self) -> int:
        """Get the number of words this definition represents."""
        if self.encode == 'float32_split':
            return 2  # float32_split uses 2 words
        else:
            return 1


@dataclass
class MessageDefinition:
    """Definition of a 1553 message."""
    name: str
    rate_hz: float
    rt: int  # Remote Terminal address
    tr: str  # Transfer type: 'BC2RT', 'RT2BC', 'BC2RT2BC'
    sa: int  # Subaddress
    wc: int  # Word count
    words: List[WordDefinition] = field(default_factory=list)
    
    def validate(self) -> List[str]:
        """Validate message definition and return list of errors."""
        errors = []
        
        # Validate rate
        if self.rate_hz <= 0 or self.rate_hz > 1000:
            errors.append(f"Rate must be between 0 and 1000 Hz, got {self.rate_hz}")
        
        # Validate RT address
        if not (0 <= self.rt <= 31):
            errors.append(f"RT address must be 0-31, got {self.rt}")
        
        # Validate SA
        if not (0 <= self.sa <= 31):
            errors.append(f"Subaddress must be 0-31, got {self.sa}")
        
        # Validate word count
        if self.wc <= 0:
            errors.append(f"Word count must be positive, got {self.wc}")
        
        # Validate transfer type
        valid_tr = ['BC2RT', 'RT2BC', 'BC2RT2BC']
        if self.tr not in valid_tr:
            errors.append(f"Transfer type must be one of {valid_tr}, got '{self.tr}'")
        
        # Validate words and check for bitfield overlaps
        word_allocations = {}  # Track bit allocations per word index
        
        for word in self.words:
            # Validate individual word
            errors.extend(word.validate())
            
            # Handle bitfield packing for overlap detection
            if word.mask is not None and word.shift is not None:
                # Determine which word this field belongs to
                word_idx = word.word_index if word.word_index is not None else 0
                
                # Initialize bit tracking for this word if needed
                if word_idx not in word_allocations:
                    word_allocations[word_idx] = 0
                
                # Calculate the actual bit positions used
                shifted_mask = (word.mask << word.shift) & 0xFFFF
                
                # Check for overlap with existing allocations
                if word_allocations[word_idx] & shifted_mask:
                    errors.append(f"Bitfield '{word.name}' overlaps with another field in word {word_idx}")
                
                # Mark these bits as allocated
                word_allocations[word_idx] |= shifted_mask
        
        # Simple word count validation based on word_index values
        if self.words:
            # Find the maximum word_index value
            word_indices = [word.word_index for word in self.words if word.word_index is not None]
            if word_indices:
                max_word_idx = max(word_indices)
                # Word count should be max_word_idx + 1 (since indices are 0-based)
                # This means if you have indices 0-31, you need 32 words total
                expected_word_count = max_word_idx + 1
                
                if expected_word_count != self.wc:
                    errors.append(f"Word count mismatch: declared {self.wc}, calculated {expected_word_count}")
            else:
                # No word_index values defined, count total words
                total_words = sum(word.get_word_count() for word in self.words)
                if total_words != self.wc:
                    errors.append(f"Word count mismatch: declared {self.wc}, calculated {total_words}")
        else:
            # No words defined
            if self.wc != 0:
                errors.append(f"Word count mismatch: declared {self.wc}, but no words defined")
        
        return errors
    
    def is_receive(self) -> bool:
        """Check if this is a receive message (BC2RT from RT perspective)."""
        return self.tr == 'BC2RT'
    
    def is_transmit(self) -> bool:
        """Check if this is a transmit message (RT2BC from RT perspective)."""
        return self.tr == 'RT2BC'


@dataclass
class ICDDefinition:
    """Complete ICD definition for a bus."""
    bus: str  # 'A' or 'B'
    messages: List[MessageDefinition] = field(default_factory=list)
    
    def validate(self) -> List[str]:
        """Validate ICD definition and return list of errors."""
        errors = []
        
        # Validate bus
        if self.bus not in ['A', 'B']:
            errors.append(f"Bus must be 'A' or 'B', got '{self.bus}'")
        
        # Check for duplicate message names
        seen_names = set()
        duplicate_names = []
        for msg in self.messages:
            if msg.name in seen_names:
                duplicate_names.append(msg.name)
            seen_names.add(msg.name)
        
        # Report duplicate name errors
        if duplicate_names:
            errors.append(f"Duplicate message names: {', '.join(duplicate_names)}")
        
        # Validate messages
        for i, msg in enumerate(self.messages):
            msg_errors = msg.validate()
            # Prefix message errors with message name for clarity
            for error in msg_errors:
                errors.append(f"Message '{msg.name}' (index {i}): {error}")
        
        return errors
    
    def get_total_bandwidth_words_per_sec(self) -> float:
        """Calculate total bandwidth in words per second."""
        total = 0.0
        for msg in self.messages:
            total += msg.rate_hz * msg.wc
        return total
    
    def get_unique_rates(self) -> List[float]:
        """Get list of unique message rates."""
        return sorted(list(set(msg.rate_hz for msg in self.messages)))
    
    def get_messages_by_rate(self, rate_hz: float) -> List[MessageDefinition]:
        """Get messages with a specific rate."""
        return [msg for msg in self.messages if msg.rate_hz == rate_hz]
    
    def get_message_by_name(self, name: str) -> Optional[MessageDefinition]:
        """Get message by name."""
        for msg in self.messages:
            if msg.name == name:
                return msg
        return None


def load_icd(filepath: Path) -> ICDDefinition:
    """Load ICD from YAML file."""
    with open(filepath, 'r') as f:
        data = yaml.safe_load(f)
    
    # Parse messages
    messages = []
    for msg_data in data.get('messages', []):
        words = []
        for word_data in msg_data.get('words', []):
            word = WordDefinition(**word_data)
            words.append(word)
        
        msg = MessageDefinition(
            name=msg_data['name'],
            rate_hz=msg_data['rate_hz'],
            rt=msg_data['rt'],
            tr=msg_data['tr'],
            sa=msg_data['sa'],
            wc=msg_data['wc'],
            words=words
        )
        messages.append(msg)
    
    icd = ICDDefinition(
        bus=data['bus'],
        messages=messages
    )
    
    # Validate and raise exceptions for critical errors
    errors = icd.validate()
    if errors:
        # Show all validation errors for better debugging
        error_message = f"ICD validation failed with {len(errors)} errors:\n"
        error_message += "\n".join(f"  - {error}" for error in errors)
        raise ValueError(error_message)
    
    return icd


def validate_icd_file(filepath: Path) -> Dict[str, Any]:
    """Validate ICD file and return validation results."""
    try:
        icd = load_icd(filepath)
        errors = icd.validate()
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'icd': icd
        }
    except Exception as e:
        return {
            'valid': False,
            'errors': [f"Failed to load ICD: {e}"],
            'icd': None
        }
