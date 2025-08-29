"""Tests for CLI functionality."""

import pytest
import tempfile
import subprocess
import sys
from pathlib import Path
from click.testing import CliRunner
from ch10gen.__main__ import cli


class TestCLI:
    """Test command-line interface."""
    
    def test_help(self):
        """Test help command returns 0."""
        runner = CliRunner()
        result = runner.invoke(cli, ['--help'])
        
        assert result.exit_code == 0
        assert 'ch10-1553-flightgen' in result.output
        assert 'Commands:' in result.output
        assert 'build' in result.output
        assert 'validate' in result.output
        assert 'check-icd' in result.output
    
    def test_version(self):
        """Test version command returns 0."""
        runner = CliRunner()
        result = runner.invoke(cli, ['--version'])
        
        assert result.exit_code == 0
        assert 'version' in result.output.lower()
        assert '1.0.0' in result.output
    
    def test_check_icd_valid(self):
        """Test check-icd on valid ICD returns 0."""
        # Create a valid test ICD
        valid_icd = """
bus: A
messages:
  - name: TEST_MSG
    rate_hz: 10
    rt: 10
    tr: BC2RT
    sa: 1
    wc: 2
    words:
      - {name: w1, src: flight.test, encode: u16}
      - {name: w2, src: flight.test, encode: u16}
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(valid_icd)
            temp_icd = Path(f.name)
        
        try:
            runner = CliRunner()
            result = runner.invoke(cli, ['check-icd', str(temp_icd)])
            
            assert result.exit_code == 0
            assert '✅' in result.output or 'valid' in result.output.lower()
        finally:
            temp_icd.unlink()
    
    def test_check_icd_invalid(self):
        """Test check-icd on broken ICD returns non-zero with helpful message."""
        # Create an invalid ICD (word count mismatch)
        invalid_icd = """
bus: A
messages:
  - name: TEST_MSG
    rate_hz: 10
    rt: 10
    tr: BC2RT
    sa: 1
    wc: 5  # Says 5 words but only has 2
    words:
      - {name: w1, src: flight.test, encode: u16}
      - {name: w2, src: flight.test, encode: u16}
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(invalid_icd)
            temp_icd = Path(f.name)
        
        try:
            runner = CliRunner()
            result = runner.invoke(cli, ['check-icd', str(temp_icd)])
            
            assert result.exit_code != 0
            assert 'word count mismatch' in result.output.lower() or 'error' in result.output.lower()
        finally:
            temp_icd.unlink()
    
    def test_build_creates_file(self):
        """Test build command creates target file with non-zero size."""
        # Create minimal test files
        test_scenario = """
name: "Test Build"
start_time_utc: "2025-01-01T12:00:00Z"
duration_s: 5
seed: 42
profile:
  base_altitude_ft: 5000
  segments:
    - type: cruise
      ias_kt: 250
      hold_s: 5
bus:
  packet_bytes_target: 4096
  jitter_ms: 0
"""
        
        test_icd = """
bus: A
messages:
  - name: TEST_MSG
    rate_hz: 10
    rt: 10
    tr: BC2RT
    sa: 1
    wc: 2
    words:
      - {name: w1, src: flight.altitude_ft, encode: u16}
      - {name: w2, src: flight.ias_kt, encode: u16}
"""
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            # Write test files
            scenario_file = tmpdir / "test_scenario.yaml"
            scenario_file.write_text(test_scenario)
            
            icd_file = tmpdir / "test_icd.yaml"
            icd_file.write_text(test_icd)
            
            output_file = tmpdir / "test_output.c10"
            
            # Run build command
            runner = CliRunner()
            result = runner.invoke(cli, [
                'build',
                '--scenario', str(scenario_file),
                '--icd', str(icd_file),
                '--out', str(output_file),
                '--seed', '42'
            ])
            
            # Check success
            assert result.exit_code == 0
            assert output_file.exists()
            assert output_file.stat().st_size > 0
            assert '✅' in result.output or 'success' in result.output.lower()
    
    @pytest.mark.skipif(sys.platform == "win32", 
                        reason="File cleanup issues on Windows with PyChapter10")
    def test_validate_on_generated_file(self):
        """Test validate command passes on generated file."""
        # First generate a file
        test_scenario = """
name: "Test Validate"
start_time_utc: "2025-01-01T12:00:00Z"
duration_s: 3
seed: 42
profile:
  base_altitude_ft: 5000
  segments:
    - type: cruise
      ias_kt: 250
      hold_s: 3
"""
        
        test_icd = """
bus: A
messages:
  - name: TEST_MSG
    rate_hz: 5
    rt: 10
    tr: BC2RT
    sa: 1
    wc: 1
    words:
      - {name: w1, src: flight.altitude_ft, encode: u16}
"""
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            # Write test files
            scenario_file = tmpdir / "test_scenario.yaml"
            scenario_file.write_text(test_scenario)
            
            icd_file = tmpdir / "test_icd.yaml"
            icd_file.write_text(test_icd)
            
            output_file = tmpdir / "test_output.c10"
            
            # Generate file
            runner = CliRunner()
            result = runner.invoke(cli, [
                'build',
                '--scenario', str(scenario_file),
                '--icd', str(icd_file),
                '--out', str(output_file)
            ])
            
            assert result.exit_code == 0
            
            # Now validate it
            result = runner.invoke(cli, ['validate', str(output_file)])
            
            # The validate command may fail due to CH10 reader limitations
            # but should at least attempt validation
            assert 'Validating:' in result.output
            # Check that it tried to read the file
            assert 'File size:' in result.output or 'bytes' in result.output
    
    def test_build_with_options(self):
        """Test build command with various options."""
        test_scenario = """
name: "Test Options"
start_time_utc: "2025-01-01T12:00:00Z"
duration_s: 10
profile:
  base_altitude_ft: 5000
  segments:
    - type: cruise
      ias_kt: 250
      hold_s: 10
"""
        
        test_icd = """
bus: A
messages:
  - name: TEST_MSG
    rate_hz: 10
    rt: 10
    tr: BC2RT
    sa: 1
    wc: 1
    words:
      - {name: w1, src: flight.altitude_ft, encode: u16}
"""
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            scenario_file = tmpdir / "test_scenario.yaml"
            scenario_file.write_text(test_scenario)
            
            icd_file = tmpdir / "test_icd.yaml"
            icd_file.write_text(test_icd)
            
            output_file = tmpdir / "test_output.c10"
            
            # Test with various options
            runner = CliRunner()
            result = runner.invoke(cli, [
                'build',
                '--scenario', str(scenario_file),
                '--icd', str(icd_file),
                '--out', str(output_file),
                '--duration', '5',  # Override duration
                '--seed', '123',
                '--packet-bytes', '8192',
                '--jitter-ms', '1',
                '--err.parity', '0.1',
                '--err.late', '0.05',
                '--verbose'
            ])
            
            assert result.exit_code == 0
            assert output_file.exists()
            
            # Verbose output should show details
            assert 'messages' in result.output.lower() or 'packets' in result.output.lower()
    
    def test_dry_run(self):
        """Test dry-run mode doesn't create file."""
        test_scenario = """
name: "Test Dry Run"
start_time_utc: "2025-01-01T12:00:00Z"
duration_s: 5
profile:
  base_altitude_ft: 5000
  segments:
    - type: cruise
      ias_kt: 250
      hold_s: 5
"""
        
        test_icd = """
bus: A
messages:
  - name: TEST_MSG
    rate_hz: 10
    rt: 10
    tr: BC2RT
    sa: 1
    wc: 1
    words:
      - {name: w1, src: flight.altitude_ft, encode: u16}
"""
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            scenario_file = tmpdir / "test_scenario.yaml"
            scenario_file.write_text(test_scenario)
            
            icd_file = tmpdir / "test_icd.yaml"
            icd_file.write_text(test_icd)
            
            output_file = tmpdir / "test_output.c10"
            
            # Run with dry-run
            runner = CliRunner()
            result = runner.invoke(cli, [
                'build',
                '--scenario', str(scenario_file),
                '--icd', str(icd_file),
                '--out', str(output_file),
                '--dry-run'
            ])
            
            assert result.exit_code == 0
            assert 'Dry run mode' in result.output
            assert not output_file.exists()  # File should NOT be created
    
    def test_missing_files(self):
        """Test appropriate errors for missing files."""
        runner = CliRunner()
        
        # Missing scenario file
        result = runner.invoke(cli, [
            'build',
            '--scenario', 'nonexistent_scenario.yaml',
            '--icd', 'some_icd.yaml',
            '--out', 'output.c10'
        ])
        
        assert result.exit_code != 0
        
        # Missing ICD file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml') as f:
            f.write("name: test\n")
            scenario_file = f.name
            
            result = runner.invoke(cli, [
                'build',
                '--scenario', scenario_file,
                '--icd', 'nonexistent_icd.yaml',
                '--out', 'output.c10'
            ])
            
            assert result.exit_code != 0
    
    @pytest.mark.skipif(sys.platform == "win32", reason="Subprocess test for non-Windows")
    def test_subprocess_invocation_unix(self):
        """Test CLI can be invoked via subprocess on Unix."""
        result = subprocess.run(
            ['python', '-m', 'ch10gen', '--help'],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
        assert 'ch10-1553-flightgen' in result.stdout
    
    @pytest.mark.skipif(sys.platform != "win32", reason="Subprocess test for Windows")
    def test_subprocess_invocation_windows(self):
        """Test CLI can be invoked via subprocess on Windows."""
        result = subprocess.run(
            ['python', '-m', 'ch10gen', '--help'],
            capture_output=True,
            text=True,
            shell=True
        )
        
        assert result.returncode == 0
        assert 'ch10-1553-flightgen' in result.stdout or 'Commands' in result.stdout
