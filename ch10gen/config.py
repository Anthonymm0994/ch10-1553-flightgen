"""Central configuration for CH10 generation.

This module provides a configuration system that merges settings from
multiple sources with clear precedence rules. Configuration can be specified via:

1. CLI arguments (highest precedence)
2. Scenario/ICD YAML files
3. Environment variables
4. Code defaults (lowest precedence)

Example usage:
    # Load configuration from multiple sources
    config = get_config(
        cli_args={'writer': 'pyc10', 'packet_bytes': 32768},
        scenario_path=Path('scenario.yaml'),
        use_env=True
    )
    
    # Access nested configuration
    print(f"Writer: {config.writer.backend}")
    print(f"Packet size: {config.writer.packet_bytes_target}")
    print(f"Jitter: {config.timing.pct_jitter}%")
"""

from dataclasses import dataclass, field, asdict
from typing import Tuple, Optional, Dict, Any
import os
import yaml
from pathlib import Path


@dataclass
class TimingConfig:
    """Timing and jitter configuration for 1553 bus simulation.
    
    Controls the timing behavior of the 1553 bus simulation, including
    response times, inter-message gaps, and jitter characteristics.
    
    Attributes:
        rt_response_us: Min/max RT response time in microseconds
        inter_message_gap_us: Nominal gap between messages in microseconds
        pct_jitter: Percentage jitter for timing gaps (0.0 = deterministic)
        time_packet_interval_s: Time packet cadence in seconds
    """
    rt_response_us: Tuple[float, float] = field(
        default=(4.0, 12.0),
        metadata={
            'description': 'Min/max RT response time in microseconds',
            'range': '4.0 to 12.0',
            'example': '(4.0, 12.0)'
        }
    )
    inter_message_gap_us: float = field(
        default=4.0,
        metadata={
            'description': 'Nominal gap between messages in microseconds',
            'range': '1.0 to 100.0',
            'example': '4.0'
        }
    )
    pct_jitter: float = field(
        default=20.0,
        metadata={
            'description': 'Percentage jitter for gaps (0.0 = deterministic)',
            'range': '0.0 to 100.0',
            'example': '20.0'
        }
    )
    time_packet_interval_s: float = field(
        default=1.0,
        metadata={
            'description': 'Time packet cadence in seconds',
            'range': '0.1 to 10.0',
            'example': '1.0'
        }
    )
    
    @property
    def zero_jitter(self) -> bool:
        """Check if jitter is disabled for deterministic tests.
        
        Returns:
            True if all timing variations are disabled
        """
        return self.pct_jitter == 0 and self.rt_response_us[0] == self.rt_response_us[1]
    
    def set_zero_jitter(self) -> None:
        """Disable all timing jitter for deterministic tests.
        
        This method sets fixed timing values to ensure reproducible
        output when testing or debugging.
        """
        self.rt_response_us = (8.0, 8.0)  # Fixed at nominal
        self.pct_jitter = 0.0


@dataclass
class WriterConfig:
    """Writer backend configuration for Chapter 10 file generation.
    
    Controls the output format, packet sizing, and progress reporting
    for the Chapter 10 file generation process.
    
    Attributes:
        backend: Writer backend selection ('irig106' or 'pyc10')
        packet_bytes_target: Maximum packet size in bytes
        flush_ms: Force flush interval in milliseconds
        timeout_s: Build timeout in seconds (None = no timeout)
        progress_interval: Progress reporting frequency in packets
        tmats_channel_id: TMATS channel identifier
        time_channel_id: Time channel identifier
        bus_a_channel_id: Bus A channel identifier
        bus_b_channel_id: Bus B channel identifier
    """
    backend: str = field(
        default='irig106',
        metadata={
            'description': 'Writer backend selection',
            'choices': ['irig106', 'pyc10'],
            'example': 'irig106'
        }
    )
    packet_bytes_target: int = field(
        default=65536,
        metadata={
            'description': 'Maximum packet size in bytes',
            'range': '1024 to 1048576',
            'example': '65536'
        }
    )
    flush_ms: int = field(
        default=1000,
        metadata={
            'description': 'Force flush interval in milliseconds',
            'range': '100 to 10000',
            'example': '1000'
        }
    )
    timeout_s: Optional[int] = field(
        default=None,
        metadata={
            'description': 'Build timeout in seconds (None = no timeout)',
            'range': '60 to 3600 or None',
            'example': '300'
        }
    )
    progress_interval: int = field(
        default=1000,
        metadata={
            'description': 'Progress reporting frequency in packets',
            'range': '100 to 10000',
            'example': '1000'
        }
    )
    
    # Channel IDs for different data types
    tmats_channel_id: int = field(
        default=0x0200,
        metadata={
            'description': 'TMATS channel identifier',
            'example': '0x0200'
        }
    )
    time_channel_id: int = field(
        default=0x0100,
        metadata={
            'description': 'Time channel identifier',
            'example': '0x0100'
        }
    )
    bus_a_channel_id: int = field(
        default=0x0210,
        metadata={
            'description': 'Bus A channel identifier',
            'example': '0x0210'
        }
    )
    bus_b_channel_id: int = field(
        default=0x0220,
        metadata={
            'description': 'Bus B channel identifier',
            'example': '0x0220'
        }
    )


@dataclass
class ErrorConfig:
    """Error injection configuration for 1553 bus simulation.
    
    Controls the injection of various types of errors to simulate
    real-world 1553 bus conditions and test error handling.
    
    Attributes:
        enabled: Master enable for error injection
        parity_error_percent: Percentage of parity errors (0.0-100.0)
        no_response_percent: Percentage of no-response conditions (0.0-100.0)
        late_response_percent: Percentage of late responses (0.0-100.0)
        word_count_error_percent: Percentage of word count errors (0.0-100.0)
        manchester_error_percent: Percentage of Manchester errors (0.0-100.0)
        sync_error_percent: Percentage of sync errors (0.0-100.0)
        bus_failover_time_s: Time before bus failover (None = disabled)
        timestamp_jitter_ms: Timestamp jitter in milliseconds
    """
    enabled: bool = field(
        default=False,
        metadata={
            'description': 'Master enable for error injection',
            'example': 'false'
        }
    )
    parity_error_percent: float = field(
        default=0.0,
        metadata={
            'description': 'Percentage of parity errors',
            'range': '0.0 to 100.0',
            'example': '0.05'
        }
    )
    no_response_percent: float = field(
        default=0.0,
        metadata={
            'description': 'Percentage of no-response conditions',
            'range': '0.0 to 100.0',
            'example': '0.02'
        }
    )
    late_response_percent: float = field(
        default=0.0,
        metadata={
            'description': 'Percentage of late responses',
            'range': '0.0 to 100.0',
            'example': '0.01'
        }
    )
    word_count_error_percent: float = field(
        default=0.0,
        metadata={
            'description': 'Percentage of word count errors',
            'range': '0.0 to 100.0',
            'example': '0.005'
        }
    )
    manchester_error_percent: float = field(
        default=0.0,
        metadata={
            'description': 'Percentage of Manchester errors',
            'range': '0.0 to 100.0',
            'example': '0.001'
        }
    )
    sync_error_percent: float = field(
        default=0.0,
        metadata={
            'description': 'Percentage of sync errors',
            'range': '0.0 to 100.0',
            'example': '0.001'
        }
    )
    bus_failover_time_s: Optional[float] = field(
        default=None,
        metadata={
            'description': 'Time before bus failover in seconds',
            'range': '1.0 to 60.0 or None',
            'example': '10.0'
        }
    )
    timestamp_jitter_ms: float = field(
        default=0.0,
        metadata={
            'description': 'Timestamp jitter in milliseconds',
            'range': '0.0 to 100.0',
            'example': '0.5'
        }
    )





@dataclass
class Config:
    """Central configuration for CH10 generation.
    
    This is the main configuration class that combines all subsystem
    configurations into a single, easily accessible structure.
    
    Attributes:
        timing: Timing and jitter configuration
        writer: Writer backend configuration
        errors: Error injection configuration
    
        dry_run: Validate configuration without generating output
        verbose: Enable verbose logging and output
        seed: Global random seed for reproducible output
    """
    timing: TimingConfig = field(default_factory=TimingConfig)
    writer: WriterConfig = field(default_factory=WriterConfig)
    errors: ErrorConfig = field(default_factory=ErrorConfig)

    
    # Runtime options
    dry_run: bool = field(
        default=False,
        metadata={
            'description': 'Validate configuration without generating output',
            'example': 'false'
        }
    )
    verbose: bool = field(
        default=False,
        metadata={
            'description': 'Enable verbose logging and output',
            'example': 'false'
        }
    )
    seed: Optional[int] = field(
        default=None,
        metadata={
            'description': 'Global random seed for reproducible output',
            'range': '1 to 999999 or None',
            'example': '42'
        }
    )
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Config':
        """Create config from dictionary with selective merging.
        
        This method merges configuration data from dictionaries (e.g., from YAML)
        while preserving the structure of nested configuration objects.
        
        Args:
            data: Dictionary containing configuration data
            
        Returns:
            New Config instance with merged values
            
        Example:
            config_data = {
                'timing': {'pct_jitter': 0.0},
                'writer': {'backend': 'pyc10'},
                'seed': 42
            }
            config = Config.from_dict(config_data)
        """
        config = cls()
        
        # Update timing configuration
        if 'timing' in data:
            for k, v in data['timing'].items():
                if hasattr(config.timing, k):
                    setattr(config.timing, k, v)
        
        # Update writer configuration
        if 'writer' in data:
            for k, v in data['writer'].items():
                if hasattr(config.writer, k):
                    setattr(config.writer, k, v)
        
        # Update error configuration
        if 'errors' in data:
            for k, v in data['errors'].items():
                if hasattr(config.errors, k):
                    setattr(config.errors, k, v)
        

        
        # Update runtime options
        for k in ['dry_run', 'verbose', 'seed']:
            if k in data:
                setattr(config, k, data[k])
        
        return config
    
    @classmethod
    def from_yaml(cls, path: Path) -> 'Config':
        """Load config from YAML file.
        
        Args:
            path: Path to YAML configuration file
            
        Returns:
            New Config instance loaded from YAML
            
        Raises:
            FileNotFoundError: If the YAML file doesn't exist
            yaml.YAMLError: If the YAML file is malformed
            
        Example:
            config = Config.from_yaml(Path('config.yaml'))
        """
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data.get('config', {}))
    
    @classmethod
    def from_env(cls) -> 'Config':
        """Create config from environment variables.
        
        This method checks for environment variables that start with 'CH10_'
        and applies them to the configuration. This allows for system-wide
        configuration overrides without modifying files.
        
        Returns:
            New Config instance with environment overrides
            
        Environment Variables:
            CH10_WRITER_BACKEND: Writer backend selection
            CH10_ZERO_JITTER: Disable timing jitter (any value)
            CH10_TIMEOUT_S: Build timeout in seconds
            CH10_SEED: Global random seed
            
        Example:
            export CH10_WRITER_BACKEND=pyc10
            export CH10_ZERO_JITTER=1
            config = Config.from_env()
        """
        config = cls()
        
        # Check for environment overrides
        if os.getenv('CH10_WRITER_BACKEND'):
            config.writer.backend = os.getenv('CH10_WRITER_BACKEND')
        
        if os.getenv('CH10_ZERO_JITTER'):
            config.timing.set_zero_jitter()
        
        if os.getenv('CH10_TIMEOUT_S'):
            config.writer.timeout_s = int(os.getenv('CH10_TIMEOUT_S'))
        
        if os.getenv('CH10_SEED'):
            config.seed = int(os.getenv('CH10_SEED'))
        
        return config
    
    def merge_cli_args(self, **kwargs) -> None:
        """Merge CLI arguments (highest precedence).
        
        This method applies command-line arguments to the configuration,
        overriding any existing values. CLI arguments have the highest
        precedence in the configuration hierarchy.
        
        Args:
            **kwargs: CLI argument key-value pairs
            
        Example:
            config.merge_cli_args(
                writer='pyc10',
                packet_bytes=32768,
                seed=42,
                verbose=True
            )
        """
        # Writer options
        if 'writer' in kwargs and kwargs['writer']:
            self.writer.backend = kwargs['writer']
        
        if 'packet_bytes' in kwargs and kwargs['packet_bytes']:
            self.writer.packet_bytes_target = kwargs['packet_bytes']
        
        if 'flush_ms' in kwargs and kwargs['flush_ms']:
            self.writer.flush_ms = kwargs['flush_ms']
        
        if 'timeout_s' in kwargs and kwargs['timeout_s']:
            self.writer.timeout_s = kwargs['timeout_s']
        
        if 'progress_every' in kwargs and kwargs['progress_every']:
            self.writer.progress_interval = kwargs['progress_every']
        
        # Runtime options
        if 'dry_run' in kwargs:
            self.dry_run = kwargs['dry_run']
        
        if 'verbose' in kwargs:
            self.verbose = kwargs['verbose']
        
        if 'seed' in kwargs and kwargs['seed'] is not None:
            self.seed = kwargs['seed']
        
        # Zero jitter mode for tests
        if 'zero_jitter' in kwargs and kwargs['zero_jitter']:
            self.timing.set_zero_jitter()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization.
        
        Returns:
            Dictionary representation of the configuration
            
        Example:
            config_dict = config.to_dict()
            yaml.dump(config_dict, file)
        """
        return asdict(self)
    
    def summary(self) -> str:
        """Generate one-line summary of resolved configuration.
        
        Returns:
            Human-readable summary string
            
        Example:
            print(config.summary())
            # Output: "Config[writer=irig106, packet=65536, jitter=20%, rt=(4.0, 12.0), seed=42]"
        """
        return (
            f"Config[writer={self.writer.backend}, "
            f"packet={self.writer.packet_bytes_target}, "
            f"jitter={self.timing.pct_jitter}%, "
            f"rt={self.timing.rt_response_us}, "
            f"seed={self.seed}]"
        )


def get_config(cli_args: Optional[Dict] = None,
               scenario_path: Optional[Path] = None,
               use_env: bool = True) -> Config:
    """Get merged configuration from all sources with proper precedence.
    
    This function implements the configuration precedence hierarchy:
    1. CLI arguments (highest priority)
    2. Scenario/ICD YAML files
    3. Environment variables
    4. Code defaults (lowest priority)
    
    Args:
        cli_args: Command-line arguments dictionary
        scenario_path: Path to scenario YAML file
        use_env: Whether to apply environment variable overrides
        
    Returns:
        Fully resolved Config instance
        
    Example:
        # Load configuration from multiple sources
        config = get_config(
            cli_args={'writer': 'pyc10', 'packet_bytes': 32768},
            scenario_path=Path('scenario.yaml'),
            use_env=True
        )
        
        # Use the configuration
        print(f"Using {config.writer.backend} backend")
        print(f"Packet size: {config.writer.packet_bytes_target}")
    """
    # Start with defaults
    config = Config()
    
    # Apply environment if requested
    if use_env:
        env_config = Config.from_env()
        # Merge env values
        if env_config.writer.backend != config.writer.backend:
            config.writer.backend = env_config.writer.backend
        if env_config.seed is not None:
            config.seed = env_config.seed
        if env_config.writer.timeout_s is not None:
            config.writer.timeout_s = env_config.writer.timeout_s
        if env_config.timing.zero_jitter:
            config.timing.set_zero_jitter()
    
    # Apply scenario if provided
    if scenario_path and scenario_path.exists():
        try:
            scenario_config = Config.from_yaml(scenario_path)
            # Merge scenario values (selective)
            config = scenario_config
        except:
            pass  # Ignore if no config section
    
    # Apply CLI (highest precedence)
    if cli_args:
        config.merge_cli_args(**cli_args)
    
    return config
