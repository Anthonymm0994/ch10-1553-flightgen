"""
Modular data generation system for scenario-driven CH10 generation.
Provides flexible, per-field configuration of data generation modes.
"""

import random
import math
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import numpy as np


@dataclass
class GenerationContext:
    """Context provided to generators for data generation."""
    time_seconds: float          # Time since start
    message_count: int           # Count for this message type
    message_name: str           # Current message name
    field_name: str            # Current field name
    field_values: Dict[str, Any]  # Already computed field values in current message
    all_values: Dict[str, Dict[str, Any]]  # All computed values across messages
    icd: Any                   # Full ICD for cross-references


class DataGenerator(ABC):
    """Base class for all data generators."""
    
    @abstractmethod
    def generate(self, context: GenerationContext) -> Union[int, float]:
        """Generate a value based on the context."""
        pass
    
    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate configuration and return list of errors."""
        return []


class RandomGenerator(DataGenerator):
    """Generate uniformly distributed random values."""
    
    def __init__(self, min_val: float = 0, max_val: float = 65535):
        self.min_val = min_val
        self.max_val = max_val
    
    def generate(self, context: GenerationContext) -> Union[int, float]:
        """Generate random value in range."""
        if isinstance(self.min_val, int) and isinstance(self.max_val, int):
            return random.randint(self.min_val, self.max_val)
        else:
            return random.uniform(self.min_val, self.max_val)


class RandomNormalGenerator(DataGenerator):
    """Generate normally distributed random values."""
    
    def __init__(self, mean: float = 0, std_dev: float = 1, 
                 min_val: Optional[float] = None, max_val: Optional[float] = None):
        self.mean = mean
        self.std_dev = std_dev
        self.min_val = min_val
        self.max_val = max_val
    
    def generate(self, context: GenerationContext) -> float:
        """Generate normal distribution value."""
        value = np.random.normal(self.mean, self.std_dev)
        
        # Clip to range if specified
        if self.min_val is not None:
            value = max(value, self.min_val)
        if self.max_val is not None:
            value = min(value, self.max_val)
        
        return value


class RandomMultimodalGenerator(DataGenerator):
    """Generate multimodal distributed random values."""
    
    def __init__(self, peaks: List[Dict[str, float]]):
        """
        Args:
            peaks: List of dicts with 'mean', 'std_dev', and 'weight' keys
        """
        self.peaks = peaks
        # Normalize weights
        total_weight = sum(p['weight'] for p in peaks)
        for peak in self.peaks:
            peak['weight'] /= total_weight
    
    def generate(self, context: GenerationContext) -> float:
        """Generate multimodal value."""
        # Choose peak based on weights
        r = random.random()
        cumulative = 0
        for peak in self.peaks:
            cumulative += peak['weight']
            if r <= cumulative:
                return np.random.normal(peak['mean'], peak['std_dev'])
        
        # Fallback to last peak
        return np.random.normal(self.peaks[-1]['mean'], self.peaks[-1]['std_dev'])


class ConstantGenerator(DataGenerator):
    """Generate constant values."""
    
    def __init__(self, value: Union[int, float]):
        self.value = value
    
    def generate(self, context: GenerationContext) -> Union[int, float]:
        """Return constant value."""
        return self.value


class IncrementGenerator(DataGenerator):
    """Generate incrementing counter values."""
    
    def __init__(self, start: int = 0, increment: int = 1, wrap: Optional[int] = None):
        self.start = start
        self.increment = increment
        self.wrap = wrap
        self.current = start
    
    def generate(self, context: GenerationContext) -> int:
        """Generate next counter value."""
        value = self.current
        self.current += self.increment
        
        if self.wrap is not None and self.current > self.wrap:
            self.current = self.start
        
        return value


class PatternGenerator(DataGenerator):
    """Generate repeating pattern values."""
    
    def __init__(self, values: List[Union[int, float]], repeat: bool = True):
        self.values = values
        self.repeat = repeat
        self.index = 0
    
    def generate(self, context: GenerationContext) -> Union[int, float]:
        """Generate next pattern value."""
        if self.index >= len(self.values):
            if self.repeat:
                self.index = 0
            else:
                return self.values[-1]  # Stick at last value
        
        value = self.values[self.index]
        self.index += 1
        return value


class SineGenerator(DataGenerator):
    """Generate sine wave values."""
    
    def __init__(self, center: float = 0, amplitude: float = 1, 
                 frequency: float = 1, phase: float = 0):
        self.center = center
        self.amplitude = amplitude
        self.frequency = frequency
        self.phase = phase
    
    def generate(self, context: GenerationContext) -> float:
        """Generate sine wave value."""
        t = context.time_seconds
        return self.center + self.amplitude * math.sin(2 * math.pi * self.frequency * t + self.phase)


class CosineGenerator(DataGenerator):
    """Generate cosine wave values."""
    
    def __init__(self, center: float = 0, amplitude: float = 1, 
                 frequency: float = 1, phase: float = 0):
        self.center = center
        self.amplitude = amplitude
        self.frequency = frequency
        self.phase = phase
    
    def generate(self, context: GenerationContext) -> float:
        """Generate cosine wave value."""
        t = context.time_seconds
        return self.center + self.amplitude * math.cos(2 * math.pi * self.frequency * t + self.phase)


class SawtoothGenerator(DataGenerator):
    """Generate sawtooth wave values."""
    
    def __init__(self, min_val: float = 0, max_val: float = 100, period: float = 1):
        self.min_val = min_val
        self.max_val = max_val
        self.period = period
        self.range = max_val - min_val
    
    def generate(self, context: GenerationContext) -> float:
        """Generate sawtooth wave value."""
        t = context.time_seconds
        phase = (t % self.period) / self.period
        return self.min_val + self.range * phase


class SquareGenerator(DataGenerator):
    """Generate square wave values."""
    
    def __init__(self, low: float = 0, high: float = 1, 
                 period: float = 1, duty_cycle: float = 0.5):
        self.low = low
        self.high = high
        self.period = period
        self.duty_cycle = duty_cycle
    
    def generate(self, context: GenerationContext) -> float:
        """Generate square wave value."""
        t = context.time_seconds
        phase = (t % self.period) / self.period
        return self.high if phase < self.duty_cycle else self.low


class RampGenerator(DataGenerator):
    """Generate linear ramp values."""
    
    def __init__(self, start: float = 0, end: float = 100, 
                 duration: float = 10, repeat: bool = False):
        self.start = start
        self.end = end
        self.duration = duration
        self.repeat = repeat
        self.range = end - start
    
    def generate(self, context: GenerationContext) -> float:
        """Generate ramp value."""
        t = context.time_seconds
        
        if self.repeat:
            t = t % self.duration
        
        if t >= self.duration:
            return self.end
        
        progress = t / self.duration
        return self.start + self.range * progress


class ExpressionGenerator(DataGenerator):
    """Generate values based on mathematical expressions."""
    
    def __init__(self, formula: str):
        self.formula = formula
        self.compiled = None
        self._compile_expression()
    
    def _compile_expression(self):
        """Compile the expression for evaluation."""
        # This is a simplified version - full implementation would parse properly
        try:
            self.compiled = compile(self.formula, '<expression>', 'eval')
        except SyntaxError as e:
            raise ValueError(f"Invalid expression syntax in '{self.formula}': {e}. Check for missing operators, parentheses, or invalid function names.")
    
    def generate(self, context: GenerationContext) -> Union[int, float]:
        """Evaluate expression with context."""
        # Build evaluation context
        eval_context = {
            'time': context.time_seconds,
            'message_count': context.message_count,
            'random': lambda min_val=0, max_val=1: random.uniform(min_val, max_val),
            'sin': math.sin,
            'cos': math.cos,
            'tan': math.tan,
            'abs': abs,
            'min': min,
            'max': max,
            'sqrt': math.sqrt,
            'pow': pow,
            'exp': math.exp,
            'log': math.log,
            'floor': math.floor,
            'ceil': math.ceil,
            'round': round,
            'int': int,
            'float': float,
        }
        
        # Add field values from current message
        eval_context.update(context.field_values)
        
        # Add cross-message references
        for msg_name, msg_values in context.all_values.items():
            # Handle spaces in names by replacing with underscores for eval
            safe_name = msg_name.replace(' ', '_')
            eval_context[safe_name] = msg_values
        
        try:
            return eval(self.compiled, {"__builtins__": {}}, eval_context)
        except Exception as e:
            # Provide more context about what went wrong
            available_vars = list(eval_context.keys())
            raise ValueError(f"Error evaluating expression '{self.formula}' for field '{context.field_name}' in message '{context.message_name}': {e}. Available variables: {', '.join(available_vars[:10])}{'...' if len(available_vars) > 10 else ''}")


class GeneratorFactory:
    """Factory for creating data generators from configuration."""
    
    @staticmethod
    def create(config: Dict[str, Any]) -> DataGenerator:
        """
        Create a data generator from configuration.
        
        Args:
            config: Configuration dictionary with 'mode' and parameters
            
        Returns:
            Configured data generator
            
        Raises:
            ValueError: If mode is unknown or config is invalid
        """
        mode = config.get('mode', 'random')
        
        if mode == 'random':
            return RandomGenerator(
                min_val=config.get('min', 0),
                max_val=config.get('max', 65535)
            )
        
        elif mode == 'random_normal':
            return RandomNormalGenerator(
                mean=config.get('mean', 0),
                std_dev=config.get('std_dev', 1),
                min_val=config.get('min'),
                max_val=config.get('max')
            )
        
        elif mode == 'random_multimodal':
            return RandomMultimodalGenerator(
                peaks=config.get('peaks', [])
            )
        
        elif mode == 'constant':
            return ConstantGenerator(
                value=config.get('value', 0)
            )
        
        elif mode == 'increment':
            return IncrementGenerator(
                start=config.get('start', 0),
                increment=config.get('increment', 1),
                wrap=config.get('wrap')
            )
        
        elif mode == 'pattern':
            return PatternGenerator(
                values=config.get('values', []),
                repeat=config.get('repeat', True)
            )
        
        elif mode == 'sine':
            return SineGenerator(
                center=config.get('center', 0),
                amplitude=config.get('amplitude', 1),
                frequency=config.get('frequency', 1),
                phase=config.get('phase', 0)
            )
        
        elif mode == 'cosine':
            return CosineGenerator(
                center=config.get('center', 0),
                amplitude=config.get('amplitude', 1),
                frequency=config.get('frequency', 1),
                phase=config.get('phase', 0)
            )
        
        elif mode == 'sawtooth':
            return SawtoothGenerator(
                min_val=config.get('min', 0),
                max_val=config.get('max', 100),
                period=config.get('period', 1)
            )
        
        elif mode == 'square':
            return SquareGenerator(
                low=config.get('low', 0),
                high=config.get('high', 1),
                period=config.get('period', 1),
                duty_cycle=config.get('duty_cycle', 0.5)
            )
        
        elif mode == 'ramp':
            return RampGenerator(
                start=config.get('start', 0),
                end=config.get('end', 100),
                duration=config.get('duration', 10),
                repeat=config.get('repeat', False)
            )
        
        elif mode == 'expression':
            return ExpressionGenerator(
                formula=config.get('formula', '0')
            )
        
        else:
            available_modes = ['random', 'random_normal', 'random_multimodal', 'constant', 'increment', 'pattern', 'expression']
            raise ValueError(f"Unknown generator mode: '{mode}'. Available modes: {', '.join(available_modes)}")


# Singleton instance for managing all generators
class DataGeneratorManager:
    """Manages data generators for all fields in a scenario."""
    
    def __init__(self):
        self.generators: Dict[str, DataGenerator] = {}
        self.start_time = time.time()
        self.message_counts: Dict[str, int] = {}
        self.all_values: Dict[str, Dict[str, Any]] = {}
    
    def get_elapsed_time(self) -> float:
        """Get elapsed time since start in seconds."""
        return time.time() - self.start_time
    
    def get_message_count(self, message_name: str) -> int:
        """Get count of messages generated for a specific message type."""
        return self.message_counts.get(message_name, 0)
    
    def increment_message_count(self, message_name: str):
        """Increment the message count."""
        if message_name not in self.message_counts:
            self.message_counts[message_name] = 0
        self.message_counts[message_name] += 1
    
    def load_scenario(self, scenario: Dict[str, Any]):
        """Load generators from scenario configuration."""
        # Global default
        default_mode = scenario.get('defaults', {}).get('data_mode', 'random')
        default_config = {'mode': default_mode}
        
        # Message-specific configurations
        messages_config = scenario.get('messages', {})
        
        for message_name, message_config in messages_config.items():
            # Message-level default
            msg_default = message_config.get('default_mode', default_mode)
            
            # Field-specific configurations
            fields_config = message_config.get('fields', {})
            
            for field_name, field_config in fields_config.items():
                # Create full path for field
                field_path = f"{message_name}.{field_name}"
                
                # Use field config if provided, otherwise message default
                if isinstance(field_config, dict) and 'mode' in field_config:
                    generator = GeneratorFactory.create(field_config)
                else:
                    generator = GeneratorFactory.create({'mode': msg_default})
                
                self.generators[field_path] = generator
    
    def generate_value(self, message_name: str, field_name: str, 
                      field_values: Dict[str, Any] = None,
                      icd: Any = None) -> Union[int, float]:
        """Generate value for a specific field."""
        field_path = f"{message_name}.{field_name}"
        
        # Get or create generator
        if field_path not in self.generators:
            # Use default random generator
            self.generators[field_path] = RandomGenerator()
        
        # Update message count
        if message_name not in self.message_counts:
            self.message_counts[message_name] = 0
        self.message_counts[message_name] += 1
        
        # Create context
        context = GenerationContext(
            time_seconds=time.time() - self.start_time,
            message_count=self.message_counts[message_name],
            message_name=message_name,
            field_name=field_name,
            field_values=field_values or {},
            all_values=self.all_values,
            icd=icd
        )
        
        # Generate value
        value = self.generators[field_path].generate(context)
        
        # Store for cross-references
        if message_name not in self.all_values:
            self.all_values[message_name] = {}
        self.all_values[message_name][field_name] = value
        
        return value
