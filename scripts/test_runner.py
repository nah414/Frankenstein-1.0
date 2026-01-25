#!/usr/bin/env python3
"""
FRANKENSTEIN 1.0 - Comprehensive Test Runner
Automated testing with detailed reporting
"""

import sys
import subprocess
import time
from pathlib import Path
from datetime import datetime


class Colors:
    """ANSI color codes for terminal output"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


def print_header(text):
    """Print a formatted header"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text.center(60)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.END}\n")


def print_section(text):
    """Print a section header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}[{text}]{Colors.END}")


def print_success(text):
    """Print success message"""
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")


def print_error(text):
    """Print error message"""
    print(f"{Colors.RED}✗ {text}{Colors.END}")


def print_warning(text):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")


def check_dependencies():
    """Check if required dependencies are installed"""
    print_section("Checking Dependencies")

    dependencies = {
        'pytest': 'pytest',
        'pytest-cov': 'pytest_cov',
        'psutil': 'psutil',
        'yaml': 'pyyaml'
    }

    missing = []
    for name, module in dependencies.items():
        try:
            __import__(module)
            print_success(f"{name} installed")
        except ImportError:
            print_error(f"{name} not found")
            missing.append(name)

    if missing:
        print_warning(f"\nMissing dependencies: {', '.join(missing)}")
        print(f"Run: pip install {' '.join(missing)}")
        return False

    return True


def run_tests(mode="standard"):
    """
    Run tests based on mode

    Modes:
        - quick: Fast tests without coverage
        - standard: Normal tests with basic coverage
        - coverage: Full coverage report
        - verbose: Verbose output
        - unit: Unit tests only
    """
    print_section(f"Running Tests ({mode} mode)")

    # Base pytest command
    cmd = [sys.executable, "-m", "pytest", "tests/"]

    # Add mode-specific flags
    if mode == "quick":
        cmd.extend(["-v"])
    elif mode == "coverage":
        cmd.extend([
            "-v",
            "--cov=core",
            "--cov=quantum",
            "--cov=classical",
            "--cov=synthesis",
            "--cov=agents",
            "--cov=security",
            "--cov-report=html",
            "--cov-report=term"
        ])
    elif mode == "verbose":
        cmd.extend(["-vv", "-s"])
    elif mode == "unit":
        cmd = [sys.executable, "-m", "pytest", "tests/unit/", "-v"]
    else:  # standard
        cmd.extend(["-v", "--cov=core", "--cov-report=term"])

    # Run tests
    start_time = time.time()
    result = subprocess.run(cmd, capture_output=False)
    duration = time.time() - start_time

    print(f"\n{Colors.BOLD}Test Duration: {duration:.2f}s{Colors.END}")

    return result.returncode == 0


def generate_report(success, mode):
    """Generate test summary report"""
    print_header("Test Summary")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"Timestamp: {timestamp}")
    print(f"Test Mode: {mode}")

    if success:
        print_success("ALL TESTS PASSED")
    else:
        print_error("SOME TESTS FAILED")

    print("\nAvailable Test Modes:")
    print("  python test_runner.py           - Standard tests with basic coverage")
    print("  python test_runner.py quick     - Quick tests, no coverage")
    print("  python test_runner.py coverage  - Full coverage report (HTML + terminal)")
    print("  python test_runner.py verbose   - Verbose output with print statements")
    print("  python test_runner.py unit      - Unit tests only")

    if mode == "coverage":
        coverage_path = Path("htmlcov") / "index.html"
        if coverage_path.exists():
            print(f"\n{Colors.CYAN}Coverage report: {coverage_path}{Colors.END}")


def main():
    """Main test runner entry point"""
    print_header("FRANKENSTEIN 1.0 - Test Runner")

    # Get test mode from command line
    mode = sys.argv[1] if len(sys.argv) > 1 else "standard"

    if mode not in ["quick", "standard", "coverage", "verbose", "unit"]:
        print_error(f"Invalid mode: {mode}")
        print("Valid modes: quick, standard, coverage, verbose, unit")
        sys.exit(1)

    # Check dependencies
    if not check_dependencies():
        print_error("\nPlease install missing dependencies first")
        print("Run: python -m pip install -r requirements.txt")
        sys.exit(1)

    # Run tests
    success = run_tests(mode)

    # Generate report
    generate_report(success, mode)

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
