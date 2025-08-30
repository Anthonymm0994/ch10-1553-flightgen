#!/usr/bin/env python3
"""
Performance tests for scenario-driven data generation.
Tests high message rates and large ICDs.
"""

import pytest
import time
import tempfile
import shutil
from pathlib import Path
import subprocess
import yaml
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestPerformanceScenario:
    """Test performance with high message rates and large ICDs."""
    
    @classmethod
    def setup_class(cls):
        """Set up test environment."""
        cls.test_dir = Path(tempfile.mkdtemp(prefix="test_perf_"))
        cls.project_root = Path(__file__).parent.parent
        
    @classmethod
    def teardown_class(cls):
        """Clean up test environment."""
        if cls.test_dir.exists():
            shutil.rmtree(cls.test_dir)
    
    def test_1000_messages_per_second(self):
        """Test generating 1000+ messages per second."""
        # Create ICD with high rate messages
        icd_data = {
            'name': 'high_rate_test',
            'bus': 'B',
            'description': 'Test ICD for high message rates',
            'messages': []
        }
        
        # Create 10 messages at 100Hz each = 1000 msg/s total
        for i in range(10):
            msg = {
                'name': f'HighRate_{i}',
                'rate_hz': 100,
                'rt': i + 1,
                'tr': 'BC2RT',
                'sa': i + 1,
                'wc': 5,
                'words': []
            }
            # Add 5 words per message
            for j in range(5):
                msg['words'].append({
                    'name': f'word_{j}',
                    'encode': 'u16',
                    'const': 0
                })
            icd_data['messages'].append(msg)
        
        # Create scenario with random data
        scenario_data = {
            'name': 'High Rate Test',
            'duration_s': 5,
            'defaults': {
                'data_mode': 'random',
                'default_config': {'distribution': 'uniform'}
            },
            'messages': {},
            'bus': {
                'utilization_percent': 80,  # High utilization
                'packet_bytes_target': 65536
            }
        }
        
        # Write files
        icd_path = self.test_dir / 'high_rate.yaml'
        scenario_path = self.test_dir / 'high_rate_scenario.yaml'
        output_path = self.test_dir / 'high_rate.ch10'
        
        with open(icd_path, 'w') as f:
            yaml.dump(icd_data, f)
        
        with open(scenario_path, 'w') as f:
            yaml.dump(scenario_data, f)
        
        # Generate CH10 file and measure time
        start_time = time.time()
        result = subprocess.run([
            sys.executable, '-m', 'ch10gen', 'build',
            '-i', str(icd_path),
            '-s', str(scenario_path),
            '-o', str(output_path),
            '--duration', '5'
        ], capture_output=True, text=True)
        generation_time = time.time() - start_time
        
        assert result.returncode == 0, f"Build failed: {result.stderr}"
        assert output_path.exists()
        
        # Parse output to get message count
        lines = result.stdout.split('\n')
        message_count = 0
        for line in lines:
            if 'Messages:' in line:
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == 'Messages:' and i + 1 < len(parts):
                        # Remove comma from number
                        count_str = parts[i + 1].replace(',', '')
                        message_count = int(count_str)
                        break
        
        # Calculate actual message rate
        expected_messages = 1000 * 5  # 1000 msg/s * 5 seconds
        actual_rate = message_count / 5 if message_count > 0 else 0
        
        print(f"\nPerformance Results:")
        print(f"  Generation time: {generation_time:.2f} seconds")
        print(f"  Messages generated: {message_count}")
        print(f"  Expected messages: ~{expected_messages}")
        print(f"  Actual rate: {actual_rate:.0f} msg/s")
        print(f"  File size: {output_path.stat().st_size / 1024:.1f} KB")
        
        # Performance assertions
        assert generation_time < 10, f"Generation too slow: {generation_time:.2f}s"
        assert message_count > expected_messages * 0.8, f"Too few messages: {message_count} < {expected_messages * 0.8}"
        assert actual_rate > 800, f"Rate too low: {actual_rate:.0f} msg/s"
    
    def test_large_icd_performance(self):
        """Test performance with extra large ICD."""
        # Use the generated xlarge ICD
        icd_path = self.project_root / 'icd' / 'test' / 'test_xlarge.yaml'
        scenario_path = self.project_root / 'scenarios' / 'test_large.yaml'
        output_path = self.test_dir / 'xlarge.ch10'
        
        if not icd_path.exists():
            pytest.skip("Extra large test ICD not found")
        
        # Measure generation time
        start_time = time.time()
        result = subprocess.run([
            sys.executable, '-m', 'ch10gen', 'build',
            '-i', str(icd_path),
            '-s', str(scenario_path),
            '-o', str(output_path),
            '--duration', '2'
        ], capture_output=True, text=True, timeout=60)
        generation_time = time.time() - start_time
        
        assert result.returncode == 0, f"Build failed: {result.stderr}"
        assert output_path.exists()
        
        # Get ICD size
        icd_size = icd_path.stat().st_size / 1024  # KB
        output_size = output_path.stat().st_size / 1024  # KB
        
        print(f"\nLarge ICD Performance:")
        print(f"  ICD size: {icd_size:.1f} KB")
        print(f"  Generation time: {generation_time:.2f} seconds")
        print(f"  Output size: {output_size:.1f} KB")
        print(f"  Generation rate: {output_size / generation_time:.1f} KB/s")
        
        # Performance assertions
        assert generation_time < 30, f"Generation too slow for large ICD: {generation_time:.2f}s"
    
    def test_all_generators_performance(self):
        """Test performance with all generator types active."""
        # Create ICD with various fields
        icd_data = {
            'name': 'all_gen_perf',
            'bus': 'B',
            'description': 'Performance test with all generators',
            'messages': [
                {
                    'name': 'Complex Message',
                    'rate_hz': 50,
                    'rt': 1,
                    'tr': 'BC2RT',
                    'sa': 1,
                    'wc': 20,
                    'words': [{'name': f'field_{i}', 'encode': 'u16', 'const': 0} for i in range(20)]
                }
            ]
        }
        
        # Create scenario using all generator types
        scenario_data = {
            'name': 'All Generators Performance',
            'duration_s': 10,
            'messages': {
                'Complex Message': {
                    'fields': {
                        'field_0': {'mode': 'constant', 'value': 100},
                        'field_1': {'mode': 'increment', 'start': 0, 'step': 1},
                        'field_2': {'mode': 'pattern', 'values': [1, 2, 3, 4, 5]},
                        'field_3': {'mode': 'sine', 'amplitude': 100, 'frequency': 1.0},
                        'field_4': {'mode': 'cosine', 'amplitude': 100, 'frequency': 1.0},
                        'field_5': {'mode': 'square', 'amplitude': 100, 'frequency': 1.0},
                        'field_6': {'mode': 'sawtooth', 'amplitude': 100, 'frequency': 1.0},
                        'field_7': {'mode': 'ramp', 'start': 0, 'end': 1000, 'duration': 10.0},
                        'field_8': {'mode': 'random', 'distribution': 'uniform'},
                        'field_9': {'mode': 'random', 'distribution': 'normal', 'mean': 500, 'std_dev': 50},
                        'field_10': {
                            'mode': 'random',
                            'distribution': 'multimodal',
                            'modes': [
                                {'mean': 100, 'std_dev': 10, 'weight': 0.5},
                                {'mean': 900, 'std_dev': 10, 'weight': 0.5}
                            ]
                        },
                        'field_11': {'mode': 'expression', 'formula': 'field_0 + field_1'},
                        'field_12': {'mode': 'expression', 'formula': 'field_3 * 2'},
                        'field_13': {'mode': 'expression', 'formula': 'abs(field_4 - field_5)'},
                        # Remaining fields use default random
                    }
                }
            }
        }
        
        # Write files
        icd_path = self.test_dir / 'all_gen.yaml'
        scenario_path = self.test_dir / 'all_gen_scenario.yaml'
        output_path = self.test_dir / 'all_gen.ch10'
        
        with open(icd_path, 'w') as f:
            yaml.dump(icd_data, f)
        
        with open(scenario_path, 'w') as f:
            yaml.dump(scenario_data, f)
        
        # Measure generation time
        start_time = time.time()
        result = subprocess.run([
            sys.executable, '-m', 'ch10gen', 'build',
            '-i', str(icd_path),
            '-s', str(scenario_path),
            '-o', str(output_path),
            '--duration', '10'
        ], capture_output=True, text=True)
        generation_time = time.time() - start_time
        
        assert result.returncode == 0, f"Build failed: {result.stderr}"
        assert output_path.exists()
        
        print(f"\nAll Generators Performance:")
        print(f"  Generation time: {generation_time:.2f} seconds")
        print(f"  Output size: {output_path.stat().st_size / 1024:.1f} KB")
        print(f"  Time per second of data: {generation_time / 10:.3f}s")
        
        # Performance assertion - should handle complex scenarios efficiently
        assert generation_time < 5, f"Generation too slow with all generators: {generation_time:.2f}s"


def run_tests():
    """Run the performance test suite."""
    print("\n" + "="*60)
    print("Running Performance Tests")
    print("="*60)
    
    # Run pytest with verbose output
    pytest.main([__file__, '-v', '--tb=short', '-s'])


if __name__ == '__main__':
    run_tests()
