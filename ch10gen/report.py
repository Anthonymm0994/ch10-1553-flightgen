"""Generate JSON reports for CH10 files."""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
from collections import Counter


def generate_report(stats: Dict[str, Any], output_path: Optional[Path] = None) -> Dict[str, Any]:
    """Generate a JSON report from CH10 file statistics.
    
    Args:
        stats: Statistics from write_ch10_file
        output_path: Optional path to save JSON report
        
    Returns:
        Report dictionary
    """
    report = {
        'timestamp': datetime.utcnow().isoformat(),
        'file_stats': {
            'size_bytes': stats.get('file_size_bytes', 0),
            'total_packets': stats.get('total_packets', 0),
            'total_messages': stats.get('total_messages', 0),
            'duration_seconds': stats.get('duration_s', 0),
        },
        'packet_types': stats.get('packet_types', {}),
        'message_stats': stats.get('message_stats', {}),
        'backend': stats.get('backend', 'unknown'),
        'spec_compliant': stats.get('spec_compliant', False)
    }
    
    # Add timing info if available
    if 'first_time' in stats:
        report['timing'] = {
            'first_time': stats['first_time'],
            'last_time': stats.get('last_time', stats['first_time'])
        }
    
    # Add RT/SA distribution if available
    if 'rt_sa_distribution' in stats:
        report['rt_sa_distribution'] = stats['rt_sa_distribution']
    
    # Add error stats if any
    if 'error_stats' in stats:
        report['error_stats'] = stats['error_stats']
    
    # Save to file if path provided
    if output_path:
        output_path = Path(output_path)
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
    
    return report


def generate_summary_report(filepath: Path, stats: Dict[str, Any]) -> Path:
    """Generate a summary report JSON next to the CH10 file.
    
    Args:
        filepath: CH10 file path
        stats: Statistics from write_ch10_file
        
    Returns:
        Path to the generated report
    """
    # Create report path (same name, .json extension)
    report_path = filepath.with_suffix('.json')
    
    # Generate and save report
    report = generate_report(stats, report_path)
    
    # Add file-specific info
    report['ch10_file'] = {
        'path': str(filepath),
        'name': filepath.name,
        'created': datetime.fromtimestamp(filepath.stat().st_ctime).isoformat() if filepath.exists() else None
    }
    
    # Save updated report
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    return report_path


def load_report(report_path: Path) -> Dict[str, Any]:
    """Load a JSON report file.
    
    Args:
        report_path: Path to JSON report
        
    Returns:
        Report dictionary
    """
    with open(report_path, 'r') as f:
        return json.load(f)


def compare_reports(report1: Dict[str, Any], report2: Dict[str, Any]) -> Dict[str, Any]:
    """Compare two reports and return differences.
    
    Args:
        report1: First report
        report2: Second report
        
    Returns:
        Comparison results
    """
    comparison = {
        'files_match': False,
        'differences': []
    }
    
    # Compare file stats
    stats1 = report1.get('file_stats', {})
    stats2 = report2.get('file_stats', {})
    
    if stats1.get('size_bytes') != stats2.get('size_bytes'):
        comparison['differences'].append(f"Size: {stats1.get('size_bytes')} vs {stats2.get('size_bytes')}")
    
    if stats1.get('total_packets') != stats2.get('total_packets'):
        comparison['differences'].append(f"Packets: {stats1.get('total_packets')} vs {stats2.get('total_packets')}")
    
    if stats1.get('total_messages') != stats2.get('total_messages'):
        comparison['differences'].append(f"Messages: {stats1.get('total_messages')} vs {stats2.get('total_messages')}")
    
    # Check if files match
    if not comparison['differences']:
        comparison['files_match'] = True
    
    return comparison
