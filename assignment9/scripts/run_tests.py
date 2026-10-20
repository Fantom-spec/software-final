#!/usr/bin/env python3
"""
Test runner script for HMS Assessment 9.
Runs the complete test suite and generates reports.
"""

import sys
import os
import subprocess
from pathlib import Path


def run_tests():
    """Run pytest with coverage."""
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    # Add assignment9 to Python path
    sys.path.insert(0, str(project_root / 'assignment9'))
    
    # Run tests with coverage
    cmd = [
        sys.executable, '-m', 'pytest',
        'assignment9/tests/',
        '-v',
        '--tb=short',
        '--cov=assignment9/hms_app',
        '--cov-report=term-missing',
        '--cov-report=html:assignment9/results/coverage_html',
        '--junitxml=assignment9/results/junit.xml',
    ]
    
    print("=" * 60)
    print("Running HMS Assessment 9 Test Suite")
    print("=" * 60)
    
    result = subprocess.run(cmd, capture_output=False)
    
    return result.returncode


def run_specific_test(test_file):
    """Run a specific test file."""
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    sys.path.insert(0, str(project_root / 'assignment9'))
    
    cmd = [
        sys.executable, '-m', 'pytest',
        f'assignment9/tests/{test_file}',
        '-v',
        '--tb=short',
    ]
    
    result = subprocess.run(cmd)
    return result.returncode


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='HMS Assessment 9 Test Runner')
    parser.add_argument('--test', help='Run specific test file (e.g., test_room_allocation.py)')
    parser.add_argument('--no-cov', action='store_true', help='Run without coverage')
    
    args = parser.parse_args()
    
    if args.test:
        exit_code = run_specific_test(args.test)
    else:
        exit_code = run_tests()
    
    sys.exit(exit_code)