#!/usr/bin/env python3
"""
Complete project validation script.
Ensures code quality, tests pass, and documentation is current.
"""

import subprocess
import sys
from pathlib import Path
import json
import time

def run_command(cmd, description):
    """Run a command and report results."""
    print(f"\n{description}...")
    result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
    if result.returncode == 0:
        print(f"  OK Success")
        return True
    else:
        print(f"  FAIL Failed")
        if result.stderr:
            print(f"    Error: {result.stderr[:200]}")
        return False

def validate_code_quality():
    """Validate code quality and style."""
    print("\n" + "="*60)
    print("CODE QUALITY VALIDATION")
    print("="*60)
    
    checks = []
    
    # Check for Python syntax errors
    print("\n1. Python Syntax Check:")
    for py_file in Path(".").rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
        cmd = f'python -m py_compile "{py_file}"'
        result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
        if result.returncode != 0:
            print(f"  FAIL Syntax error in {py_file}")
            checks.append(False)
        else:
            checks.append(True)
    
    if all(checks):
        print(f"  OK All Python files have valid syntax")
    
    # Check imports
    print("\n2. Import Check:")
    cmd = 'python -c "import ch10gen; print(ch10gen.__version__)"'
    if run_command(cmd, "  Checking ch10gen imports"):
        checks.append(True)
    else:
        checks.append(False)
    
    return all(checks) if checks else False

def validate_tests():
    """Run test suite."""
    print("\n" + "="*60)
    print("TEST SUITE VALIDATION")
    print("="*60)
    
    # Run core tests
    cmd = "python -m pytest tests/test_bitfield_packing.py tests/test_icd.py -q"
    core_tests = run_command(cmd, "Core tests")
    
    # Run CLI tests
    cmd = "python -m pytest tests/test_cli.py -q"
    cli_tests = run_command(cmd, "CLI tests")
    
    return core_tests and cli_tests

def validate_functionality():
    """Validate core functionality."""
    print("\n" + "="*60)
    print("FUNCTIONALITY VALIDATION")
    print("="*60)
    
    checks = []
    
    # Test CH10 generation
    print("\n1. CH10 Generation:")
    cmd = 'python -m ch10gen build --scenario scenarios/test_scenario.yaml --icd icd/nav_icd.yaml --out test.ch10 --duration 1'
    if run_command(cmd, "  Generating CH10 file"):
        # Check file was created
        if Path("test.ch10").exists():
            size = Path("test.ch10").stat().st_size
            print(f"    Generated file: {size} bytes")
            Path("test.ch10").unlink()
            checks.append(True)
        else:
            print("    File not created")
            checks.append(False)
    else:
        checks.append(False)
    
    # Test ICD validation
    print("\n2. ICD Validation:")
    cmd = 'python -m ch10gen check-icd icd/nav_icd.yaml'
    checks.append(run_command(cmd, "  Validating ICD"))
    
    # Test bitfield example
    print("\n3. Bitfield Example:")
    cmd = 'python -m ch10gen check-icd icd/bitfield_example.yaml'
    checks.append(run_command(cmd, "  Validating bitfield ICD"))
    
    return all(checks)

def validate_documentation():
    """Check documentation is present and valid."""
    print("\n" + "="*60)
    print("DOCUMENTATION VALIDATION")
    print("="*60)
    
    required_docs = [
        "README.md",
        "docs/ARCHITECTURE.md",
        "docs/CONFIGURATION.md",
        "docs/TESTING.md",
        "docs/API.md"
    ]
    
    checks = []
    for doc in required_docs:
        if Path(doc).exists():
            size = Path(doc).stat().st_size
            if size > 100:  # Reasonable minimum size
                print(f"  OK {doc} ({size:,} bytes)")
                checks.append(True)
            else:
                print(f"  FAIL {doc} (too small: {size} bytes)")
                checks.append(False)
        else:
            print(f"  FAIL {doc} (missing)")
            checks.append(False)
    
    return all(checks)

def validate_project_structure():
    """Validate project structure and organization."""
    print("\n" + "="*60)
    print("PROJECT STRUCTURE VALIDATION")
    print("="*60)
    
    required_dirs = [
        "ch10gen",
        "ch10gen/core",
        "ch10gen/utils",
        "tests",
        "docs",
        "icd",
        "scenarios",
        "examples"
    ]
    
    required_files = [
        "ch10gen/__init__.py",
        "ch10gen/__main__.py",
        "ch10gen/cli.py",
        "ch10gen/icd.py",
        "ch10gen/scenario.py",
        "ch10gen/schedule.py",
        "setup.py",
        "requirements.txt",
        "pytest.ini"
    ]
    
    print("\nDirectories:")
    dir_checks = []
    for dir_path in required_dirs:
        if Path(dir_path).is_dir():
            print(f"  OK {dir_path}/")
            dir_checks.append(True)
        else:
            print(f"  FAIL {dir_path}/ (missing)")
            dir_checks.append(False)
    
    print("\nKey Files:")
    file_checks = []
    for file_path in required_files:
        if Path(file_path).is_file():
            print(f"  OK {file_path}")
            file_checks.append(True)
        else:
            print(f"  FAIL {file_path} (missing)")
            file_checks.append(False)
    
    return all(dir_checks + file_checks)

def main():
    """Run complete project validation."""
    print("="*60)
    print("CH10 GENERATOR - PROJECT VALIDATION")
    print("="*60)
    print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {}
    
    # Run all validations
    results['structure'] = validate_project_structure()
    results['quality'] = validate_code_quality()
    results['tests'] = validate_tests()
    results['functionality'] = validate_functionality()
    results['documentation'] = validate_documentation()
    
    # Summary
    print("\n" + "="*60)
    print("VALIDATION SUMMARY")
    print("="*60)
    
    for category, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {category.capitalize()}: {status}")
    
    all_passed = all(results.values())
    
    print("\n" + "="*60)
    if all_passed:
        print("PASS: PROJECT VALIDATION SUCCESSFUL")
        print("The CH10 Generator project is ready for use!")
    else:
        print("WARN: PROJECT VALIDATION INCOMPLETE")
        print("Some validations failed. Please review the output above.")
    print("="*60)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
