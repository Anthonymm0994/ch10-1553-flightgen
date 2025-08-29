"""Test central configuration system."""

import pytest
import os
import tempfile
from pathlib import Path
from ch10gen.config import Config, TimingConfig, WriterConfig, get_config


@pytest.mark.unit
class TestConfigMerging:
    """Test configuration merging precedence."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = Config()
        
        # Check defaults
        assert config.writer.backend == 'irig106'
        assert config.writer.packet_bytes_target == 65536
        assert config.timing.rt_response_us == (4.0, 12.0)
        assert config.timing.pct_jitter == 20.0
        assert config.seed is None
        assert config.dry_run == False
    
    def test_zero_jitter_mode(self):
        """Test zero-jitter mode configuration."""
        config = Config()
        config.timing.set_zero_jitter()
        
        assert config.timing.pct_jitter == 0.0
        assert config.timing.rt_response_us[0] == config.timing.rt_response_us[1]
        assert config.timing.zero_jitter == True
    
    def test_from_dict(self):
        """Test creating config from dictionary."""
        data = {
            'timing': {
                'rt_response_us': (6.0, 10.0),
                'pct_jitter': 15.0
            },
            'writer': {
                'backend': 'pyc10',
                'packet_bytes_target': 32768
            },
            'seed': 42,
            'verbose': True
        }
        
        config = Config.from_dict(data)
        
        assert config.timing.rt_response_us == (6.0, 10.0)
        assert config.timing.pct_jitter == 15.0
        assert config.writer.backend == 'pyc10'
        assert config.writer.packet_bytes_target == 32768
        assert config.seed == 42
        assert config.verbose == True
    
    def test_from_yaml(self):
        """Test loading config from YAML file."""
        import yaml
        
        yaml_content = """
config:
  timing:
    rt_response_us: [5.0, 15.0]
    pct_jitter: 10.0
  writer:
    backend: irig106
    flush_ms: 500
  seed: 999
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            yaml_path = Path(f.name)
        
        try:
            config = Config.from_yaml(yaml_path)
            
            assert config.timing.rt_response_us == [5.0, 15.0]
            assert config.timing.pct_jitter == 10.0
            assert config.writer.flush_ms == 500
            assert config.seed == 999
        finally:
            yaml_path.unlink()
    
    def test_env_override(self):
        """Test environment variable overrides."""
        # Save original env
        orig_backend = os.environ.get('CH10_WRITER_BACKEND')
        orig_seed = os.environ.get('CH10_SEED')
        orig_jitter = os.environ.get('CH10_ZERO_JITTER')
        
        try:
            # Set test env vars
            os.environ['CH10_WRITER_BACKEND'] = 'pyc10'
            os.environ['CH10_SEED'] = '54321'
            os.environ['CH10_ZERO_JITTER'] = '1'
            
            config = Config.from_env()
            
            assert config.writer.backend == 'pyc10'
            assert config.seed == 54321
            assert config.timing.zero_jitter == True
        finally:
            # Restore env
            if orig_backend:
                os.environ['CH10_WRITER_BACKEND'] = orig_backend
            else:
                os.environ.pop('CH10_WRITER_BACKEND', None)
            
            if orig_seed:
                os.environ['CH10_SEED'] = orig_seed
            else:
                os.environ.pop('CH10_SEED', None)
                
            if orig_jitter:
                os.environ['CH10_ZERO_JITTER'] = orig_jitter
            else:
                os.environ.pop('CH10_ZERO_JITTER', None)
    
    def test_cli_highest_precedence(self):
        """Test that CLI args have highest precedence."""
        config = Config()
        config.writer.backend = 'pyc10'  # Start with non-default
        
        cli_args = {
            'writer': 'irig106',
            'packet_bytes': 8192,
            'seed': 777,
            'zero_jitter': True
        }
        
        config.merge_cli_args(**cli_args)
        
        assert config.writer.backend == 'irig106'  # CLI overrides
        assert config.writer.packet_bytes_target == 8192
        assert config.seed == 777
        assert config.timing.zero_jitter == True
    
    def test_config_summary(self):
        """Test config summary string."""
        config = Config()
        config.seed = 42
        
        summary = config.summary()
        
        assert 'writer=irig106' in summary
        assert 'packet=65536' in summary
        assert 'seed=42' in summary
        assert 'jitter=' in summary
        assert 'rt=' in summary


@pytest.mark.unit
class TestGetConfig:
    """Test get_config function with precedence."""
    
    def test_precedence_order(self):
        """Test that precedence order is correct."""
        # Create test scenario file
        import yaml
        
        scenario_data = {
            'config': {
                'writer': {
                    'backend': 'pyc10'  # Scenario sets pyc10
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(scenario_data, f)
            scenario_path = Path(f.name)
        
        try:
            # CLI should override scenario
            cli_args = {
                'writer': 'irig106'  # CLI sets irig106
            }
            
            config = get_config(
                cli_args=cli_args,
                scenario_path=scenario_path,
                use_env=False
            )
            
            # CLI wins
            assert config.writer.backend == 'irig106'
        finally:
            scenario_path.unlink()
    
    def test_partial_configs_merge(self):
        """Test that partial configs merge correctly."""
        cli_args = {
            'seed': 100
        }
        
        config = get_config(cli_args=cli_args, use_env=False)
        
        # CLI seed is set
        assert config.seed == 100
        
        # Other values are defaults
        assert config.writer.backend == 'irig106'
        assert config.timing.pct_jitter == 20.0


@pytest.mark.unit
class TestTimingConfig:
    """Test timing configuration specifics."""
    
    def test_rt_response_range(self):
        """Test RT response time range configuration."""
        timing = TimingConfig()
        
        # Default should be MIL-STD-1553B compliant
        assert timing.rt_response_us[0] >= 4.0  # Min 4μs
        assert timing.rt_response_us[1] <= 12.0  # Max 12μs
    
    def test_jitter_percentage(self):
        """Test jitter percentage configuration."""
        timing = TimingConfig()
        timing.pct_jitter = 50.0
        
        # Calculate jittered value
        nominal = 100.0
        min_val = nominal * (1 - timing.pct_jitter / 100)
        max_val = nominal * (1 + timing.pct_jitter / 100)
        
        assert min_val == 50.0
        assert max_val == 150.0


@pytest.mark.unit
class TestWriterConfig:
    """Test writer configuration specifics."""
    
    def test_channel_ids(self):
        """Test channel ID assignments."""
        writer = WriterConfig()
        
        # Check standard channel assignments
        assert writer.tmats_channel_id == 0x0200
        assert writer.time_channel_id == 0x0100
        assert writer.bus_a_channel_id == 0x0210
        assert writer.bus_b_channel_id == 0x0220
        
        # Channels should be unique
        channels = [
            writer.tmats_channel_id,
            writer.time_channel_id,
            writer.bus_a_channel_id,
            writer.bus_b_channel_id
        ]
        assert len(channels) == len(set(channels))  # All unique
    
    def test_packet_size_limits(self):
        """Test packet size configuration limits."""
        writer = WriterConfig()
        
        # Default should be reasonable
        assert writer.packet_bytes_target >= 1024  # At least 1KB
        assert writer.packet_bytes_target <= 1048576  # At most 1MB
        
        # Should be power of 2 or common size
        common_sizes = [1024, 2048, 4096, 8192, 16384, 32768, 65536, 131072, 262144, 524288]
        assert writer.packet_bytes_target in common_sizes or \
               writer.packet_bytes_target % 1024 == 0
