#!/usr/bin/env python
"""Simple test runner using the virtual environment Python.

Usage:
    python test_runner.py              # Run all tests
    python test_runner.py parser       # Run specific test file
    python test_runner.py -k "test_and" # Run tests matching pattern
"""

import sys
import subprocess
from pathlib import Path

def main():
    """Run tests using venv python."""
    # Use venv python
    venv_python = Path(__file__).parent / ".venv" / "Scripts" / "python.exe"
    
    # Build command
    cmd = [str(venv_python), "-m", "pytest", "tests", "-v"]
    
    # Add user args
    if len(sys.argv) > 1:
        # If first arg doesn't start with -, treat as test file
        if not sys.argv[1].startswith("-"):
            test_file = sys.argv[1]
            if not test_file.endswith("_test.py"):
                test_file = f"{test_file}_test.py"
            cmd[3] = f"tests/{test_file}"
            cmd.extend(sys.argv[2:])
        else:
            cmd.extend(sys.argv[1:])
    
    print(f"Running: {' '.join(cmd)}\n")
    result = subprocess.run(cmd)
    return result.returncode

if __name__ == "__main__":
    sys.exit(main())
