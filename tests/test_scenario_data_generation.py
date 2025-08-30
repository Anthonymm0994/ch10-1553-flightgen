"""
Comprehensive tests for scenario-driven data generation.
Tests all generator types, field references, and CH10 output validity.
"""

import pytest
import tempfile
import yaml
import math
import numpy as np
from pathlib import Path
from typing import Dict, Any, List

# Import our modules
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from ch10gen.data_generators import (
    GeneratorFactory, RandomGenerator, RandomNormalGenerator,
    ConstantGenerator, IncrementGenerator, PatternGenerator,
    SineGenerator, RampGenerator, DataGeneratorManager,
    GenerationContext
)
from ch10gen.scenario_manager import ScenarioManager, FieldReferenceResolver


class TestFieldReferences:
    """Test field reference parsing and resolution."""
    
    def test_same_word_reference(self):
        """Test reference to field in same word."""
        resolver = FieldReferenceResolver()
        msg, word, field = resolver.parse_reference("field1", "Nav Data", 2)
        assert msg == "Nav Data"
        assert word == 2
        assert field == "field1"
    
    def test_same_message_different_word(self):
        """Test reference to different word in same message."""
        resolver = FieldReferenceResolver()
        msg, word, field = resolver.parse_reference("word3.field2", "Nav Data", 1)
        assert msg == "Nav Data"
        assert word == 3
        assert field == "field2"
    
    def test_different_message_reference(self):
        """Test reference to different message."""
        resolver = FieldReferenceResolver()
        msg, word, field = resolver.parse_reference("Engine Data.rpm", "Nav Data", 0)
        assert msg == "Engine Data"
        assert word == -1  # Search all words
        assert field == "rpm"
    
    def test_message_with_spaces(self):
        """Test reference to message with spaces in name."""
        resolver = FieldReferenceResolver()
        msg, word, field = resolver.parse_reference("Navigation Data.altitude", "Engine", 0)
        assert msg == "Navigation Data"
        assert word == -1
        assert field == "altitude"
    
    def test_full_path_reference(self):
        """Test full path with message, word, and field."""
        resolver = FieldReferenceResolver()
        msg, word, field = resolver.parse_reference("Navigation Data.word2.altitude", "Engine", 0)
        assert msg == "Navigation Data"
        assert word == 2
        assert field == "altitude"


class TestGenerators:
    """Test all data generator types."""
    
    def test_random_generator(self):
        """Test uniform random generator."""
        gen = RandomGenerator(min_val=10, max_val=20)
        context = self._create_context()
        
        values = [gen.generate(context) for _ in range(100)]
        assert all(10 <= v <= 20 for v in values)
        assert len(set(values)) > 5  # Should have variety
    
    def test_random_normal_generator(self):
        """Test normal distribution generator."""
        gen = RandomNormalGenerator(mean=50, std_dev=10, min_val=0, max_val=100)
        context = self._create_context()
        
        values = [gen.generate(context) for _ in range(1000)]
        assert all(0 <= v <= 100 for v in values)  # Within bounds
        assert 40 <= np.mean(values) <= 60  # Near mean
        assert 5 <= np.std(values) <= 15  # Reasonable std dev
    
    def test_multimodal_generator(self):
        """Test multimodal distribution generator."""
        from ch10gen.data_generators import RandomMultimodalGenerator
        
        peaks = [
            {'mean': 25, 'std_dev': 5, 'weight': 0.5},
            {'mean': 75, 'std_dev': 5, 'weight': 0.5}
        ]
        gen = RandomMultimodalGenerator(peaks)
        context = self._create_context()
        
        values = [gen.generate(context) for _ in range(1000)]
        # Should have values clustered around 25 and 75
        low_cluster = [v for v in values if v < 50]
        high_cluster = [v for v in values if v >= 50]
        
        assert len(low_cluster) > 300  # Roughly half
        assert len(high_cluster) > 300  # Roughly half
    
    def test_constant_generator(self):
        """Test constant value generator."""
        gen = ConstantGenerator(value=42)
        context = self._create_context()
        
        values = [gen.generate(context) for _ in range(10)]
        assert all(v == 42 for v in values)
    
    def test_increment_generator(self):
        """Test incrementing counter generator."""
        gen = IncrementGenerator(start=10, increment=2, wrap=20)
        context = self._create_context()
        
        values = [gen.generate(context) for _ in range(10)]
        expected = [10, 12, 14, 16, 18, 20, 10, 12, 14, 16]
        assert values == expected
    
    def test_pattern_generator(self):
        """Test pattern generator."""
        gen = PatternGenerator(values=[1, 2, 3, 4], repeat=True)
        context = self._create_context()
        
        values = [gen.generate(context) for _ in range(10)]
        expected = [1, 2, 3, 4, 1, 2, 3, 4, 1, 2]
        assert values == expected
    
    def test_sine_generator(self):
        """Test sine wave generator."""
        gen = SineGenerator(center=50, amplitude=10, frequency=1, phase=0)
        
        # Test at specific time points
        times = [0, 0.25, 0.5, 0.75, 1.0]
        expected = [50, 60, 50, 40, 50]  # sine values at 0, π/2, π, 3π/2, 2π
        
        for t, exp in zip(times, expected):
            context = self._create_context(time_seconds=t)
            value = gen.generate(context)
            assert abs(value - exp) < 0.1  # Close to expected
    
    def test_ramp_generator(self):
        """Test linear ramp generator."""
        gen = RampGenerator(start=0, end=100, duration=10, repeat=False)
        
        # Test at different times
        for t in [0, 2.5, 5, 7.5, 10]:
            context = self._create_context(time_seconds=t)
            value = gen.generate(context)
            expected = t * 10  # Linear from 0 to 100 over 10 seconds
            assert abs(value - expected) < 0.1
    
    def _create_context(self, **kwargs) -> GenerationContext:
        """Create a test generation context."""
        defaults = {
            'time_seconds': 0,
            'message_count': 0,
            'message_name': 'TEST_MSG',
            'field_name': 'test_field',
            'field_values': {},
            'all_values': {},
            'icd': None
        }
        defaults.update(kwargs)
        return GenerationContext(**defaults)


class TestGeneratorFactory:
    """Test generator factory creation."""
    
    def test_create_random(self):
        """Test creating random generator from config."""
        config = {'mode': 'random', 'min': 10, 'max': 20}
        gen = GeneratorFactory.create(config)
        assert isinstance(gen, RandomGenerator)
        assert gen.min_val == 10
        assert gen.max_val == 20
    
    def test_create_sine(self):
        """Test creating sine generator from config."""
        config = {
            'mode': 'sine',
            'center': 100,
            'amplitude': 50,
            'frequency': 0.5
        }
        gen = GeneratorFactory.create(config)
        assert isinstance(gen, SineGenerator)
        assert gen.center == 100
        assert gen.amplitude == 50
    
    def test_default_random(self):
        """Test default generator is random."""
        config = {}  # No mode specified
        gen = GeneratorFactory.create(config)
        assert isinstance(gen, RandomGenerator)
    
    def test_invalid_mode(self):
        """Test error on invalid mode."""
        config = {'mode': 'invalid_mode'}
        with pytest.raises(ValueError, match="Unknown generator mode"):
            GeneratorFactory.create(config)


class TestScenarioIntegration:
    """Test full scenario integration."""
    
    def test_simple_scenario(self):
        """Test simple scenario with mixed generators."""
        # Create test ICD
        icd = self._create_test_icd()
        
        # Create scenario
        scenario = {
            'config': {
                'default_mode': 'random'
            },
            'messages': {
                'NAV_DATA': {
                    'fields': {
                        'altitude': {
                            'mode': 'sine',
                            'center': 10000,
                            'amplitude': 1000,
                            'frequency': 0.1
                        },
                        'speed': {
                            'mode': 'constant',
                            'value': 250
                        }
                    }
                },
                'STATUS': {
                    'fields': {
                        'counter': {
                            'mode': 'increment',
                            'start': 0,
                            'increment': 1
                        }
                    }
                }
            }
        }
        
        # Create manager
        manager = ScenarioManager(scenario, icd)
        
        # Generate data for NAV_DATA
        nav_data = manager.generate_message_data('NAV_DATA', icd.messages[0])
        assert len(nav_data) > 0
        
        # Generate data for STATUS
        status_data = manager.generate_message_data('STATUS', icd.messages[1])
        assert len(status_data) > 0
    
    def test_field_in_same_word(self):
        """Test generating fields in the same word with bitfields."""
        icd = self._create_bitfield_icd()
        
        scenario = {
            'messages': {
                'STATUS_MSG': {
                    'fields': {
                        'flag1': {'mode': 'constant', 'value': 1},
                        'flag2': {'mode': 'constant', 'value': 0},
                        'counter': {'mode': 'increment', 'start': 0}
                    }
                }
            }
        }
        
        manager = ScenarioManager(scenario, icd)
        data = manager.generate_message_data('STATUS_MSG', icd.messages[0])
        
        # Check first word has correct bitfield values
        word0 = data[0]
        assert (word0 & 0x0001) == 1  # flag1 = 1
        assert (word0 & 0x0002) == 0  # flag2 = 0
    
    def test_expression_with_references(self):
        """Test expressions with field references."""
        icd = self._create_test_icd()
        
        scenario = {
            'messages': {
                'NAV_DATA': {
                    'fields': {
                        'altitude': {'mode': 'constant', 'value': 10000},
                        'altitude_meters': {
                            'mode': 'expression',
                            'formula': 'altitude * 0.3048'
                        }
                    }
                }
            }
        }
        
        manager = ScenarioManager(scenario, icd)
        data = manager.generate_message_data('NAV_DATA', icd.messages[0])
        
        # altitude_meters should be altitude * 0.3048
        # Need to check the computed values
        assert 'NAV_DATA' in manager.computed_values
        values = manager.computed_values['NAV_DATA']
        # Find altitude_meters value
        altitude_meters = None
        for word_values in values.values():
            if isinstance(word_values, dict) and 'altitude_meters' in word_values:
                altitude_meters = word_values['altitude_meters']
                break
        
        assert altitude_meters is not None
        assert abs(altitude_meters - 3048) < 0.1  # 10000 * 0.3048
    
    def _create_test_icd(self):
        """Create a simple test ICD."""
        from types import SimpleNamespace
        
        # Create mock ICD structure
        icd = SimpleNamespace()
        icd.messages = [
            SimpleNamespace(
                name='NAV_DATA',
                words=[
                    SimpleNamespace(name='altitude', fields=None),
                    SimpleNamespace(name='speed', fields=None),
                    SimpleNamespace(name='altitude_meters', fields=None)
                ]
            ),
            SimpleNamespace(
                name='STATUS',
                words=[
                    SimpleNamespace(name='counter', fields=None),
                    SimpleNamespace(name='flags', fields=None)
                ]
            )
        ]
        return icd
    
    def _create_bitfield_icd(self):
        """Create ICD with bitfields."""
        from types import SimpleNamespace
        
        icd = SimpleNamespace()
        icd.messages = [
            SimpleNamespace(
                name='STATUS_MSG',
                words=[
                    SimpleNamespace(
                        name='status_word',
                        fields=[
                            SimpleNamespace(name='flag1', mask=0x0001, shift=0),
                            SimpleNamespace(name='flag2', mask=0x0002, shift=1),
                            SimpleNamespace(name='counter', mask=0xFF00, shift=8)
                        ]
                    )
                ]
            )
        ]
        return icd


class TestCH10Generation:
    """Test actual CH10 file generation with scenarios."""
    
    def test_generate_ch10_with_scenario(self):
        """Test generating a CH10 file with scenario data."""
        # Create test ICD file
        icd_content = {
            'name': 'test_icd',
            'bus': 'B',
            'messages': [
                {
                    'name': 'TEST_MSG',
                    'rate_hz': 10,
                    'rt': 10,
                    'tr': 'BC2RT',
                    'sa': 1,
                    'wc': 3,
                    'words': [
                        {'name': 'field1', 'encode': 'u16'},
                        {'name': 'field2', 'encode': 'u16'},
                        {'name': 'field3', 'encode': 'u16'}
                    ]
                }
            ]
        }
        
        # Create scenario
        scenario_content = {
            'name': 'test_scenario',
            'duration': 2,
            'messages': {
                'TEST_MSG': {
                    'fields': {
                        'field1': {'mode': 'constant', 'value': 100},
                        'field2': {'mode': 'increment', 'start': 0},
                        'field3': {'mode': 'random', 'min': 0, 'max': 100}
                    }
                }
            }
        }
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Save ICD
            icd_path = Path(tmpdir) / 'test.yaml'
            with open(icd_path, 'w') as f:
                yaml.dump(icd_content, f)
            
            # Save scenario
            scenario_path = Path(tmpdir) / 'scenario.yaml'
            with open(scenario_path, 'w') as f:
                yaml.dump(scenario_content, f)
            
            # Generate CH10
            output_path = Path(tmpdir) / 'test.ch10'
            
            # Import and run
            from ch10gen.icd import load_icd
            from ch10gen.ch10_writer import write_ch10_file
            
            icd = load_icd(icd_path)
            stats = write_ch10_file(
                output_path=output_path,
                scenario=scenario_content,
                icd=icd,
                seed=42
            )
            
            # Verify file was created
            assert output_path.exists()
            assert stats['total_messages'] > 0
            assert stats['file_size_bytes'] > 0
    
    def test_large_icd_generation(self):
        """Test with a large ICD to ensure scalability."""
        # Create large ICD
        messages = []
        for i in range(100):  # 100 messages
            words = []
            for j in range(10):  # 10 words per message
                words.append({
                    'name': f'word_{j}',
                    'encode': 'u16'
                })
            
            messages.append({
                'name': f'MSG_{i:03d}',
                'rate_hz': 5,
                'rt': 10 + (i % 20),
                'tr': 'BC2RT',
                'sa': 1 + (i % 30),
                'wc': len(words),
                'words': words
            })
        
        icd_content = {
            'name': 'large_test_icd',
            'bus': 'B',
            'messages': messages
        }
        
        # Simple scenario - all random
        scenario_content = {
            'name': 'large_test',
            'duration': 1,
            'config': {
                'default_mode': 'random'
            }
        }
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Save ICD
            icd_path = Path(tmpdir) / 'large.yaml'
            with open(icd_path, 'w') as f:
                yaml.dump(icd_content, f)
            
            # Generate CH10
            output_path = Path(tmpdir) / 'large.ch10'
            
            from ch10gen.icd import load_icd
            from ch10gen.ch10_writer import write_ch10_file
            
            icd = load_icd(icd_path)
            stats = write_ch10_file(
                output_path=output_path,
                scenario=scenario_content,
                icd=icd,
                seed=42
            )
            
            # Verify generation succeeded
            assert output_path.exists()
            assert stats['total_messages'] > 0
            print(f"Generated {stats['total_messages']} messages in {stats['file_size_bytes']} bytes")


def test_all_generators():
    """Run all generator tests."""
    # Test field references
    ref_tests = TestFieldReferences()
    ref_tests.test_same_word_reference()
    ref_tests.test_same_message_different_word()
    ref_tests.test_different_message_reference()
    ref_tests.test_message_with_spaces()
    ref_tests.test_full_path_reference()
    
    # Test generators
    gen_tests = TestGenerators()
    gen_tests.test_random_generator()
    gen_tests.test_random_normal_generator()
    gen_tests.test_multimodal_generator()
    gen_tests.test_constant_generator()
    gen_tests.test_increment_generator()
    gen_tests.test_pattern_generator()
    gen_tests.test_sine_generator()
    gen_tests.test_ramp_generator()
    
    # Test factory
    factory_tests = TestGeneratorFactory()
    factory_tests.test_create_random()
    factory_tests.test_create_sine()
    factory_tests.test_default_random()
    
    # Test scenario integration
    scenario_tests = TestScenarioIntegration()
    scenario_tests.test_simple_scenario()
    scenario_tests.test_field_in_same_word()
    
    print("SUCCESS: All generator tests passed!")


if __name__ == '__main__':
    test_all_generators()
