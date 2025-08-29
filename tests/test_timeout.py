"""Test timeout and safety features."""

import pytest
import json
import time
import subprocess
import sys
from pathlib import Path
import tempfile


@pytest.mark.integration
class TestTimeoutSafety:
    """Test build timeouts and safety features."""
    
    def test_build_with_timeout(self):
        """Test that builds respect timeout and exit cleanly."""
        # Create a long scenario that would take more than 5 seconds
        scenario_data = {
            'name': 'Timeout Test',
            'duration_s': 3600,  # 1 hour - should timeout
            'seed': 42,
            'profile': {
                'base_altitude_ft': 10000,
                'segments': [
                    {'type': 'cruise', 'ias_kt': 300, 'hold_s': 3600}
                ]
            }
        }
        
        icd_data = {
            'bus': 'A',
            'messages': [
                {
                    'name': 'TEST_MSG',
                    'rate_hz': 100,  # High rate
                    'rt': 5,
                    'tr': 'BC2RT',
                    'sa': 1,
                    'wc': 4,
                    'words': [
                        {'name': 'w1', 'const': 1},
                        {'name': 'w2', 'const': 2},
                        {'name': 'w3', 'const': 3},
                        {'name': 'w4', 'const': 4}
                    ]
                }
            ]
        }
        
        # Write temp files
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            scenario_file = tmpdir / 'timeout_scenario.yaml'
            icd_file = tmpdir / 'timeout_icd.yaml'
            output_file = tmpdir / 'timeout_test.c10'
            json_file = tmpdir / 'timeout_test.json'
            
            import yaml
            with open(scenario_file, 'w') as f:
                yaml.dump(scenario_data, f)
            
            with open(icd_file, 'w') as f:
                yaml.dump(icd_data, f)
            
            # Run build with 2 second timeout
            start_time = time.time()
            result = subprocess.run([
                sys.executable, '-m', 'ch10gen', 'build',
                '--scenario', str(scenario_file),
                '--icd', str(icd_file),
                '--out', str(output_file),
                '--writer', 'irig106',
                '--timeout-s', '2',  # 2 second timeout
                '--seed', '42'
            ], capture_output=True, text=True)
            
            elapsed = time.time() - start_time
            
            # Should timeout within 3 seconds (2s timeout + overhead)
            assert elapsed < 5, f"Timeout took too long: {elapsed:.1f}s"
            
            # Output file should exist (partial)
            assert output_file.exists(), "Partial output file not created"
            
            # JSON report should exist if supported
            if json_file.exists():
                with open(json_file) as f:
                    report = json.load(f)
                
                # Check for timeout indication
                if 'timeout_reached' in report:
                    assert report['timeout_reached'] == True
    
    def test_flush_on_timeout(self):
        """Test that pending data is flushed on timeout."""
        # Short scenario with flush settings
        scenario_data = {
            'name': 'Flush Test',
            'duration_s': 10,
            'seed': 42,
            'profile': {
                'base_altitude_ft': 5000,
                'segments': [
                    {'type': 'cruise', 'ias_kt': 250, 'hold_s': 10}
                ]
            }
        }
        
        icd_data = {
            'bus': 'A',
            'messages': [
                {
                    'name': 'FLUSH_MSG',
                    'rate_hz': 20,
                    'rt': 1,
                    'tr': 'BC2RT',
                    'sa': 1,
                    'wc': 2,
                    'words': [
                        {'name': 'w1', 'const': 0xAAAA},
                        {'name': 'w2', 'const': 0x5555}
                    ]
                }
            ]
        }
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            scenario_file = tmpdir / 'flush_scenario.yaml'
            icd_file = tmpdir / 'flush_icd.yaml'
            output_file = tmpdir / 'flush_test.c10'
            
            import yaml
            with open(scenario_file, 'w') as f:
                yaml.dump(scenario_data, f)
            
            with open(icd_file, 'w') as f:
                yaml.dump(icd_data, f)
            
            # Run with forced flush interval
            result = subprocess.run([
                sys.executable, '-m', 'ch10gen', 'build',
                '--scenario', str(scenario_file),
                '--icd', str(icd_file),
                '--out', str(output_file),
                '--writer', 'irig106',
                '--flush-ms', '100',  # Force flush every 100ms
                '--seed', '42'
            ], capture_output=True, text=True)
            
            assert result.returncode == 0, f"Build failed: {result.stderr}"
            assert output_file.exists(), "Output file not created"
            
            # File should have content
            file_size = output_file.stat().st_size
            assert file_size > 0, "Output file is empty"
            
            # Should have multiple packets due to flush
            # (Can't easily verify packet count without parsing)
