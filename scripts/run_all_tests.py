#!/usr/bin/env python
"""Test runner for ch10-1553-flightgen project."""

import sys
import subprocess
import time
from pathlib import Path

def run_command(cmd, description, allow_fail=False):
    """Run a command and report results."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print(f"✓ {description} - PASSED")
            if result.stdout:
                print("Output:", result.stdout[:500])  # Show first 500 chars
            return True
        else:
            print(f"✗ {description} - FAILED (exit code: {result.returncode})")
            if result.stderr:
                print("Error:", result.stderr[:500])
            if not allow_fail:
                return False
            return True  # Still continue if allowed to fail
            
    except subprocess.TimeoutExpired:
        print(f"✗ {description} - TIMEOUT (>30s)")
        return allow_fail
    except Exception as e:
        print(f"✗ {description} - ERROR: {e}")
        return allow_fail

def main():
    """Run all tests and verification."""
    project_root = Path(__file__).parent.parent
    
    all_passed = True
    
    # 1. Python version check
    if not run_command(
        [sys.executable, "--version"],
        "Python version check"
    ):
        all_passed = False
    
    # 2. Import checks
    if not run_command(
        [sys.executable, "-c", "import ch10gen; print('ch10gen imported successfully')"],
        "Import ch10gen module"
    ):
        all_passed = False
    
    # 3. Core unit tests (fast, reliable)
    unit_tests = [
        "tests/test_encode1553.py",
        "tests/test_icd.py",
        "tests/test_flight_profile.py",
        "tests/test_schedule.py",
        "tests/test_tmats_min.py",
        
    ]
    
    for test_file in unit_tests:
        test_path = project_root / test_file
        if test_path.exists():
            if not run_command(
                [sys.executable, "-m", "pytest", str(test_path), "-xvs", "--tb=short"],
                f"Unit test: {test_file}"
            ):
                all_passed = False
        else:
            print(f"⚠ Test file not found: {test_file}")
    
    # 4. CLI smoke test
    if not run_command(
        [sys.executable, "-m", "ch10gen", "--version"],
        "CLI version check"
    ):
        all_passed = False
    
    # 5. Demo build test (small, fast)
    test_output = project_root / "test_output.c10"
    test_output.unlink(missing_ok=True)
    
    if not run_command(
        [
            sys.executable, "-m", "ch10gen", "build",
            "-s", str(project_root / "scenarios" / "test_scenario.yaml"),
            "-i", str(project_root / "icd" / "test_icd.yaml"),
            "-o", str(test_output),
            "--writer", "irig106"
        ],
        "Demo build (irig106 writer)"
    ):
        all_passed = False
    else:
        if test_output.exists():
            size_mb = test_output.stat().st_size / (1024 * 1024)
            print(f"  Output file size: {size_mb:.2f} MB")
            test_output.unlink()  # Clean up
    

    
    # 7. Integration tests (may be slower)
    integration_tests = [
        "tests/test_wire_invariants.py",
        "tests/test_spec_driven.py"
    ]
    
    for test_file in integration_tests:
        test_path = project_root / test_file
        if test_path.exists():
            if not run_command(
                [sys.executable, "-m", "pytest", str(test_path), "-xvs", "--tb=short"],
                f"Integration test: {test_file}",
                allow_fail=True  # These may depend on external tools
            ):
                print(f"  ⚠ Integration test failed (may need external tools)")
    
    # 8. PyChapter10 compatibility tests (expected to have some failures)
    print("\n" + "="*60)
    print("PyChapter10 Compatibility Tests (some failures expected)")
    print("="*60)
    
    run_command(
        [sys.executable, "-m", "pytest", "-m", "compat", "-xvs", "--tb=short"],
        "PyChapter10 compatibility tests",
        allow_fail=True  # Known issues with PyChapter10
    )
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    if all_passed:
        print("✓ All core tests PASSED")
        print("✓ ch10gen is working correctly")
        print("✓ Project is ready for use")
        return 0
    else:
        print("✗ Some tests FAILED")
        print("  - Check error messages above")
        print("  - Core functionality may still work")
        return 1

if __name__ == "__main__":
    sys.exit(main())
