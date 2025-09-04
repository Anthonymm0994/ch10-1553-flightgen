"""Tests for report generation."""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime

from ch10gen.report import (
    generate_report,
    generate_summary_report,
    load_report,
    compare_reports
)


class TestGenerateReport:
    """Test report generation."""
    
    def test_basic_report(self):
        """Test basic report generation."""
        stats = {
            'file_size_bytes': 1024,
            'total_packets': 10,
            'total_messages': 100,
            'duration_s': 5.0,
            'backend': 'irig106',
            'spec_compliant': True
        }
        
        report = generate_report(stats)
        
        assert 'timestamp' in report
        assert report['file_stats']['size_bytes'] == 1024
        assert report['file_stats']['total_packets'] == 10
        assert report['file_stats']['total_messages'] == 100
        assert report['file_stats']['duration_seconds'] == 5.0
        assert report['backend'] == 'irig106'
        assert report['spec_compliant'] == True
        
    def test_report_with_timing(self):
        """Test report with timing information."""
        stats = {
            'first_time': '2024-01-01T00:00:00Z',
            'last_time': '2024-01-01T00:01:00Z'
        }
        
        report = generate_report(stats)
        
        assert 'timing' in report
        assert report['timing']['first_time'] == '2024-01-01T00:00:00Z'
        assert report['timing']['last_time'] == '2024-01-01T00:01:00Z'
        
    def test_report_with_distribution(self):
        """Test report with RT/SA distribution."""
        stats = {
            'rt_sa_distribution': {
                '1_1': 50,
                '1_2': 25,
                '2_1': 25
            }
        }
        
        report = generate_report(stats)
        
        assert 'rt_sa_distribution' in report
        assert report['rt_sa_distribution']['1_1'] == 50
        assert report['rt_sa_distribution']['1_2'] == 25
        
    def test_report_with_errors(self):
        """Test report with error statistics."""
        stats = {
            'error_stats': {
                'invalid_packets': 2,
                'crc_errors': 1
            }
        }
        
        report = generate_report(stats)
        
        assert 'error_stats' in report
        assert report['error_stats']['invalid_packets'] == 2
        assert report['error_stats']['crc_errors'] == 1
        
    def test_save_report_to_file(self):
        """Test saving report to file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = Path(f.name)
        
        try:
            stats = {
                'file_size_bytes': 2048,
                'total_packets': 20
            }
            
            report = generate_report(stats, temp_path)
            
            # File should exist
            assert temp_path.exists()
            
            # Load and verify
            with open(temp_path, 'r') as f:
                saved = json.load(f)
            
            assert saved['file_stats']['size_bytes'] == 2048
            assert saved['file_stats']['total_packets'] == 20
            
        finally:
            temp_path.unlink()


class TestSummaryReport:
    """Test summary report generation."""
    
    def test_generate_summary_report(self):
        """Test generating summary report next to CH10 file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ch10_path = Path(tmpdir) / "test.c10"
            ch10_path.write_text("dummy")  # Create dummy file
            
            stats = {
                'file_size_bytes': 4096,
                'total_messages': 200
            }
            
            report_path = generate_summary_report(ch10_path, stats)
            
            # Report should be next to CH10 file
            assert report_path == ch10_path.with_suffix('.json')
            assert report_path.exists()
            
            # Load and verify
            report = load_report(report_path)
            assert report['file_stats']['size_bytes'] == 4096
            assert report['file_stats']['total_messages'] == 200
            
            # Should have CH10 file info
            assert 'ch10_file' in report
            assert report['ch10_file']['name'] == 'test.c10'
            assert report['ch10_file']['path'] == str(ch10_path)


class TestLoadReport:
    """Test loading reports."""
    
    def test_load_report(self):
        """Test loading a JSON report."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            data = {
                'timestamp': '2024-01-01T12:00:00',
                'file_stats': {
                    'size_bytes': 1024
                }
            }
            json.dump(data, f)
            temp_path = Path(f.name)
        
        try:
            report = load_report(temp_path)
            
            assert report['timestamp'] == '2024-01-01T12:00:00'
            assert report['file_stats']['size_bytes'] == 1024
            
        finally:
            temp_path.unlink()


class TestCompareReports:
    """Test report comparison."""
    
    def test_identical_reports(self):
        """Test comparing identical reports."""
        report1 = {
            'file_stats': {
                'size_bytes': 1024,
                'total_packets': 10,
                'total_messages': 100
            }
        }
        
        report2 = report1.copy()
        
        comparison = compare_reports(report1, report2)
        
        assert comparison['files_match'] == True
        assert len(comparison['differences']) == 0
        
    def test_different_sizes(self):
        """Test comparing reports with different sizes."""
        report1 = {
            'file_stats': {
                'size_bytes': 1024
            }
        }
        
        report2 = {
            'file_stats': {
                'size_bytes': 2048
            }
        }
        
        comparison = compare_reports(report1, report2)
        
        assert comparison['files_match'] == False
        assert 'Size: 1024 vs 2048' in comparison['differences']
        
    def test_different_packets(self):
        """Test comparing reports with different packet counts."""
        report1 = {
            'file_stats': {
                'total_packets': 10,
                'total_messages': 100
            }
        }
        
        report2 = {
            'file_stats': {
                'total_packets': 20,
                'total_messages': 100
            }
        }
        
        comparison = compare_reports(report1, report2)
        
        assert comparison['files_match'] == False
        assert 'Packets: 10 vs 20' in comparison['differences']
        assert 'Messages' not in str(comparison['differences'])
        
    def test_multiple_differences(self):
        """Test comparing reports with multiple differences."""
        report1 = {
            'file_stats': {
                'size_bytes': 1024,
                'total_packets': 10,
                'total_messages': 100
            }
        }
        
        report2 = {
            'file_stats': {
                'size_bytes': 2048,
                'total_packets': 20,
                'total_messages': 200
            }
        }
        
        comparison = compare_reports(report1, report2)
        
        assert comparison['files_match'] == False
        assert len(comparison['differences']) == 3
