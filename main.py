"""Main entry point for the Data Converter CLI.

This module serves as the entry point for the dataconv command-line tool.

Usage:
    $ python main.py "from input.json to output.yaml"
    $ python main.py "from data.json[users.*] to output.toml where age > 25"
"""

import sys

from src.cli import app


def main() -> None:
    """Run the CLI application."""
    app()


if __name__ == "__main__":
    main()
