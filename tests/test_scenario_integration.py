#!/usr/bin/env python3
"""
Integration tests for scenario-driven data generation.
Tests the complete pipeline from scenario -> CH10 file generation.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
import subprocess
import json
import yaml
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ch10gen.icd import ICDDefinition
from ch10gen.scenario_manager import ScenarioManager
from ch10gen.ch10_writer import write_ch10_file


class TestScenarioIntegration:
    """Test complete scenario-driven data generation pipeline."""
    
    @classmethod
    def setup_class(cls):
        """Set up test environment."""
        cls.test_dir = Path(tempfile.mkdtemp(prefix="test_scenario_"))
        cls.project_root = Path(__file__).parent.parent
        
    @classmethod
    def teardown_class(cls):
        """Clean up test environment."""
        if cls.test_dir.exists():
            shutil.rmtree(cls.test_dir)
    
    def test_basic_random_generation(self):
        """Test basic random data generation."""
        # Create simple ICD
        icd_data = {
            'name': 'test_random',
            'bus': 'B',
            'description': 'Test ICD for random generation',
            'messages': [
                {
                    'name': 'Test Message',
                    'rate_hz': 10,
                    'rt': 1,
                    'tr': 'BC2RT',
                    'sa': 1,
                    'wc': 3,
                    'words': [
                        {'name': 'field1', 'encode': 'u16', 'const': 0},
                        {'name': 'field2', 'encode': 'i16', 'const': 0},
                        {'name': 'field3', 'encode': 'u16', 'const': 0}
                    ]
                }
            ]
        }
        
        # Create scenario with random data
        scenario_data = {
            'name': 'Random Test',
            'duration_s': 2,
            'defaults': {
                'data_mode': 'random',
                'default_config': {'distribution': 'uniform'}
            },
            'messages': {}
        }
        
        # Write files
        icd_path = self.test_dir / 'test.yaml'
        scenario_path = self.test_dir / 'scenario.yaml'
        output_path = self.test_dir / 'output.ch10'
        
        with open(icd_path, 'w') as f:
            yaml.dump(icd_data, f)
        
        with open(scenario_path, 'w') as f:
            yaml.dump(scenario_data, f)
        
        # Generate CH10 file
        result = subprocess.run([
            sys.executable, '-m', 'ch10gen', 'build',
            '-i', str(icd_path),
            '-s', str(scenario_path),
            '-o', str(output_path),
            '--duration', '1'
        ], capture_output=True, text=True)
        
        assert result.returncode == 0, f"Build failed: {result.stderr}"
        assert output_path.exists()
        assert output_path.stat().st_size > 0
        
    def test_all_generator_types(self):
        """Test all data generator types."""
        # Create ICD with multiple messages
        icd_data = {
            'name': 'test_generators',
            'bus': 'B',
            'description': 'Test all generator types',
            'messages': [
                {
                    'name': 'Generator Test',
                    'rate_hz': 20,
                    'rt': 1,
                    'tr': 'BC2RT',
                    'sa': 1,
                    'wc': 10,
                    'words': [
                        {'name': 'constant_field', 'encode': 'u16', 'const': 0},
                        {'name': 'increment_field', 'encode': 'u16', 'const': 0},
                        {'name': 'sine_field', 'encode': 'u16', 'const': 0},
                        {'name': 'ramp_field', 'encode': 'u16', 'const': 0},
                        {'name': 'normal_field', 'encode': 'u16', 'const': 0},
                        {'name': 'pattern_field', 'encode': 'u16', 'const': 0},
                        {'name': 'expr_field', 'encode': 'u16', 'const': 0},
                        {'name': 'multimodal_field', 'encode': 'u16', 'const': 0},
                        {'name': 'square_field', 'encode': 'u16', 'const': 0},
                        {'name': 'sawtooth_field', 'encode': 'u16', 'const': 0}
                    ]
                }
            ]
        }
        
        # Create scenario with all generator types
        scenario_data = {
            'name': 'All Generators Test',
            'duration_s': 2,
            'messages': {
                'Generator Test': {
                    'fields': {
                        'constant_field': {'mode': 'constant', 'value': 42},
                        'increment_field': {'mode': 'increment', 'start': 0, 'step': 1},
                        'sine_field': {'mode': 'sine', 'amplitude': 100, 'frequency': 1.0},
                        'ramp_field': {'mode': 'ramp', 'start': 0, 'end': 1000, 'duration': 2.0},
                        'normal_field': {'mode': 'random', 'distribution': 'normal', 'mean': 500, 'std_dev': 50},
                        'pattern_field': {'mode': 'pattern', 'values': [1, 2, 3, 4, 5]},
                        'expr_field': {'mode': 'expression', 'formula': 'constant_field * 2'},
                        'multimodal_field': {
                            'mode': 'random',
                            'distribution': 'multimodal',
                            'modes': [
                                {'mean': 100, 'std_dev': 10, 'weight': 0.3},
                                {'mean': 500, 'std_dev': 20, 'weight': 0.7}
                            ]
                        },
                        'square_field': {'mode': 'square', 'amplitude': 50, 'frequency': 2.0},
                        'sawtooth_field': {'mode': 'sawtooth', 'amplitude': 75, 'frequency': 1.5}
                    }
                }
            }
        }
        
        # Write files
        icd_path = self.test_dir / 'generators.yaml'
        scenario_path = self.test_dir / 'gen_scenario.yaml'
        output_path = self.test_dir / 'generators.ch10'
        
        with open(icd_path, 'w') as f:
            yaml.dump(icd_data, f)
        
        with open(scenario_path, 'w') as f:
            yaml.dump(scenario_data, f)
        
        # Generate CH10 file
        result = subprocess.run([
            sys.executable, '-m', 'ch10gen', 'build',
            '-i', str(icd_path),
            '-s', str(scenario_path),
            '-o', str(output_path),
            '--duration', '2'
        ], capture_output=True, text=True)
        
        assert result.returncode == 0, f"Build failed: {result.stderr}"
        assert output_path.exists()
        
    def test_field_references(self):
        """Test field references in expressions."""
        # Create ICD with multiple messages
        icd_data = {
            'name': 'test_references',
            'bus': 'B',
            'description': 'Test field references',
            'messages': [
                {
                    'name': 'Source Message',
                    'rate_hz': 10,
                    'rt': 1,
                    'tr': 'BC2RT',
                    'sa': 1,
                    'wc': 2,
                    'words': [
                        {'name': 'source1', 'encode': 'u16', 'const': 0},
                        {'name': 'source2', 'encode': 'u16', 'const': 0}
                    ]
                },
                {
                    'name': 'Reference Message',
                    'rate_hz': 10,
                    'rt': 2,
                    'tr': 'BC2RT',
                    'sa': 2,
                    'wc': 3,
                    'words': [
                        {'name': 'same_word_ref', 'encode': 'u16', 'const': 0},
                        {'name': 'same_msg_ref', 'encode': 'u16', 'const': 0},
                        {'name': 'cross_msg_ref', 'encode': 'u16', 'const': 0}
                    ]
                }
            ]
        }
        
        # Create scenario with field references
        scenario_data = {
            'name': 'Reference Test',
            'duration_s': 1,
            'messages': {
                'Source Message': {
                    'fields': {
                        'source1': {'mode': 'constant', 'value': 100},
                        'source2': {'mode': 'constant', 'value': 200}
                    }
                },
                'Reference Message': {
                    'fields': {
                        'same_word_ref': {'mode': 'constant', 'value': 10},
                        'same_msg_ref': {'mode': 'expression', 'formula': 'same_word_ref * 2'},
                        'cross_msg_ref': {'mode': 'expression', 'formula': '"Source Message".source1 + "Source Message".source2'}
                    }
                }
            }
        }
        
        # Write files
        icd_path = self.test_dir / 'references.yaml'
        scenario_path = self.test_dir / 'ref_scenario.yaml'
        output_path = self.test_dir / 'references.ch10'
        
        with open(icd_path, 'w') as f:
            yaml.dump(icd_data, f)
        
        with open(scenario_path, 'w') as f:
            yaml.dump(scenario_data, f)
        
        # Generate CH10 file
        result = subprocess.run([
            sys.executable, '-m', 'ch10gen', 'build',
            '-i', str(icd_path),
            '-s', str(scenario_path),
            '-o', str(output_path),
            '--duration', '1'
        ], capture_output=True, text=True)
        
        assert result.returncode == 0, f"Build failed: {result.stderr}"
        assert output_path.exists()
        
    def test_large_icd_performance(self):
        """Test performance with large ICD."""
        # Use the generated large ICD
        icd_path = self.project_root / 'icd' / 'test' / 'test_large.yaml'
        scenario_path = self.project_root / 'scenarios' / 'test_large.yaml'
        output_path = self.test_dir / 'large.ch10'
        
        if not icd_path.exists():
            pytest.skip("Large test ICD not found")
        
        # Generate CH10 file
        result = subprocess.run([
            sys.executable, '-m', 'ch10gen', 'build',
            '-i', str(icd_path),
            '-s', str(scenario_path),
            '-o', str(output_path),
            '--duration', '1'
        ], capture_output=True, text=True, timeout=30)
        
        assert result.returncode == 0, f"Build failed: {result.stderr}"
        assert output_path.exists()
        
        # Check file size is reasonable
        file_size = output_path.stat().st_size
        assert file_size > 1000, "Output file too small"
        assert file_size < 100_000_000, "Output file too large"


def run_tests():
    """Run the test suite."""
    print("\n" + "="*60)
    print("Running Scenario Integration Tests")
    print("="*60)
    
    # Run pytest with verbose output
    pytest.main([__file__, '-v', '--tb=short'])


if __name__ == '__main__':
    run_tests()
