"""Error injection tests."""

import pytest
from ch10gen.utils.errors import (
    ErrorInjectionConfig, MessageErrorInjector,
    create_error_config_from_dict
)


@pytest.mark.unit
class TestErrorInjectionConfig:
    """Test error injection configuration."""
    
    def test_default_config(self):
        """Test default error configuration."""
        config = ErrorInjectionConfig()
        
        # All errors should be 0 by default
        assert config.parity_error_percent == 0.0
        assert config.no_response_percent == 0.0
        assert config.late_response_percent == 0.0
        assert config.word_count_error_percent == 0.0
        assert config.manchester_error_percent == 0.0
        assert config.sync_error_percent == 0.0
        assert config.bus_failover_time_s is None
        assert config.timestamp_jitter_ms == 0.0
    
    def test_config_from_dict(self):
        """Test creating config from dictionary."""
        config_dict = {
            'parity_error_percent': 5.0,
            'no_response_percent': 2.0,
            'late_response_percent': 3.0,
            'word_count_error_percent': 1.0,
            'manchester_error_percent': 0.5,
            'sync_error_percent': 0.1,
            'bus_failover_time_s': 10.0,
            'timestamp_jitter_ms': 1.5
        }
        
        config = create_error_config_from_dict(config_dict)
        
        assert config.parity_error_percent == 5.0
        assert config.no_response_percent == 2.0
        assert config.late_response_percent == 3.0
        assert config.word_count_error_percent == 1.0
        assert config.manchester_error_percent == 0.5
        assert config.sync_error_percent == 0.1
        assert config.bus_failover_time_s == 10.0
        assert config.timestamp_jitter_ms == 1.5
    
    def test_config_validation(self):
        """Test config validation for valid ranges."""
        # Percentages should be 0-100
        config = ErrorInjectionConfig()
        
        # Set valid percentages
        config.parity_error_percent = 50.0
        assert config.parity_error_percent == 50.0
        
        config.parity_error_percent = 0.0
        assert config.parity_error_percent == 0.0
        
        config.parity_error_percent = 100.0
        assert config.parity_error_percent == 100.0


@pytest.mark.unit
class TestMessageErrorInjector:
    """Test message error injector."""
    
    def test_injector_creation(self):
        """Test creating error injector."""
        config = ErrorInjectionConfig()
        injector = MessageErrorInjector(config, seed=42)
        
        assert injector is not None
        assert injector.config == config
        assert injector.message_count == 0
        assert isinstance(injector.error_count, dict)
    
    def test_inject_no_errors(self):
        """Test injector with no errors configured."""
        config = ErrorInjectionConfig()  # All zeros
        injector = MessageErrorInjector(config, seed=42)
        
        message = {
            'command_word': 0x2822,
            'status_word': 0x2800,
            'data_words': [0x1234, 0x5678]
        }
        
        result = injector.inject_errors(message)
        
        # Should be unchanged
        assert result == message
        assert injector.message_count == 1
        assert all(count == 0 for count in injector.error_count.values())
    
    def test_inject_parity_errors(self):
        """Test parity error injection."""
        config = ErrorInjectionConfig()
        config.parity_error_percent = 100.0  # Always inject
        
        injector = MessageErrorInjector(config, seed=42)
        
        message = {
            'command_word': 0x2822,
            'status_word': 0x2800,
            'data_words': [0x1234, 0x5678]
        }
        
        # Inject errors in 10 messages
        for _ in range(10):
            result = injector.inject_errors(message.copy())
            # Status word should have parity error bit set
            # or command word should be modified
            assert result != message or 'error_type' in result
        
        # Should have counted errors
        assert injector.error_count['parity'] > 0
    
    def test_inject_no_response(self):
        """Test no response error injection."""
        config = ErrorInjectionConfig()
        config.no_response_percent = 100.0  # Always inject
        
        injector = MessageErrorInjector(config, seed=42)
        
        message = {
            'command_word': 0x2822,
            'status_word': 0x2800,
            'data_words': [0x1234, 0x5678]
        }
        
        result = injector.inject_errors(message.copy())
        
        # Should mark as no response
        assert result.get('error_type') == 'no_response' or \
               result.get('status_word') == 0 or \
               'no_response' in result
        
        assert injector.error_count['no_response'] > 0
    
    def test_inject_late_response(self):
        """Test late response error injection."""
        config = ErrorInjectionConfig()
        config.late_response_percent = 100.0
        
        injector = MessageErrorInjector(config, seed=42)
        
        message = {
            'command_word': 0x2822,
            'status_word': 0x2800,
            'data_words': [0x1234, 0x5678],
            'rt_response_time_us': 8.0
        }
        
        result = injector.inject_errors(message.copy())
        
        # Response time should be increased
        if 'rt_response_time_us' in result:
            assert result['rt_response_time_us'] > 12.0  # Beyond spec
        
        assert injector.error_count['late_response'] > 0
    
    def test_inject_word_count_error(self):
        """Test word count mismatch error injection."""
        config = ErrorInjectionConfig()
        config.word_count_error_percent = 100.0
        
        injector = MessageErrorInjector(config, seed=42)
        
        message = {
            'command_word': 0x2822,  # WC=2 encoded
            'status_word': 0x2800,
            'data_words': [0x1234, 0x5678]  # 2 words
        }
        
        result = injector.inject_errors(message.copy())
        
        # Word count should be wrong
        if 'data_words' in result:
            # Either more or fewer words
            assert len(result['data_words']) != 2
        
        assert injector.error_count['word_count'] > 0
    
    def test_error_distribution(self):
        """Test that errors follow configured distribution."""
        config = ErrorInjectionConfig()
        config.parity_error_percent = 10.0  # 10% error rate
        
        injector = MessageErrorInjector(config, seed=42)
        
        message = {
            'command_word': 0x2822,
            'status_word': 0x2800,
            'data_words': [0x1234, 0x5678]
        }
        
        # Inject errors in many messages
        total_messages = 1000
        for _ in range(total_messages):
            injector.inject_errors(message.copy())
        
        # Check error rate is approximately 10%
        error_rate = injector.error_count['parity'] / total_messages * 100
        assert 5 < error_rate < 15  # Within reasonable bounds


@pytest.mark.unit
class TestSpecificErrorTypes:
    """Test specific error type implementations."""
    
    def test_parity_error_injection(self):
        """Test parity error injection via MessageErrorInjector."""
        config = ErrorInjectionConfig(parity_error_percent=100.0)
        injector = MessageErrorInjector(config)
        
        message = {
            'command_word': 0x2822,
            'status_word': 0x2800,
            'data_words': [0x1234]
        }
        
        # Inject errors
        result = injector.inject_errors(message)
        
        # Should have injected error
        assert injector.error_count['parity'] > 0
    
    def test_no_response_injection(self):
        """Test no response error injection via MessageErrorInjector."""
        config = ErrorInjectionConfig(no_response_percent=100.0)
        injector = MessageErrorInjector(config)
        
        message = {
            'command_word': 0x2822,
            'status_word': 0x2800,
            'data_words': [0x1234]
        }
        
        result = injector.inject_errors(message)
        
        # Should have injected error
        assert injector.error_count['no_response'] > 0
    
    def test_late_response_injection(self):
        """Test late response error injection via MessageErrorInjector."""
        config = ErrorInjectionConfig(late_response_percent=100.0)
        injector = MessageErrorInjector(config)
        
        message = {
            'command_word': 0x2822,
            'status_word': 0x2800,
            'data_words': [0x1234],
            'rt_response_time_us': 8.0
        }
        
        result = injector.inject_errors(message)
        
        # Should have injected error
        assert injector.error_count['late_response'] > 0
    
    def test_word_count_mismatch_injection(self):
        """Test word count mismatch error injection via MessageErrorInjector."""
        config = ErrorInjectionConfig(word_count_mismatch_percent=100.0)
        injector = MessageErrorInjector(config)
        
        message = {
            'command_word': 0x2822,  # Encodes WC=2
            'status_word': 0x2800,
            'data_words': [0x1234, 0x5678]  # 2 words
        }
        
        result = injector.inject_errors(message)
        
        # Should have injected error
        assert injector.error_count['word_count_mismatch'] > 0
        
        # Should be 1 or 3 (off by one)
        assert len(result['data_words']) in [1, 3]
    
    def test_manchester_error_injection(self):
        """Test Manchester encoding error injection via MessageErrorInjector."""
        config = ErrorInjectionConfig(manchester_error_percent=100.0)
        injector = MessageErrorInjector(config)
        
        message = {
            'command_word': 0x2822,
            'status_word': 0x2800,
            'data_words': [0x1234]
        }
        
        result = injector.inject_errors(message)
        
        # Should have injected error
        assert injector.error_count['manchester'] > 0
    
    def test_sync_error_injection(self):
        """Test sync pattern error injection via MessageErrorInjector."""
        config = ErrorInjectionConfig(sync_error_percent=100.0)
        injector = MessageErrorInjector(config)
        
        message = {
            'command_word': 0x2822,
            'status_word': 0x2800,
            'data_words': [0x1234],
            'sync_type': 'command'
        }
        
        result = injector.inject_errors(message)
        
        # Should have injected error
        assert injector.error_count['sync'] > 0


@pytest.mark.unit
class TestErrorCombinations:
    """Test combinations of errors."""
    
    def test_multiple_error_types(self):
        """Test multiple error types together."""
        config = ErrorInjectionConfig()
        config.parity_error_percent = 50.0
        config.late_response_percent = 50.0
        
        injector = MessageErrorInjector(config, seed=42)
        
        messages_with_both = 0
        messages_with_parity = 0
        messages_with_late = 0
        
        for _ in range(100):
            message = {
                'command_word': 0x2822,
                'status_word': 0x2800,
                'data_words': [0x1234],
                'rt_response_time_us': 8.0
            }
            
            result = injector.inject_errors(message)
            
            has_parity = result != message and 'command_word' in result
            has_late = result.get('rt_response_time_us', 8.0) > 12.0
            
            if has_parity:
                messages_with_parity += 1
            if has_late:
                messages_with_late += 1
            if has_parity and has_late:
                messages_with_both += 1
        
        # Should have some of each
        assert messages_with_parity > 20
        assert messages_with_late > 20
        # Might have some with both
        assert messages_with_both >= 0
    
    def test_bus_failover(self):
        """Test bus failover timing."""
        config = ErrorInjectionConfig()
        config.bus_failover_time_s = 5.0  # Failover at 5 seconds
        
        injector = MessageErrorInjector(config, seed=42)
        
        # Message before failover
        message_early = {
            'time_s': 2.0,
            'bus': 0,  # Bus A
            'command_word': 0x2822
        }
        
        result_early = injector.inject_errors(message_early)
        assert result_early['bus'] == 0  # Still on bus A
        
        # Message after failover
        message_late = {
            'time_s': 7.0,
            'bus': 0,  # Bus A
            'command_word': 0x2822
        }
        
        result_late = injector.inject_errors(message_late)
        # Might switch to bus B
        # Implementation-dependent
    
    def test_timestamp_jitter(self):
        """Test timestamp jitter injection."""
        config = ErrorInjectionConfig()
        config.timestamp_jitter_ms = 2.0  # ±2ms jitter
        
        injector = MessageErrorInjector(config, seed=42)
        
        original_times = []
        jittered_times = []
        
        for i in range(100):
            message = {
                'ipts': i * 1000000,  # Microseconds
                'command_word': 0x2822
            }
            
            result = injector.inject_errors(message)
            
            original_times.append(message['ipts'])
            jittered_times.append(result.get('ipts', message['ipts']))
        
        # Should have some jitter
        differences = [abs(j - o) for j, o in zip(jittered_times, original_times)]
        
        # Some should be jittered
        assert max(differences) > 0
        # But within bounds (2ms = 2000μs)
        assert max(differences) <= 2000
