#!/usr/bin/env python3
"""
Test suite runner for CH10 Generator.
Provides detailed reporting and validation of all components.
"""

import subprocess
import sys
from pathlib import Path
import json
import time
from typing import Dict, List, Tuple

class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def colored(text: str, color: str) -> str:
    """Apply color to text if terminal supports it."""
    if sys.stdout.isatty():
        return f"{color}{text}{Colors.RESET}"
    return text

class TestCategory:
    """Test category with results tracking."""
    def __init__(self, name: str, files: List[str]):
        self.name = name
        self.files = files
        self.passed = []
        self.failed = []
        self.errors = []
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0

class TestRunner:
    """Runs all tests and provides detailed reporting."""
    
    def __init__(self):
        self.categories = {
            'Core Functionality': [
                'test_bitfield_packing.py',
                'test_icd.py', 
                'test_encode1553.py',
                'test_1553_encode.py'
            ],
            'Scenario & Flight': [
                'test_scenario.py',
                'test_flight_profile.py',
                'test_profile.py',
                'test_flight_profile_comprehensive.py',
                'test_flight_state.py'
            ],
            'Scheduling': [
                'test_schedule.py',
                'test_scheduler.py',
                'test_schedule_comprehensive.py',
                'test_schedule_simple.py'
            ],
            'Error Handling': [
                'test_errors_simple.py',
                'test_error_injection_comprehensive.py'
            ],
            'TMATS': [
                'test_tmats.py',
                'test_tmats_min.py'
            ],
            'Export & PCAP': [
                'test_pcap_export.py',
                'test_pcap_comprehensive.py'
            ],
            'Utilities': [
                'test_util_time.py',
                'test_channel_config.py',
                'test_config.py',
                'test_timebase.py'
            ],
            'Validation': [
                'test_tshark_validation.py',
                'test_tshark_comprehensive.py',
                'test_comprehensive_bitfields.py',
                'test_large_ch10_validation.py',
                'test_validation_comprehensive.py'
            ],
            'Integration': [
                'test_ch10_roundtrip.py',
                'test_cli.py',
                'test_integration_spec.py',
                'test_spec_driven.py',
                'test_wire_format.py',
                'test_wire_invariants.py'
            ],
            'Writer & Backend': [
                'test_writer_backend.py',
                'test_dual_reader.py',
                'test_independent_reader.py',
                'test_packet_accumulator.py'
            ],
            'Performance': [
                'test_performance.py',
                'test_timeout.py'
            ],
            'Other': [
                'test_icd_edge_cases.py',
                'test_minimal_1553_repro.py',
                'test_ms1553_messages.py',
                'test_pychapter10_behavior.py',
                'test_report.py'
            ]
        }
        
        self.test_categories = {
            name: TestCategory(name, files) 
            for name, files in self.categories.items()
        }
        
        self.total_files = 0
        self.passed_files = 0
        self.failed_files = 0
        self.error_files = 0
        
    def run_test_file(self, test_file: Path) -> Tuple[str, int, int]:
        """Run a single test file and return status."""
        cmd = [sys.executable, "-m", "pytest", str(test_file), 
               "-v", "--tb=short", "-q", "--no-header"]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            # Parse results
            output = result.stdout + result.stderr
            
            # Look for test counts
            import re
            passed_match = re.search(r'(\d+) passed', output)
            failed_match = re.search(r'(\d+) failed', output)
            error_match = re.search(r'(\d+) error', output)
            
            passed = int(passed_match.group(1)) if passed_match else 0
            failed = int(failed_match.group(1)) if failed_match else 0
            errors = int(error_match.group(1)) if error_match else 0
            
            if errors > 0:
                return 'ERROR', 0, errors
            elif failed > 0:
                return 'FAIL', passed, failed
            elif passed > 0:
                return 'PASS', passed, 0
            else:
                return 'SKIP', 0, 0
                
        except subprocess.TimeoutExpired:
            return 'TIMEOUT', 0, 1
        except Exception:
            return 'ERROR', 0, 1
    
    def run_category(self, category: TestCategory):
        """Run all tests in a category."""
        test_dir = Path("tests")
        
        for file_name in category.files:
            test_file = test_dir / file_name
            if not test_file.exists():
                continue
            
            self.total_files += 1
            status, passed, failed = self.run_test_file(test_file)
            
            category.total_tests += passed + failed
            category.passed_tests += passed
            category.failed_tests += failed
            
            if status == 'PASS':
                category.passed.append((file_name, passed))
                self.passed_files += 1
                print(f"  {colored('OK', Colors.GREEN)} {file_name}: {passed} tests")
            elif status == 'FAIL':
                category.failed.append((file_name, failed))
                self.failed_files += 1
                print(f"  {colored('FAIL', Colors.RED)} {file_name}: {failed} failures")
            elif status == 'ERROR':
                category.errors.append(file_name)
                self.error_files += 1
                print(f"  {colored('WARN', Colors.YELLOW)} {file_name}: Import/syntax error")
            elif status == 'TIMEOUT':
                category.errors.append(file_name)
                self.error_files += 1
                print(f"  {colored('⏱', Colors.YELLOW)} {file_name}: Timeout")
            else:
                print(f"  {colored('-', Colors.BLUE)} {file_name}: No tests")
    
    def run_all_tests(self):
        """Run all test categories."""
        print(colored("="*70, Colors.BOLD))
        print(colored("CH10 GENERATOR - TEST SUITE", Colors.BOLD))
        print(colored("="*70, Colors.BOLD))
        
        start_time = time.time()
        
        for name, category in self.test_categories.items():
            print(f"\n{colored(name, Colors.BOLD)}:")
            print("-" * 50)
            self.run_category(category)
        
        elapsed = time.time() - start_time
        self.print_summary(elapsed)
    
    def print_summary(self, elapsed_time: float):
        """Print test summary."""
        print(f"\n{colored('='*70, Colors.BOLD)}")
        print(colored("TEST SUMMARY", Colors.BOLD))
        print(colored("="*70, Colors.BOLD))
        
        # Category breakdown
        print(f"\n{colored('Category Results:', Colors.BOLD)}")
        for name, category in self.test_categories.items():
            if category.total_tests > 0:
                pass_rate = (category.passed_tests / category.total_tests) * 100
                status_color = Colors.GREEN if pass_rate == 100 else Colors.YELLOW if pass_rate >= 80 else Colors.RED
                print(f"  {name}: {colored(f'{pass_rate:.1f}%', status_color)} "
                      f"({category.passed_tests}/{category.total_tests} tests)")
        
        # Overall statistics
        total_tests = sum(c.total_tests for c in self.test_categories.values())
        passed_tests = sum(c.passed_tests for c in self.test_categories.values())
        failed_tests = sum(c.failed_tests for c in self.test_categories.values())
        
        print(f"\n{colored('Overall Statistics:', Colors.BOLD)}")
        print(f"  Files: {self.passed_files}/{self.total_files} passed")
        print(f"  Tests: {passed_tests}/{total_tests} passed")
        
        if failed_tests > 0:
            print(f"  Failed: {colored(str(failed_tests), Colors.RED)} tests")
        if self.error_files > 0:
            print(f"  Errors: {colored(str(self.error_files), Colors.YELLOW)} files")
        
        print(f"  Time: {elapsed_time:.2f} seconds")
        
        # Success/failure message
        if failed_tests == 0 and self.error_files == 0:
            print(f"\n{colored('PASS ALL TESTS PASSED!', Colors.GREEN + Colors.BOLD)}")
            return True
        else:
            print(f"\n{colored('WARN SOME TESTS FAILED', Colors.YELLOW + Colors.BOLD)}")
            
            # List failures
            if failed_tests > 0:
                print(f"\n{colored('Failed Tests:', Colors.RED)}")
                for category in self.test_categories.values():
                    for file_name, count in category.failed:
                        print(f"  - {file_name}: {count} failures")
            
            if self.error_files > 0:
                print(f"\n{colored('Files with Errors:', Colors.YELLOW)}")
                for category in self.test_categories.values():
                    for file_name in category.errors:
                        print(f"  - {file_name}")
            
            return False
    
    def run_functional_tests(self):
        """Run functional validation tests."""
        print(f"\n{colored('='*70, Colors.BOLD)}")
        print(colored("FUNCTIONAL VALIDATION", Colors.BOLD))
        print(colored("="*70, Colors.BOLD))
        
        tests_passed = 0
        tests_failed = 0
        
        # Test 1: CH10 file generation
        print("\n1. CH10 File Generation:")
        cmd = [sys.executable, "-m", "ch10gen", "build",
               "--scenario", "scenarios/test_scenario.yaml",
               "--icd", "icd/nav_icd.yaml",
               "--out", "test_output.ch10",
               "--duration", "1"]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"  {colored('OK', Colors.GREEN)} Basic CH10 generation")
            Path("test_output.ch10").unlink(missing_ok=True)
            tests_passed += 1
        else:
            print(f"  {colored('FAIL', Colors.RED)} Basic CH10 generation failed")
            tests_failed += 1
        
        # Test 2: ICD validation
        print("\n2. ICD Validation:")
        cmd = [sys.executable, "-m", "ch10gen", "validate",
               "--icd", "icd/nav_icd.yaml"]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"  {colored('OK', Colors.GREEN)} ICD validation")
            tests_passed += 1
        else:
            print(f"  {colored('FAIL', Colors.RED)} ICD validation failed")
            tests_failed += 1
        
        # Test 3: CLI help
        print("\n3. CLI Commands:")
        for cmd_args in [["--help"], ["build", "--help"], ["validate", "--help"]]:
            cmd = [sys.executable, "-m", "ch10gen"] + cmd_args
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"  {colored('OK', Colors.GREEN)} ch10gen {' '.join(cmd_args)}")
                tests_passed += 1
            else:
                print(f"  {colored('FAIL', Colors.RED)} ch10gen {' '.join(cmd_args)}")
                tests_failed += 1
        
        print(f"\nFunctional Tests: {tests_passed} passed, {tests_failed} failed")
        return tests_failed == 0

def main():
    """Main entry point."""
    runner = TestRunner()
    
    # Run unit tests
    test_success = runner.run_all_tests()
    
    # Run functional tests
    functional_success = runner.run_functional_tests()
    
    # Final status
    print(f"\n{colored('='*70, Colors.BOLD)}")
    if test_success and functional_success:
        print(colored("PASS ALL VALIDATIONS PASSED", Colors.GREEN + Colors.BOLD))
        return 0
    else:
        print(colored("WARN VALIDATION INCOMPLETE", Colors.YELLOW + Colors.BOLD))
        return 1

if __name__ == "__main__":
    sys.exit(main())
