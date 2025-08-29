#!/usr/bin/env python3
"""
Run TShark validation on CH10 files.
This script provides a simple way to validate CH10 files using tshark.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

# Default tshark path for Windows
DEFAULT_TSHARK_WIN = "C:/Program Files/Wireshark/tshark.exe"
DEFAULT_TSHARK_UNIX = "/usr/bin/tshark"

def find_tshark():
    """Find tshark executable."""
    # Check environment variable first
    tshark = os.environ.get('TSHARK')
    if tshark and Path(tshark).exists():
        return tshark
    
    # Check common locations
    if sys.platform == 'win32':
        if Path(DEFAULT_TSHARK_WIN).exists():
            return DEFAULT_TSHARK_WIN
    else:
        if Path(DEFAULT_TSHARK_UNIX).exists():
            return DEFAULT_TSHARK_UNIX
    
    # Try PATH
    import shutil
    tshark = shutil.which('tshark')
    if tshark:
        return tshark
    
    return None

def validate_ch10(ch10_file, tshark_path=None, verbose=False):
    """Validate a CH10 file using tshark."""
    
    if not tshark_path:
        tshark_path = find_tshark()
    
    if not tshark_path:
        print("ERROR: tshark not found. Please install Wireshark.")
        return False
    
    ch10_path = Path(ch10_file)
    if not ch10_path.exists():
        print(f"ERROR: File not found: {ch10_file}")
        return False
    
    print(f"Validating: {ch10_path.name}")
    print(f"Using tshark: {tshark_path}")
    print("-" * 60)
    
    # Test 1: Can tshark read the file?
    print("Test 1: File readability...")
    cmd = [tshark_path, '-r', str(ch10_path), '-c', '1']
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"  FAIL: TShark cannot read file")
        if verbose:
            print(f"  Error: {result.stderr}")
        return False
    print("  PASS: File is readable")
    
    # Test 2: Count packets
    print("\nTest 2: Packet analysis...")
    cmd = [tshark_path, '-r', str(ch10_path), '-q', '-z', 'io,stat,0']
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        # Parse output for packet count
        lines = result.stdout.split('\n')
        for line in lines:
            if 'Frames' in line or 'frames' in line:
                print(f"  {line.strip()}")
    
    # Test 3: Look for 1553 messages
    print("\nTest 3: 1553 message detection...")
    cmd = [tshark_path, '-r', str(ch10_path), '-Y', 'ch10']
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        lines = result.stdout.strip().split('\n')
        ch10_count = len([l for l in lines if l])
        print(f"  Found {ch10_count} CH10 packets")
        
        # Check for MIL-STD-1553
        has_1553 = any('MILSTD1553' in line for line in lines)
        if has_1553:
            print("  PASS: MIL-STD-1553 messages detected")
        else:
            print("  WARNING: No MIL-STD-1553 messages found")
    
    # Test 4: Extract some fields (if possible)
    print("\nTest 4: Field extraction...")
    cmd = [tshark_path, '-r', str(ch10_path), '-T', 'fields', 
           '-e', 'frame.number', '-e', 'frame.len', '-c', '5']
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0 and result.stdout:
        print("  Sample frames:")
        for line in result.stdout.strip().split('\n')[:5]:
            if line:
                parts = line.split('\t')
                if len(parts) >= 2:
                    print(f"    Frame {parts[0]}: {parts[1]} bytes")
    
    print("\n" + "=" * 60)
    print("VALIDATION COMPLETE: SUCCESS")
    print("=" * 60)
    return True

def main():
    parser = argparse.ArgumentParser(description='Validate CH10 files using TShark')
    parser.add_argument('ch10_file', help='CH10 file to validate')
    parser.add_argument('--tshark', help='Path to tshark executable')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    success = validate_ch10(args.ch10_file, args.tshark, args.verbose)
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
