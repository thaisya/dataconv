"""Tests for public API module.

This module tests the high-level library API functions that users call
to programmatically convert data between formats.
"""

import json
import tempfile
from pathlib import Path

import pytest
import toml
import yaml

from dataconv.api import convert, extract_path, filter, load, query, save


class TestLoad:
    """Tests for load() function."""

    def test_load_json(self):
        """Load JSON file with auto-detection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "data.json"
            test_file.write_text('{"name": "Alice", "age": 30}')

            data = load(test_file)

            assert data == {"name": "Alice", "age": 30}

    def test_load_yaml(self):
        """Load YAML file with auto-detection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "data.yaml"
            test_file.write_text("name: Bob\nage: 25")

            data = load(test_file)

            assert data == {"name": "Bob", "age": 25}

    def test_load_toml(self):
        """Load TOML file with auto-detection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "data.toml"
            test_file.write_text('name = "Charlie"\nage = 35')

            data = load(test_file)

            assert data == {"name": "Charlie", "age": 35}

    def test_load_with_string_path(self):
        """Load file using string path instead of Path object."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "data.json"
            test_file.write_text('{"key": "value"}')

            data = load(str(test_file))

            assert data == {"key": "value"}

    def test_load_with_encoding_option(self):
        """Load file with custom encoding option."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "data.json"
            test_file.write_text('{"message": "Hello 世界"}', encoding="utf-8")

            data = load(test_file, encoding="utf-8")

            assert data == {"message": "Hello 世界"}

    def test_load_with_jsonpath_extraction(self):
        """Load file with JSONPath extraction syntax."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "data.json"
            test_file.write_text('{"users": [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]}')

            users = load(str(test_file) + "[$.users[*]]")

            assert users == [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]

    def test_load_with_literal_brackets_in_filename(self):
        """Load file that has literal brackets in its name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "archive[2024].json"
            test_file.write_text('{"archived": true, "year": 2024}')

            data = load(test_file)

            assert data == {"archived": True, "year": 2024}

    def test_load_with_complex_jsonpath(self):
        """Load file with complex JSONPath wildcard extraction."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "data.json"
            test_file.write_text(
                '{"company": {"departments": [{"name": "Sales"}, {"name": "IT"}]}}'
            )

            departments = load(str(test_file) + "[$.company.departments[*].name]")

            assert departments == ["Sales", "IT"]


class TestSave:
    """Tests for save() function."""

    def test_save_json(self):
        """Save data to JSON file with auto-detection."""
        data = {"name": "Alice", "score": 95}

        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "output.json"

            save(data, output_file)

            assert output_file.exists()

            loaded = json.loads(output_file.read_text())
            assert loaded == data

    def test_save_yaml(self):
        """Save data to YAML file with auto-detection."""
        data = {"name": "Bob", "score": 88}

        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "output.yaml"

            save(data, output_file)

            assert output_file.exists()

            loaded = yaml.safe_load(output_file.read_text())
            assert loaded == data

    def test_save_toml(self):
        """Save data to TOML file with auto-detection."""
        data = {"name": "Charlie", "score": 92}

        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "output.toml"

            save(data, output_file)

            assert output_file.exists()

            loaded = toml.loads(output_file.read_text())
            assert loaded == data

    def test_save_with_string_path(self):
        """Save data using string path instead of Path object."""
        data = {"key": "value"}

        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "output.json"

            save(data, str(output_file))

            assert output_file.exists()
            loaded = json.loads(output_file.read_text())
            assert loaded == data

    def test_save_with_indent_option(self):
        """Save JSON with custom indent option."""
        data = {"name": "Test", "nested": {"key": "value"}}

        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "output.json"

            save(data, output_file, indent=4)

            content = output_file.read_text()
            assert "    " in content

    def test_save_with_atomic_option(self):
        """Save with atomic write option."""
        data = {"test": "atomic"}

        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "output.json"

            save(data, output_file, atomic=True)

            assert output_file.exists()
            loaded = json.loads(output_file.read_text())
            assert loaded == data

    def test_save_list_data(self):
        """Save list data to file."""
        data = [{"id": 1}, {"id": 2}, {"id": 3}]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "output.json"

            save(data, output_file)

            assert output_file.exists()
            loaded = json.loads(output_file.read_text())
            assert loaded == data


class TestExtractPath:
    """Tests for extract_path() function."""

    def test_extract_simple_path(self):
        """Extract data using simple JSONPath."""
        data = {"user": {"name": "Alice", "age": 30}}

        result = extract_path(data, "$.user.name")

        assert result == "Alice"

    def test_extract_array_wildcard(self):
        """Extract all array elements using wildcard."""
        data = {"users": [{"name": "Alice"}, {"name": "Bob"}]}

        result = extract_path(data, "$.users[*]")

        assert result == [{"name": "Alice"}, {"name": "Bob"}]

    def test_extract_nested_array_field(self):
        """Extract specific field from all array elements."""
        data = {"users": [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]}

        result = extract_path(data, "$.users[*].name")

        assert result == ["Alice", "Bob"]

    def test_extract_array_index(self):
        """Extract specific array element by index."""
        data = {"users": [{"name": "Alice"}, {"name": "Bob"}, {"name": "Charlie"}]}

        result = extract_path(data, "$.users[1]")

        assert result == {"name": "Bob"}

    def test_extract_complex_nested(self):
        """Extract from complex nested structure."""
        data = {
            "company": {
                "departments": [
                    {"name": "Sales", "employees": [{"name": "Alice"}, {"name": "Bob"}]},
                    {"name": "IT", "employees": [{"name": "Charlie"}]},
                ]
            }
        }

        result = extract_path(data, "$.company.departments[*].employees[*].name")

        assert result == ["Alice", "Bob", "Charlie"]


class TestFilter:
    """Tests for filter() function."""

    def test_filter_simple_comparison(self):
        """Filter list with simple comparison."""
        data = [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 17}, {"name": "Charlie", "age": 25}]

        result = filter(data, "age >= 18")

        assert len(result) == 2
        assert result[0]["name"] == "Alice"
        assert result[1]["name"] == "Charlie"

    def test_filter_equality(self):
        """Filter with equality operator."""
        data = [{"name": "Alice", "status": "active"}, {"name": "Bob", "status": "inactive"}]

        result = filter(data, 'status == "active"')

        assert len(result) == 1
        assert result[0]["name"] == "Alice"

    def test_filter_and_logic(self):
        """Filter with AND logic."""
        data = [
            {"name": "Alice", "age": 30, "active": True},
            {"name": "Bob", "age": 25, "active": False},
            {"name": "Charlie", "age": 35, "active": True},
        ]

        result = filter(data, "age > 28 and active == true")

        assert len(result) == 2
        assert result[0]["name"] == "Alice"
        assert result[1]["name"] == "Charlie"

    def test_filter_or_logic(self):
        """Filter with OR logic."""
        data = [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 17}, {"name": "Charlie", "age": 25}]

        result = filter(data, "age < 20 or age > 28")

        assert len(result) == 2
        assert result[0]["name"] == "Alice"
        assert result[1]["name"] == "Bob"

    def test_filter_not_operator(self):
        """Filter with NOT operator."""
        data = [{"name": "Alice", "active": True}, {"name": "Bob", "active": False}]

        result = filter(data, "active == false")

        assert len(result) == 1
        assert result[0]["name"] == "Bob"

    def test_filter_single_dict(self):
        """Filter single dictionary (non-list)."""
        data = {"name": "Alice", "age": 30}

        result = filter(data, "age > 25")

        assert result == {"name": "Alice", "age": 30}

    def test_filter_dict_no_match(self):
        """Filter single dict with no match returns empty dict."""
        data = {"name": "Alice", "age": 17}

        result = filter(data, "age >= 18")

        assert result == {}

    def test_filter_complex_expression(self):
        """Filter with complex nested boolean expression."""
        data = [
            {"name": "Alice", "age": 30, "city": "NYC"},
            {"name": "Bob", "age": 25, "city": "LA"},
            {"name": "Charlie", "age": 35, "city": "NYC"},
        ]

        result = filter(data, '(age > 28 and city == "NYC") or city == "LA"')

        assert len(result) == 3 # all match


class TestConvert:
    """Tests for convert() function."""

    def test_convert_json_to_yaml(self):
        """Convert JSON to YAML."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "input.json"
            source.write_text('{"name": "Alice", "age": 30}')

            dest = Path(tmpdir) / "output.yaml"
            convert(source, dest)

            assert dest.exists()
            loaded = yaml.safe_load(dest.read_text())
            assert loaded == {"name": "Alice", "age": 30}

    def test_convert_yaml_to_json(self):
        """Convert YAML to JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "input.yaml"
            source.write_text("name: Bob\nage: 25")

            dest = Path(tmpdir) / "output.json"
            convert(source, dest)

            assert dest.exists()
            loaded = json.loads(dest.read_text())
            assert loaded == {"name": "Bob", "age": 25}

    def test_convert_with_jsonpath(self):
        """Convert with JSONPath extraction."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "input.json"
            source.write_text('{"users": [{"name": "Alice"}, {"name": "Bob"}]}')

            dest = Path(tmpdir) / "output.yaml"
            convert(str(source) + "[$.users[*]]", dest)

            assert dest.exists()
            loaded = yaml.safe_load(dest.read_text())
            assert loaded == [{"name": "Alice"}, {"name": "Bob"}]

    def test_convert_with_options(self):
        """Convert with custom options."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "input.json"
            source.write_text('{"nested": {"key": "value"}}')

            dest = Path(tmpdir) / "output.json"
            convert(source, dest, indent=4)

            assert dest.exists()
            loaded = json.loads(dest.read_text())
            assert loaded == {"nested": {"key": "value"}}


class TestQuery:
    """Tests for query() function."""

    def test_query_simple_conversion(self):
        """Execute simple conversion query."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "input.json"
            source.write_text('{"name": "Alice", "age": 30}')

            dest = Path(tmpdir) / "output.yaml"
            result = query(f'from "{source.as_posix()}" to "{dest.as_posix()}"')

            assert result is None

            assert dest.exists()
            loaded = yaml.safe_load(dest.read_text())
            assert loaded == {"name": "Alice", "age": 30}

    def test_query_view_only(self):
        """Execute view-only query (no destination)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "input.json"
            source.write_text('{"name": "Bob", "age": 25}')

            result = query(f'from "{source.as_posix()}"')
            assert result is not None
            assert result == {"name": "Bob", "age": 25}

    def test_query_with_where_clause(self):
        """Execute query with WHERE clause filtering."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "input.json"
            source.write_text('[{"name": "Alice", "age": 30}, {"name": "Bob", "age": 17}]')

            result = query(f'from "{source.as_posix()}" where age >= 18')
            assert result is not None
            assert len(result) == 1
            assert result[0]["name"] == "Alice"

    def test_query_with_jsonpath(self):
        """Execute query with JSONPath extraction."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "input.json"
            source.write_text('{"users": [{"name": "Alice"}, {"name": "Bob"}]}')

            result = query(f'from "{source.as_posix()}"[$.users[*]]')
            assert result is not None
            assert result == [{"name": "Alice"}, {"name": "Bob"}]

    def test_query_complex_full_syntax(self):
        """Execute complex query with all features."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "input.json"
            source.write_text(
                '{"users": [{"name": "Alice", "age": 30, "active": true}, '
                '{"name": "Bob", "age": 25, "active": false}, '
                '{"name": "Charlie", "age": 35, "active": true}]}'
            )

            dest = Path(tmpdir) / "output.yaml"
            result = query(f'from "{source.as_posix()}"[$.users[*]] to "{dest.as_posix()}" where age > 28 and active == true')

            assert result is None

            assert dest.exists()
            loaded = yaml.safe_load(dest.read_text())
            assert len(loaded) == 2
            assert loaded[0]["name"] == "Alice"
            assert loaded[1]["name"] == "Charlie"

    def test_query_with_options(self):
        """Execute query with custom options."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "input.json"
            source.write_text('{"nested": {"key": "value"}}')

            dest = Path(tmpdir) / "output.json"
            query(f'from "{source.as_posix()}" to "{dest.as_posix()}"', indent=4)

            assert dest.exists()
            loaded = json.loads(dest.read_text())
            assert loaded == {"nested": {"key": "value"}}