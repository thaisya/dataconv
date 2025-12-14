"""Interactive command-line interface for the Data Converter.

This module provides a MySQL-style interactive REPL for data conversion operations.
Users can load files, convert between formats, filter data, and more in a continuous session.

Example:
    $ python main.py
    DataConverter v2.0
    Type 'help' for commands, 'exit' to quit.

    dataconv> load test/test.json
    [+] Loaded: test.json (3 records)

    dataconv> convert to output.yaml
    [+] Converted and saved to output.yaml
"""

import logging
import re
import sys
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.table import Table

from src import __version__
from src.io import DataConverterIOError, detect_format, smart_load, smart_save
from src.parser import ParseError, QueryParser
from src.processor import ProcessorError, apply_path, apply_conditions
from src.validation import ValidationError, format_validation_report, validate

# Initialize Rich console
console = Console()


def setup_logging(verbose: bool = False) -> None:
    """Configure logging with Rich handler.

    Args:
        verbose: If True, set log level to DEBUG, otherwise WARNING
    """
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )


class InteractiveCLI:
    """Interactive REPL for data conversion operations.

    This class provides a MySQL-style command-line interface where users can
    load files, convert between formats, apply filters, and more.

    Attributes:
        current_file: Path to currently loaded file
        current_data: The loaded data
        current_format: Detected format of current file
        verbose: Whether verbose logging is enabled
        running: Whether the REPL loop is active
    """

    def __init__(self, verbose: bool = False) -> None:
        """Initialize the interactive CLI.

        Args:
            verbose: Enable verbose logging
        """
        self.current_file: Path | None = None
        self.current_data: Any = None
        self.current_format: str | None = None
        self.verbose = verbose
        self.running = True
        self.logger = logging.getLogger(__name__)

        setup_logging(verbose)

    def run(self) -> None:
        """Start the interactive REPL loop."""
        self._print_welcome()

        while self.running:
            try:
                # Get user input
                user_input = input("dataconv> ").strip()

                if not user_input:
                    continue

                # Parse and execute command
                self._execute_command(user_input)

            except KeyboardInterrupt:
                console.print("\n[yellow]Use 'exit' to quit.[/yellow]")
            except EOFError:
                self._cmd_exit("")

    def _print_welcome(self) -> None:
        """Print welcome message."""
        ascii_art = f"""
╭────────────────────────────────── Interactive Data Converter ──────────────────────────────────╮
│                                                                                                │
│   ██████╗  █████╗ ████████╗ █████╗  ██████╗ ██████╗ ███╗   ██╗██╗   ██╗                        │
│   ██╔══██╗██╔══██╗╚══██╔══╝██╔══██╗██╔════╝██╔═══██╗████╗  ██║██║   ██║                        │
│   ██║  ██║███████║   ██║   ███████║██║     ██║   ██║██╔██╗ ██║██║   ██║                        │
│   ██║  ██║██╔══██║   ██║   ██╔══██║██║     ██║   ██║██║╚██╗██║╚██╗ ██╔╝                        │
│   ██████╔╝██║  ██║   ██║   ██║  ██║╚██████╗╚██████╔╝██║ ╚████║ ╚████╔╝                         │
│   ╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚═╝  ╚═══╝  ╚═══╝                          │
│                                                                                                │
│   Version: {__version__}                                                                               │
│   Type 'help' for commands, 'exit' to quit.                                                    │
│                                                                                                │
╰────────────────────────────────────────────────────────────────────────────────────────────────╯
        """
        console.print(f"[cyan]{ascii_art}[/cyan]")

    def _execute_command(self, user_input: str) -> None:
        """Parse and execute a user command or query.

        Args:
            user_input: Raw user input string
        """
        # Check if input is a query (starts with 'from')
        if user_input.strip().lower().startswith('from'):
            self._execute_query(user_input)
            return

        # Otherwise treat as helper command
        parts = user_input.split(maxsplit=1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        # Simplified command dispatch
        commands = {
            "help": self._cmd_help,
            "exit": self._cmd_exit,
            "quit": self._cmd_exit,
            "bye": self._cmd_exit,
            "clear": self._cmd_clear,
        }

        if command in commands:
            try:
                commands[command](args)
            except Exception as e:
                console.print(f"[red][X] Error: {e}[/red]")
                self.logger.exception("Command execution failed")
        else:
            console.print(
                f"[red]Unknown command: '{command}'. Type 'help' or use query syntax.[/red]"
            )

    def _execute_query(self, query: str) -> None:
        """Execute a data conversion query.

        Args:
            query: Full query string (e.g., "from data.json[users.*] to out.yaml where age > 25")
        """
        try:
            # Parse the query
            parser = QueryParser()
            parsed_query = parser.parse(query)

            # Extract components
            source_file = Path(parsed_query["source"]["file"])
            source_path = parsed_query["source"]["path"]
            dest_file = Path(parsed_query["dest"]["file"])
            conditions = parsed_query["conditions"]

            # Load source data
            console.print(f"[cyan]Loading: {source_file}[/cyan]")
            data = smart_load(source_file)

            # Apply path extraction if specified
            if source_path:
                console.print(f"[cyan]Extracting path: [{source_path}][/cyan]")
                data = apply_path(data, source_path)

            # Apply conditions if specified
            if conditions:
                console.print(f"[cyan]Applying {len(conditions)} filter(s)...[/cyan]")
                data = apply_conditions(data if isinstance(data, list) else [data], conditions)

            # Validate before saving
            target_format = detect_format(dest_file)
            validation_result = validate(data, target_format)

            if validation_result.warnings:
                for warning in validation_result.warnings:
                    console.print(f"[yellow][!] {warning.message}[/yellow]")

            if validation_result.errors:
                console.print("[red]Validation failed:[/red]")
                for error in validation_result.errors:
                    console.print(f"[red]  [X] {error.message}[/red]")
                return

            # Handle list data for TOML/XML (requires dict root)
            if isinstance(data, list):
                if target_format.value == "toml":
                    console.print(
                        "[yellow][!] Wrapping list in {'root': data} for TOML compatibility[/yellow]"
                    )
                    data = {"root": data}
                elif target_format.value == "xml":
                    console.print(
                        "[yellow][!] Wrapping list in {'root': {'item': data}} for XML compatibility[/yellow]"
                    )
                    data = {"root": {"item": data}}

            # Save to destination
            smart_save(data, dest_file, atomic=True)

            # Update state
            self.current_data = data
            self.current_file = dest_file

            # Success message
            record_count = self._count_records(data)
            console.print(f"[green][+] Processed {record_count} record(s) -> {dest_file}[/green]")

        except ParseError as e:
            console.print(f"[red][X] Parse error: {e}[/red]")
        except Exception as e:
            console.print(f"[red][X] Error: {e}[/red]")
            self.logger.exception("Query execution failed")

    def _cmd_load(self, args: str) -> None:
        """Load a data file into memory.

        Args:
            args: File path to load
        """
        if not args:
            console.print("[red]Usage: load <file_path>[/red]")
            return

        file_path = Path(args.strip())

        if not file_path.exists():
            console.print(f"[red][X] File not found: {file_path}[/red]")
            return

        try:
            self.current_data = smart_load(file_path)
            self.current_file = file_path
            self.current_format = detect_format(file_path).value

            # Count records
            record_count = self._count_records(self.current_data)
            console.print(
                f"[green][+] Loaded:[/green] {file_path.name} "
                f"({record_count} record{'s' if record_count != 1 else ''})"
            )

        except DataConverterIOError as e:
            console.print(f"[red][X] Failed to load file: {e}[/red]")

    def _cmd_save(self, args: str) -> None:
        """Save current data to a file.

        Args:
            args: File path to save to
        """
        if not args:
            console.print("[red]Usage: save <file_path>[/red]")
            return

        if self.current_data is None:
            console.print("[red][X] No data loaded. Use 'load <file>' first.[/red]")
            return

        file_path = Path(args.strip())

        try:
            smart_save(self.current_data, file_path, atomic=True)
            console.print(f"[green][+] Saved to:[/green] {file_path}")
        except DataConverterIOError as e:
            console.print(f"[red][X] Failed to save file: {e}[/red]")

    def _cmd_convert(self, args: str) -> None:
        """Convert and save data with optional filtering.

        Supports syntax:
            convert to <file>
            convert to <file> where <conditions>

        Args:
            args: "to <file> [where <conditions>]"
        """
        if not args:
            console.print("[red]Usage: convert to <file> [where <conditions>][/red]")
            return

        if self.current_data is None:
            console.print("[red][X] No data loaded. Use 'load <file>' first.[/red]")
            return

        # Parse the convert command
        # Expected format: "to <file> [where <conditions>]"
        if not args.lower().startswith("to "):
            console.print("[red]Usage: convert to <file> [where <conditions>][/red]")
            return

        # Build a query string for the parser
        # Normalize Windows paths (backslash -> forward slash) for the grammar
        source_file = self.current_file or Path("temp.json")
        source_path_str = str(source_file).replace("\\", "/")
        query = f"from {source_path_str} {args}"

        try:
            parser = QueryParser()
            parsed_query = parser.parse(query)

            dest_file = Path(parsed_query["dest"]["file"])
            dest_path = parsed_query["dest"]["path"]
            conditions = parsed_query["conditions"]

            if dest_path:
                console.print(
                    "[yellow][!] Warning: Path expressions on destination are ignored[/yellow]"
                )

            # Start with current data
            data = self.current_data

            # Apply path and conditions if specified
            source_path = parsed_query["source"]["path"]
            if source_path or conditions:
                try:
                    data = process_data(data, source_path, conditions)
                except ProcessorError as e:
                    console.print(f"[red][X] Processing error: {e}[/red]")
                    return

            # Validate for target format
            try:
                target_format = detect_format(dest_file)
                validation_result = validate(data, target_format)
            except ValidationError as e:
                console.print(f"[red][X] Validation error: {e}[/red]")
                return

            # Display validation warnings
            if validation_result.warnings:
                console.print("[yellow][!] Validation Warnings:[/yellow]")
                for warning in validation_result.warnings:
                    console.print(f"  • [{warning.path}] {warning.message}")

            if validation_result.errors:
                console.print("[red][X] Validation Errors:[/red]")
                for error in validation_result.errors:
                    console.print(f"  • [{error.path}] {error.message}")
                console.print(
                    "[red]Aborting due to validation errors. Fix the issues above.[/red]"
                )
                return

            # Handle list data for TOML/XML (requires dict root)
            if isinstance(data, list):
                if target_format.value == "toml":
                    console.print(
                        "[yellow][!] Wrapping list in {'root': data} for TOML compatibility[/yellow]"
                    )
                    data = {"root": data}
                elif target_format.value == "xml":
                    console.print(
                        "[yellow][!] Wrapping list in {'root': {'item': data}} for XML compatibility[/yellow]"
                    )
                    data = {"root": {"item": data}}

            # Save the file
            smart_save(data, dest_file, atomic=True)

            # Success message
            record_count = self._count_records(data)
            if conditions:
                console.print(
                    f"[green][+] Filtered {record_count} record(s), saved to {dest_file}[/green]"
                )
            else:
                console.print(f"[green][+] Converted and saved to {dest_file}[/green]")

        except ParseError as e:
            console.print(f"[red][X] Parse error: {e}[/red]")
        except DataConverterIOError as e:
            console.print(f"[red][X] I/O error: {e}[/red]")

    def _cmd_show(self, args: str) -> None:
        """Display current data preview.

        Args:
            args: Optional limit (default: 10 records)
        """
        if self.current_data is None:
            console.print("[red][X] No data loaded. Use 'load <file>' first.[/red]")
            return

        limit = 10
        if args.strip().isdigit():
            limit = int(args.strip())

        console.print(Panel(f"[cyan]Data Preview (limit: {limit})[/cyan]"))

        if isinstance(self.current_data, list):
            for i, item in enumerate(self.current_data[:limit]):
                console.print(f"[dim]{i + 1}.[/dim] {item}")
            if len(self.current_data) > limit:
                console.print(f"[dim]... and {len(self.current_data) - limit} more[/dim]")
        elif isinstance(self.current_data, dict):
            for i, (key, value) in enumerate(list(self.current_data.items())[:limit]):
                console.print(f"[cyan]{key}:[/cyan] {value}")
            if len(self.current_data) > limit:
                console.print(f"[dim]... and {len(self.current_data) - limit} more keys[/dim]")
        else:
            console.print(self.current_data)

    def _cmd_status(self, args: str) -> None:
        """Show current state information.

        Args:
            args: Unused
        """
        table = Table(title="Current Status", show_header=False, box=None)
        table.add_column("Property", style="cyan")
        table.add_column("Value")

        if self.current_file:
            table.add_row("Loaded File", str(self.current_file))
            table.add_row("Format", self.current_format.upper() if self.current_format else "Unknown")
            table.add_row("Records", str(self._count_records(self.current_data)))
        else:
            table.add_row("Status", "[yellow]No file loaded[/yellow]")

        console.print(table)

    def _cmd_validate(self, args: str) -> None:
        """Validate current data for a format.

        Args:
            args: Optional format to validate against (json, yaml, toml, xml)
        """
        if self.current_data is None:
            console.print("[red][X] No data loaded. Use 'load <file>' first.[/red]")
            return

        from src.io import FileFormat

        # Determine target format
        if args.strip():
            try:
                target_format = FileFormat(args.strip().lower())
            except ValueError:
                console.print(
                    f"[red][X] Invalid format: {args}. Valid: json, toml, yaml, xml[/red]"
                )
                return
        elif self.current_format:
            target_format = FileFormat(self.current_format)
        else:
            console.print("[red]Usage: validate [format][/red]")
            return

        console.print(f"Validating for [cyan]{target_format.value.upper()}[/cyan]...")

        try:
            validation_result = validate(self.current_data, target_format)
            report = format_validation_report(validation_result)
            console.print(report)
        except ValidationError as e:
            console.print(f"[red][X] Validation error: {e}[/red]")

    def _cmd_help(self, args: str) -> None:
        """Display help information.

        Args:
            args: Unused
        """
        help_table = Table(title="Available Commands", show_header=True)
        help_table.add_column("Command", style="cyan")
        help_table.add_column("Description")
        help_table.add_column("Example", style="dim")

        commands = [

            ("[bold cyan]Query Syntax[/bold cyan]", "", ""),

            ("from <file>[path] to <file>", "Convert between formats", "from data.json to output.yaml"),

            ("  + [path]", "Extract data path", "from data.json[users.*] to out.yaml"),

            ("  + where <cond>", "Filter data", "from data.json to out.yaml where age > 25"),

            ("", "", ""),

            ("[bold cyan]Helper Commands[/bold cyan]", "", ""),

            ("clear", "Clear screen", "clear"),

            ("help", "Show this help", "help"),

            ("exit / quit / bye", "Exit program", "exit"),

        ]



        for cmd, desc, example in commands:

            help_table.add_row(cmd, desc, example)

        console.print(help_table)

    def _cmd_exit(self, args: str) -> None:
        """Exit the REPL.

        Args:
            args: Unused
        """
        console.print("[cyan]Goodbye![/cyan]")
        self.running = False

    def _cmd_clear(self, args: str) -> None:
        """Clear the terminal screen.

        Args:
            args: Unused
        """
        console.clear()
        self._print_welcome()

    def _count_records(self, data: Any) -> int:
        """Count the number of records in data.

        Args:
            data: Data to count. Expected to be:
                  - list of records (returns list length)
                  - single record dict (returns 1)
                  - primitive value (returns 1)

        Returns:
            Number of records
        """
        if isinstance(data, list):
            return len(data)
        else:
            return 1

