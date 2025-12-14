"""Unit tests for src/cli.py module.

Tests cover:
- CLI commands (load, save, convert, show, status, validate, help, exit, clear)
- Command parsing
- Error handling
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.cli import InteractiveCLI


class TestCLICommands:
    """Tests for CLI command execution."""

    @pytest.fixture
    def cli(self):
        """Create an InteractiveCLI instance."""
        return InteractiveCLI(verbose=False)

    def test_load_command_success(self, cli):
        """Test successful file loading."""
        with patch("src.cli.smart_load") as mock_load:
            mock_load.return_value = {"name": "John", "age": 30}

            cli._cmd_load("files/data.json")

            assert cli.current_data is not None
            assert cli.current_file == Path("files/data.json")
            mock_load.assert_called_once()

    def test_load_command_file_not_found(self, cli):
        """Test load command with non-existent file."""
        cli._cmd_load("nonexistent.json")

        # Should not raise, just print error message
        assert cli.current_data is None

    def test_load_command_no_args(self, cli):
        """Test load command without arguments."""
        cli._cmd_load("")

        # Should not raise, just print usage message
        assert cli.current_data is None

    def test_save_command_success(self, cli):
        """Test successful file saving."""
        cli.current_data = {"name": "John"}

        with patch("src.cli.smart_save") as mock_save:
            cli._cmd_save("output.json")

            mock_save.assert_called_once()

    def test_save_command_no_data_loaded(self, cli):
        """Test save command without loaded data."""
        cli.current_data = None

        cli._cmd_save("output.json")

        # Should not raise, just print error message

    def test_save_command_no_args(self, cli):
        """Test save command without arguments."""
        cli.current_data = {"test": "data"}

        cli._cmd_save("")

        # Should not raise, just print usage message

    def test_convert_command_simple(self, cli):
        """Test basic convert command."""
        cli.current_data = {"name": "John", "age": 30}
        cli.current_file = Path("input.json")

        with patch("src.cli.smart_save") as mock_save, patch(
            "src.cli.validate"
        ) as mock_validate:
            from src.validation import ValidationResult

            mock_validate.return_value = ValidationResult()

            cli._cmd_convert("to output.yaml")

            mock_save.assert_called_once()

    def test_convert_command_no_data(self, cli):
        """Test convert without loaded data."""
        cli.current_data = None

        cli._cmd_convert("to output.yaml")

        # Should not raise, just print error message

    def test_show_command_with_data(self, cli):
        """Test show command with loaded data."""
        cli.current_data = [{"name": "John"}, {"name": "Jane"}]

        cli._cmd_show("")

        # Should not raise, just display data

    def test_show_command_no_data(self, cli):
        """Test show command without loaded data."""
        cli.current_data = None

        cli._cmd_show("")

        # Should not raise, just print error message

    def test_show_command_with_limit(self, cli):
        """Test show command with custom limit."""
        cli.current_data = [{"id": i} for i in range(100)]

        cli._cmd_show("5")

        # Should not raise, just display limited data

    def test_status_command_with_data(self, cli):
        """Test status command with loaded file."""
        cli.current_file = Path("test.json")
        cli.current_format = "json"
        cli.current_data = [{"name": "John"}]

        cli._cmd_status("")

        # Should not raise, just display status

    def test_status_command_no_data(self, cli):
        """Test status command without loaded file."""
        cli._cmd_status("")

        # Should not raise, just show "no file loaded"

    def test_validate_command_with_data(self, cli):
        """Test validate command."""
        cli.current_data = {"name": "John"}
        cli.current_format = "json"

        with patch("src.cli.validate") as mock_validate:
            from src.validation import ValidationResult

            mock_validate.return_value = ValidationResult()

            cli._cmd_validate("")

            mock_validate.assert_called_once()

    def test_validate_command_no_data(self, cli):
        """Test validate without loaded data."""
        cli.current_data = None

        cli._cmd_validate("")

        # Should not raise, just print error message

    def test_help_command(self, cli):
        """Test help command displays command list."""
        cli._cmd_help("")

        # Should not raise, just display help

    def test_exit_command(self, cli):
        """Test exit command."""
        cli._cmd_exit("")

        assert cli.running is False

    def test_exit_alias_quit(self, cli):
        """Test quit command (alias for exit)."""
        cli._execute_command("quit")

        assert cli.running is False

    def test_exit_alias_bye(self, cli):
        """Test bye command (alias for exit)."""
        cli._execute_command("bye")

        assert cli.running is False

    def test_clear_command(self, cli):
        """Test clear command."""
        with patch("src.cli.console.clear"):
            cli._cmd_clear("")

            # Should not raise

    def test_count_records_list(self, cli):
        """Test record counting for lists."""
        data = [{"id": 1}, {"id": 2}, {"id": 3}]
        count = cli._count_records(data)

        assert count == 3

    def test_count_records_dict(self, cli):
        """Test record counting for single dict."""
        data = {"id": 1}
        count = cli._count_records(data)

        assert count == 1

    def test_count_records_primitive(self, cli):
        """Test record counting for primitive value."""
        count = cli._count_records("single value")

        assert count == 1


class TestCLICommandParsing:
    """Tests for command parsing and dispatch."""

    @pytest.fixture
    def cli(self):
        """Create an InteractiveCLI instance."""
        return InteractiveCLI(verbose=False)

    def test_unknown_command(self, cli):
        """Test handling of unknown command."""
        cli._execute_command("unknown_command arg1 arg2")

        # Should not raise, just print error message

    def test_empty_command(self, cli):
        """Test empty command input."""
        # This would be handled in the run loop, but we can test execute
        # with empty input
        pass  # Empty input is filtered in run()

    def test_command_case_insensitive(self, cli):
        """Test commands are case-insensitive."""
        with patch.object(cli, "_cmd_help") as mock_help:
            cli._execute_command("HELP")
            mock_help.assert_called_once()

            cli._execute_command("Help")
            assert mock_help.call_count == 2


class TestCLIIntegration:
    """Integration tests for CLI workflow."""

    @pytest.fixture
    def cli(self):
        """Create an InteractiveCLI instance."""
        return InteractiveCLI(verbose=False)

    def test_load_then_show_workflow(self, cli):
        """Test loading a file then showing data."""
        with patch("src.cli.smart_load") as mock_load, \
            patch("pathlib.Path.exists", return_value=True):

            mock_load.return_value = [{"name": "John"}]
            cli._cmd_load("files/data.json")
            assert cli.current_data is not None

            cli._cmd_show("")
            # Should display the loaded data

    def test_load_then_save_workflow(self, cli):
        """Test loading then saving to different format."""
        with patch("src.cli.smart_load") as mock_load, \
            patch("src.cli.smart_save") as mock_save, \
            patch("pathlib.Path.exists", return_value=True):

            mock_load.return_value = {"name": "John"}
            cli._cmd_load("input.json")
            cli._cmd_save("output.yaml")

            assert mock_save.called


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
