"""Main entry point for the dataconv CLI.

This module serves as the entry point for the dataconv interactive command-line tool.

Usage:
    $ python main.py
    
    dataconv v2.0
    Type 'help' for commands, 'exit' to quit.

    dataconv> load input.json
    dataconv> convert to output.yaml where age > 25
"""

from src.cli import InteractiveCLI
import sys

def main() -> None:
    """Run the interactive CLI application."""
    cli = InteractiveCLI()
    try:
        cli.run()
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
