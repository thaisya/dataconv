"""Command-line interface for the Data Converter.

This module provides a beautiful CLI using Typer and Rich for colored output,
progress bars, and enhanced user experience.

Example:
    $ dataconv "from test/test.json to output.yaml"
    $ dataconv "from data.json[users.*] to output.toml where age > 25"
    $ dataconv "from input.json to output.yaml" --verbose --dry-run
"""

import logging
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table

from src.io import DataConverterIOError, detect_format, smart_load, smart_save
from src.parser import ParseError, QueryParser
from src.processor import ProcessorError, process_data
from src.validation import ValidationError, format_validation_report, validate

# Initialize Typer app
app = typer.Typer(
    name="dataconv",
    help="🚀 Professional data format converter with query support",
    add_completion=False,
)

# Initialize Rich console
console = Console()


def setup_logging(verbose: bool = False) -> None:
    """Configure logging with Rich handler.

    Args:
        verbose: If True, set log level to DEBUG, otherwise INFO
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )


@app.command()
def convert(
    query: str = typer.Argument(
        ...,
        help='Query string: "from <source>[path] to <dest> where <conditions>"',
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose logging",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-d",
        help="Validate only, don't save output",
    ),
    no_atomic: bool = typer.Option(
        False,
        "--no-atomic",
        help="Disable atomic writes (not recommended)",
    ),
) -> None:
    """Convert data between formats with optional filtering.

    Examples:
        \b
        $ dataconv "from input.json to output.yaml"
        $ dataconv "from data.json[users.*] to output.toml"
        $ dataconv "from data.json to output.yaml where age > 25 and status == \\"active\\""
        $ dataconv "from input.json to output.yaml" --verbose --dry-run
    """
    setup_logging(verbose)
    logger = logging.getLogger(__name__)

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            console=console,
        ) as progress:
            # Step 1: Parse query
            task1 = progress.add_task("📖 Parsing query...", total=1)
            try:
                parser = QueryParser()
                parsed_query = parser.parse(query)
                logger.debug(f"Parsed query: {parsed_query}")
            except ParseError as e:
                console.print(f"[red]❌ Query parse error: {e}[/red]")
                raise typer.Exit(code=1)
            progress.update(task1, completed=1)

            # Extract query components
            source_file = Path(parsed_query["source"]["file"])
            source_path = parsed_query["source"]["path"]
            dest_file = Path(parsed_query["dest"]["file"])
            dest_path = parsed_query["dest"]["path"]
            conditions = parsed_query["conditions"]

            if dest_path:
                console.print(
                    "[yellow]⚠️  Warning: Path expressions on destination are ignored[/yellow]"
                )

            # Step 2: Load source file
            task2 = progress.add_task(f"📂 Loading {source_file.name}...", total=1)
            try:
                data = smart_load(source_file)
                logger.info(f"Loaded {source_file}")
            except DataConverterIOError as e:
                console.print(f"[red]❌ Failed to load file: {e}[/red]")
                raise typer.Exit(code=1)
            progress.update(task2, completed=1)

            # Step 3: Process data (apply path and conditions)
            if source_path or conditions:
                task3 = progress.add_task("⚙️  Processing data...", total=1)
                try:
                    data = process_data(data, source_path, conditions)
                    logger.info("Data processing completed")
                except ProcessorError as e:
                    console.print(f"[red]❌ Processing error: {e}[/red]")
                    raise typer.Exit(code=1)
                progress.update(task3, completed=1)

            # Step 4: Validate data for target format
            task4 = progress.add_task("✅ Validating data...", total=1)
            try:
                target_format = detect_format(dest_file)
                validation_result = validate(data, target_format)
            except ValidationError as e:
                console.print(f"[red]❌ Validation error: {e}[/red]")
                raise typer.Exit(code=1)
            progress.update(task4, completed=1)

            # Display validation results
            if validation_result.warnings:
                console.print()
                console.print("[yellow]⚠️  Validation Warnings:[/yellow]")
                for warning in validation_result.warnings:
                    console.print(f"  • [{warning.path}] {warning.message}")

            if validation_result.errors:
                console.print()
                console.print("[red]❌ Validation Errors:[/red]")
                for error in validation_result.errors:
                    console.print(f"  • [{error.path}] {error.message}")
                console.print()
                console.print(
                    "[red]Aborting due to validation errors. Fix the issues above.[/red]"
                )
                raise typer.Exit(code=1)

            # Handle list data for TOML/XML (requires dict root)
            if isinstance(data, list):
                if target_format.value == "toml":
                    console.print(
                        "[yellow]⚠️  Wrapping list in {'root': data} for TOML compatibility[/yellow]"
                    )
                    data = {"root": data}
                elif target_format.value == "xml":
                    console.print(
                        "[yellow]⚠️  Wrapping list in {'root': {'item': data}} for XML compatibility[/yellow]"
                    )
                    data = {"root": {"item": data}}

            # Step 5: Save output file
            if dry_run:
                console.print()
                console.print(
                    Panel(
                        "✅ Validation passed! (Dry run - file not saved)",
                        style="green",
                    )
                )
            else:
                task5 = progress.add_task(f"💾 Saving {dest_file.name}...", total=1)
                try:
                    atomic = not no_atomic
                    smart_save(data, dest_file, atomic=atomic)
                    logger.info(f"Saved to {dest_file}")
                except DataConverterIOError as e:
                    console.print(f"[red]❌ Failed to save file: {e}[/red]")
                    raise typer.Exit(code=1)
                progress.update(task5, completed=1)

                # Success message
                console.print()
                success_table = Table.grid(padding=(0, 2))
                success_table.add_column(style="cyan")
                success_table.add_column()
                success_table.add_row("Source:", str(source_file))
                success_table.add_row("Destination:", str(dest_file))
                success_table.add_row("Format:", target_format.value.upper())
                if source_path:
                    success_table.add_row("Path:", source_path)
                if conditions:
                    success_table.add_row("Conditions:", f"{len(conditions)} filter(s)")

                console.print(
                    Panel(
                        success_table,
                        title="✅ Conversion Complete",
                        style="green",
                    )
                )

    except typer.Exit:
        raise
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️  Cancelled by user[/yellow]")
        raise typer.Exit(code=130)
    except Exception as e:
        logger.exception("Unexpected error occurred")
        console.print(f"[red]❌ Unexpected error: {e}[/red]")
        raise typer.Exit(code=1)


@app.command()
def validate_file(
    file_path: str = typer.Argument(..., help="Path to file to validate"),
    format_override: str | None = typer.Option(
        None,
        "--format",
        "-f",
        help="Override format detection (json, toml, yaml, xml)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose logging",
    ),
) -> None:
    """Validate a file for format compatibility.

    Examples:
        \b
        $ dataconv validate-file data.json
        $ dataconv validate-file data.txt --format json
    """
    setup_logging(verbose)
    logger = logging.getLogger(__name__)

    path = Path(file_path)

    try:
        # Load file
        console.print(f"📂 Loading [cyan]{path.name}[/cyan]...")
        data = smart_load(path)

        # Detect or use override format
        if format_override:
            from src.io import FileFormat

            try:
                target_format = FileFormat(format_override.lower())
            except ValueError:
                console.print(
                    f"[red]❌ Invalid format: {format_override}. "
                    f"Valid: json, toml, yaml, xml[/red]"
                )
                raise typer.Exit(code=1)
        else:
            target_format = detect_format(path)

        console.print(f"✅ Validating as [cyan]{target_format.value.upper()}[/cyan]...")

        # Validate
        validation_result = validate(data, target_format)

        # Display results
        console.print()
        report = format_validation_report(validation_result)
        console.print(report)

        if not validation_result.is_valid():
            raise typer.Exit(code=1)

    except DataConverterIOError as e:
        console.print(f"[red]❌ I/O error: {e}[/red]")
        raise typer.Exit(code=1)
    except ValidationError as e:
        console.print(f"[red]❌ Validation error: {e}[/red]")
        raise typer.Exit(code=1)
    except Exception as e:
        logger.exception("Unexpected error occurred")
        console.print(f"[red]❌ Unexpected error: {e}[/red]")
        raise typer.Exit(code=1)


def main() -> None:
    """Entry point for the CLI application."""
    try:
        app()
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️  Cancelled by user[/yellow]")
        sys.exit(130)


if __name__ == "__main__":
    main()
