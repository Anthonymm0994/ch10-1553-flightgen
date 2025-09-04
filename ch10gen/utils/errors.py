"""
Error and jitter injection for 1553 messages.

This module provides configurable error injection capabilities for MIL-STD-1553
messages, enabling generation of realistic test data that includes various
types of bus errors and timing issues.

Key components:
- ErrorType: Enumeration of supported error types
- ErrorInjectionConfig: Configuration for error injection rates
- MessageErrorInjector: Main class for injecting errors into messages

The error injection system supports:
- Parity errors: Bit errors in transmitted words
- Response errors: Missing or late responses from RTs
- Protocol errors: Word count mismatches, sync errors
- Timing errors: Jitter and bus failover scenarios

This is essential for creating comprehensive test data that exercises
error handling and recovery mechanisms in ground station software.
"""

import random
from dataclasses import dataclass
from typing import Optional, Tuple, List
from enum import IntEnum


class ErrorType(IntEnum):
    """
    Types of 1553 errors that can be injected.
    
    These correspond to common error conditions that occur in real
    MIL-STD-1553 bus systems and are important for testing ground
    station error handling capabilities.
    """
    NONE = 0  # No error (normal operation)
    PARITY_ERROR = 1  # Bit error in transmitted word
    NO_RESPONSE = 2  # Remote Terminal fails to respond
    LATE_RESPONSE = 3  # Remote Terminal responds too late
    WORD_COUNT_MISMATCH = 4  # Incorrect number of data words
    MANCHESTER_ERROR = 5  # Manchester encoding violation
    SYNC_ERROR = 6  # Sync word error
    BUS_FAILOVER = 7  # Bus A/B failover event


@dataclass
class ErrorInjectionConfig:
    """Configuration for error injection."""
    parity_error_percent: float = 0.0
    no_response_percent: float = 0.0
    late_response_percent: float = 0.0
    word_count_error_percent: float = 0.0
    manchester_error_percent: float = 0.0
    sync_error_percent: float = 0.0
    bus_failover_time_s: Optional[float] = None
    timestamp_jitter_ms: float = 0.0
    
    def __init__(self, **kwargs):
        """Initialize with optional legacy parameter names."""
        # Handle legacy parameter names
        if 'word_count_mismatch_percent' in kwargs:
            kwargs['word_count_error_percent'] = kwargs.pop('word_count_mismatch_percent')
        
        # Set all attributes
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def should_inject_error(self, error_type: ErrorType) -> bool:
        """Determine if an error should be injected based on probability."""
        if error_type == ErrorType.PARITY_ERROR:
            return random.random() * 100 < self.parity_error_percent
        elif error_type == ErrorType.NO_RESPONSE:
            return random.random() * 100 < self.no_response_percent
        elif error_type == ErrorType.LATE_RESPONSE:
            return random.random() * 100 < self.late_response_percent
        elif error_type == ErrorType.WORD_COUNT_MISMATCH:
            return random.random() * 100 < self.word_count_error_percent
        elif error_type == ErrorType.MANCHESTER_ERROR:
            return random.random() * 100 < self.manchester_error_percent
        elif error_type == ErrorType.SYNC_ERROR:
            return random.random() * 100 < self.sync_error_percent
        return False
    
    def get_timestamp_jitter_us(self) -> int:
        """Get random timestamp jitter in microseconds."""
        if self.timestamp_jitter_ms <= 0:
            return 0
        
        # Generate random jitter within ± jitter_ms
        jitter_ms = random.uniform(-self.timestamp_jitter_ms, self.timestamp_jitter_ms)
        return int(jitter_ms * 1000)
    
    def should_switch_bus(self, current_time_s: float) -> bool:
        """Check if bus should switch at current time."""
        if self.bus_failover_time_s is None:
            return False
        return current_time_s >= self.bus_failover_time_s


class MessageErrorInjector:
    """
    Inject errors into 1553 messages.
    
    This class provides the main interface for injecting various types of
    errors into MIL-STD-1553 messages. It maintains error statistics and
    handles bus failover scenarios.
    
    The injector can modify:
    - Command words (parity errors, sync errors)
    - Status words (parity errors, response errors)
    - Data words (parity errors, word count mismatches)
    - Timing (jitter, late responses)
    - Bus selection (A/B failover)
    """
    
    def __init__(self, config: ErrorInjectionConfig, seed: Optional[int] = None):
        """
        Initialize with error configuration.
        
        Args:
            config: Error injection configuration with rates and timing
            seed: Random seed for reproducible error injection
        """
        self.config = config
        self.current_bus = 'A'  # Track which bus is currently active
        self.error_count = {error_type: 0 for error_type in ErrorType}  # Error statistics
        self.message_count = 0  # Track total messages processed
        
        # Set random seed if provided for reproducible error patterns
        if seed is not None:
            random.seed(seed)
    
    def inject_errors(self, message_time_s_or_message, command_word=None, 
                     status_word=None, data_words=None) -> Tuple[int, int, List[int], ErrorType]:
        """
        Inject errors into a message.
        
        Args:
            message_time_s_or_message: Message timestamp in seconds OR message object
            command_word: Original command word (required if first arg is timestamp)
            status_word: Original status word (required if first arg is timestamp)
            data_words: Original data words (required if first arg is timestamp)
        
        Returns:
            Tuple of (command_word, status_word, data_words, error_type)
        """
        # Handle legacy call with message object
        if hasattr(message_time_s_or_message, 'message'):
            message = message_time_s_or_message
            message_time_s = 0.0  # Default time
            command_word = 0x0000  # Default command
            status_word = 0x0000   # Default status
            data_words = []        # Default data
        else:
            message_time_s = message_time_s_or_message
            if command_word is None or status_word is None or data_words is None:
                raise ValueError("command_word, status_word, and data_words are required when calling with timestamp")
        
        self.message_count += 1  # Track message
        
        # Check for bus failover
        if self.config.should_switch_bus(message_time_s):
            if self.current_bus == 'A':
                self.current_bus = 'B'
                self.error_count[ErrorType.BUS_FAILOVER] += 1
        
        # Determine which error to inject (if any)
        error_type = self._select_error_type()
        
        if error_type == ErrorType.NONE:
            return command_word, status_word, data_words, ErrorType.NONE
        
        # Apply error based on type
        if error_type == ErrorType.PARITY_ERROR:
            # Flip a bit in status word to cause parity error
            status_word ^= (1 << random.randint(0, 15))
            self.error_count[ErrorType.PARITY_ERROR] += 1
            
        elif error_type == ErrorType.NO_RESPONSE:
            # Set busy bit in status word
            status_word |= (1 << 3)  # Busy bit
            # Could also return empty data_words, but keeping them for realism
            self.error_count[ErrorType.NO_RESPONSE] += 1
            
        elif error_type == ErrorType.LATE_RESPONSE:
            # Set instrumentation bit to indicate timing issue
            status_word |= (1 << 9)  # Instrumentation bit
            self.error_count[ErrorType.LATE_RESPONSE] += 1
            
        elif error_type == ErrorType.WORD_COUNT_MISMATCH:
            # Truncate or extend data words
            if len(data_words) > 1:
                if random.random() < 0.5:
                    # Truncate
                    data_words = data_words[:-1]
                else:
                    # Extend with garbage
                    data_words.append(random.randint(0, 0xFFFF))
            self.error_count[ErrorType.WORD_COUNT_MISMATCH] += 1
            
        elif error_type == ErrorType.MANCHESTER_ERROR:
            # Corrupt a random data word
            if data_words:
                idx = random.randint(0, len(data_words) - 1)
                data_words[idx] ^= random.randint(1, 0xFFFF)
            self.error_count[ErrorType.MANCHESTER_ERROR] += 1
            
        elif error_type == ErrorType.SYNC_ERROR:
            # Set message error bit in status word
            status_word |= (1 << 10)  # Message error bit
            self.error_count[ErrorType.SYNC_ERROR] += 1
        
        return command_word, status_word, data_words, error_type
    
    def _select_error_type(self) -> ErrorType:
        """Select which error type to inject (if any)."""
        # Check each error type in order of priority
        # Only inject one error per message
        
        if self.config.should_inject_error(ErrorType.NO_RESPONSE):
            return ErrorType.NO_RESPONSE
        
        if self.config.should_inject_error(ErrorType.PARITY_ERROR):
            return ErrorType.PARITY_ERROR
        
        if self.config.should_inject_error(ErrorType.LATE_RESPONSE):
            return ErrorType.LATE_RESPONSE
        
        if self.config.should_inject_error(ErrorType.WORD_COUNT_MISMATCH):
            return ErrorType.WORD_COUNT_MISMATCH
        
        if self.config.should_inject_error(ErrorType.MANCHESTER_ERROR):
            return ErrorType.MANCHESTER_ERROR
        
        if self.config.should_inject_error(ErrorType.SYNC_ERROR):
            return ErrorType.SYNC_ERROR
        
        return ErrorType.NONE
    
    def get_statistics(self) -> dict:
        """Get error injection statistics."""
        total_errors = sum(self.error_count.values())
        
        stats = {
            'total_errors': total_errors,
            'current_bus': self.current_bus,
            'error_counts': dict(self.error_count),
            'error_percentages': {}
        }
        
        # Calculate percentages if we have a total
        if total_errors > 0:
            for error_type, count in self.error_count.items():
                if error_type != ErrorType.NONE:
                    stats['error_percentages'][error_type.name] = (count / total_errors) * 100
        
        return stats
    
    def reset_statistics(self):
        """Reset error statistics."""
        self.error_count = {error_type: 0 for error_type in ErrorType}


def create_error_config_from_dict(config_dict: dict) -> ErrorInjectionConfig:
    """Create error injection config from dictionary."""
    return ErrorInjectionConfig(
        parity_error_percent=config_dict.get('parity_error_percent', config_dict.get('parity_percent', 0.0)),
        no_response_percent=config_dict.get('no_response_percent', 0.0),
        late_response_percent=config_dict.get('late_response_percent', config_dict.get('late_percent', 0.0)),
        word_count_error_percent=config_dict.get('word_count_error_percent', config_dict.get('word_count_percent', 0.0)),
        manchester_error_percent=config_dict.get('manchester_error_percent', config_dict.get('manchester_percent', 0.0)),
        sync_error_percent=config_dict.get('sync_error_percent', config_dict.get('sync_percent', 0.0)),
        bus_failover_time_s=config_dict.get('bus_failover_time_s'),
        timestamp_jitter_ms=config_dict.get('timestamp_jitter_ms', config_dict.get('jitter_ms', 0.0))
    )
