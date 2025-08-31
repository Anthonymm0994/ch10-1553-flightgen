"""Simple tests for error injection that match actual code."""

import pytest
import random

from ch10gen.utils.errors import (
    ErrorType,
    ErrorInjectionConfig,
    MessageErrorInjector,
    create_error_config_from_dict
)


class TestErrorType:
    """Test ErrorType enum."""
    
    def test_error_types(self):
        """Test error type values."""
        assert ErrorType.NONE == 0
        assert ErrorType.PARITY_ERROR == 1
        assert ErrorType.NO_RESPONSE == 2
        assert ErrorType.LATE_RESPONSE == 3
        assert ErrorType.WORD_COUNT_MISMATCH == 4
        assert ErrorType.MANCHESTER_ERROR == 5
        assert ErrorType.SYNC_ERROR == 6
        assert ErrorType.BUS_FAILOVER == 7


class TestErrorInjectionConfig:
    """Test error injection configuration."""
    
    def test_default_config(self):
        """Test default configuration has no errors."""
        config = ErrorInjectionConfig()
        
        assert config.parity_error_percent == 0.0
        assert config.no_response_percent == 0.0
        assert config.late_response_percent == 0.0
        assert config.word_count_error_percent == 0.0
        assert config.manchester_error_percent == 0.0
        assert config.sync_error_percent == 0.0
        assert config.bus_failover_time_s is None
        assert config.timestamp_jitter_ms == 0.0
        
    def test_should_inject_error_zero_percent(self):
        """Test no error injection with 0% probability."""
        config = ErrorInjectionConfig()
        
        # With 0% probability, should never inject
        for _ in range(10):
            assert config.should_inject_error(ErrorType.PARITY_ERROR) == False
            assert config.should_inject_error(ErrorType.NO_RESPONSE) == False
            
    def test_should_inject_error_100_percent(self):
        """Test error injection with 100% probability."""
        config = ErrorInjectionConfig(
            parity_error_percent=100.0,
            no_response_percent=100.0
        )
        
        # With 100% probability, should always inject
        for _ in range(10):
            assert config.should_inject_error(ErrorType.PARITY_ERROR) == True
            assert config.should_inject_error(ErrorType.NO_RESPONSE) == True
            
    def test_get_timestamp_jitter_zero(self):
        """Test timestamp jitter with zero configured."""
        config = ErrorInjectionConfig(timestamp_jitter_ms=0.0)
        
        # With 0 jitter, should always return 0
        for _ in range(10):
            assert config.get_timestamp_jitter_us() == 0
            
    def test_get_timestamp_jitter_nonzero(self):
        """Test timestamp jitter with non-zero value."""
        config = ErrorInjectionConfig(timestamp_jitter_ms=10.0)
        
        jitters = [config.get_timestamp_jitter_us() for _ in range(100)]
        
        # Should have variation
        assert min(jitters) < max(jitters)
        
        # Should be within expected range (-10000 to +10000 microseconds)
        assert all(-10000 <= j <= 10000 for j in jitters)


class TestMessageErrorInjector:
    """Test MessageErrorInjector class."""
    
    def test_injector_init(self):
        """Test error injector initialization."""
        config = ErrorInjectionConfig()
        injector = MessageErrorInjector(config)
        
        assert injector.config == config
        assert injector.message_count == 0
        assert isinstance(injector.error_count, dict)
        assert all(count == 0 for count in injector.error_count.values())
        
    def test_injector_with_config(self):
        """Test injector with custom config."""
        config = ErrorInjectionConfig(
            parity_error_percent=10.0,
            no_response_percent=5.0
        )
        injector = MessageErrorInjector(config)
        
        assert injector.config.parity_error_percent == 10.0
        assert injector.config.no_response_percent == 5.0


class TestCreateErrorConfig:
    """Test creating error config from dict."""
    
    def test_create_from_empty_dict(self):
        """Test creating config from empty dict."""
        config = create_error_config_from_dict({})
        
        # Should have all defaults
        assert config.parity_error_percent == 0.0
        assert config.no_response_percent == 0.0
        
    def test_create_from_dict_with_values(self):
        """Test creating config from dict with values."""
        data = {
            'parity_error_percent': 2.5,
            'no_response_percent': 1.0,
            'timestamp_jitter_ms': 5.0
        }
        
        config = create_error_config_from_dict(data)
        
        assert config.parity_error_percent == 2.5
        assert config.no_response_percent == 1.0
        assert config.timestamp_jitter_ms == 5.0
        
    def test_create_from_dict_partial(self):
        """Test creating config from dict with partial values."""
        data = {
            'sync_error_percent': 0.5
        }
        
        config = create_error_config_from_dict(data)
        
        # Specified value should be set
        assert config.sync_error_percent == 0.5
        
        # Others should be default
        assert config.parity_error_percent == 0.0
        assert config.no_response_percent == 0.0
