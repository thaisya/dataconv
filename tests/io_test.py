"""Unit tests for src/io.py module.

Tests cover:
- Format detection (detect_format)
- File loading (smart_load)
- File saving (smart_save)
- Error handling
"""

import json
import tempfile
from pathlib import Path

import pytest
import toml
import xmltodict
import yaml

from src.io import (
    DataConverterIOError,
    FileFormat,
    FileLoadError,
    FileSaveError,
    UnsupportedFormatError,
    detect_format,
    smart_load,
    smart_save,
)


class TestDetectFormat:
    """Tests for format detection."""

    def test_detect_json(self):
        """Test JSON format detection."""
        assert detect_format(Path("test.json")) == FileFormat.JSON

    def test_detect_yaml(self):
        """Test YAML format detection."""
        assert detect_format(Path("test.yaml")) == FileFormat.YAML

    def test_detect_yml(self):
        """Test .yml extension detection."""
        assert detect_format(Path("test.yml")) == FileFormat.YAML

    def test_detect_toml(self):
        """Test TOML format detection."""
        assert detect_format(Path("test.toml")) == FileFormat.TOML

    def test_detect_xml(self):
        """Test XML format detection."""
        assert detect_format(Path("test.xml")) == FileFormat.XML

    def test_detect_unsupported(self):
        """Test error on unsupported format."""
        with pytest.raises(UnsupportedFormatError) as exc_info:
            detect_format(Path("test.txt"))
        assert "Unsupported file format" in str(exc_info.value)


class TestSmartLoad:
    """Tests for smart file loading."""

    def test_load_json(self):
        """Test loading JSON file."""
        data = smart_load(Path("files/data.json"))
        assert isinstance(data, (dict, list))
        assert data is not None

    def test_load_yaml(self):
        """Test loading YAML file."""
        data = smart_load(Path("files/data.yaml"))
        assert isinstance(data, (dict, list))
        assert data is not None

    def test_load_toml(self):
        """Test loading TOML file."""
        data = smart_load(Path("files/john.toml"))
        assert isinstance(data, dict)
        assert data is not None

    def test_load_file_not_found(self):
        """Test error when file doesn't exist."""
        with pytest.raises(FileLoadError) as exc_info:
            smart_load(Path("nonexistent.json"))
        assert "File not found" in str(exc_info.value)

    def test_load_invalid_json(self):
        """Test error on malformed JSON."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{invalid json}")
            temp_path = Path(f.name)

        try:
            with pytest.raises(FileLoadError):
                smart_load(temp_path)
        finally:
            temp_path.unlink()


class TestSmartSave:
    """Tests for smart file saving."""

    def test_save_json(self):
        """Test saving to JSON file."""
        data = {"name": "John", "age": 30}
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "output.json"
            smart_save(data, output_path, atomic=True)

            assert output_path.exists()
            loaded = json.loads(output_path.read_text())
            assert loaded == data

    def test_save_yaml(self):
        """Test saving to YAML file."""
        data = {"name": "Jane", "age": 25}
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "output.yaml"
            smart_save(data, output_path, atomic=True)

            assert output_path.exists()
            loaded = yaml.safe_load(output_path.read_text())
            assert loaded == data

    def test_save_toml(self):
        """Test saving to TOML file."""
        data = {"name": "Bob", "age": 35}
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "output.toml"
            smart_save(data, output_path, atomic=True)

            assert output_path.exists()
            loaded = toml.loads(output_path.read_text())
            assert loaded == data

    def test_save_xml(self):
        """Test saving to XML file."""
        data = {"root": {"name": "Alice", "age": 28}}
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "output.xml"
            smart_save(data, output_path, atomic=True)

            assert output_path.exists()
            loaded = xmltodict.parse(output_path.read_text())
            assert "root" in loaded
            assert loaded["root"]["name"] == "Alice"
            assert loaded["root"]["age"] == "28"

    def test_save_atomic_vs_non_atomic(self):
        """Test difference between atomic and non-atomic writes."""
        data = {"test": "data"}
        with tempfile.TemporaryDirectory() as tmpdir:
            # Atomic write
            atomic_path = Path(tmpdir) / "atomic.json"
            smart_save(data, atomic_path, atomic=True)
            assert atomic_path.exists()

            # Non-atomic write
            non_atomic_path = Path(tmpdir) / "non_atomic.json"
            smart_save(data, non_atomic_path, atomic=False)
            assert non_atomic_path.exists()

    def test_save_creates_parent_dirs(self):
        """Test that parent directories are created automatically."""
        data = {"test": "nested"}
        with tempfile.TemporaryDirectory() as tmpdir:
            nested_path = Path(tmpdir) / "subdir" / "deep" / "output.json"
            smart_save(data, nested_path)

            assert nested_path.exists()
            assert nested_path.parent.exists()

    def test_save_json_with_indent(self):
        """Test JSON saving with custom indent kwarg."""
        data = {"name": "John", "age": 30}
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "indented.json"
            smart_save(data, output_path, indent=4)

            content = output_path.read_text()
            assert "    " in content
            assert '"name"' in content

    def test_save_yaml_with_allow_unicode(self):
        """Test YAML saving with allow_unicode kwarg."""
        data = {"name": "Алиса", "город": "Москва"}
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "unicode.yaml"
            smart_save(data, output_path, allow_unicode=True)

            content = output_path.read_text(encoding="utf-8")
            assert "Алиса" in content
            assert "Москва" in content

    def test_save_xml_with_pretty(self):
        """Test XML saving with pretty kwarg."""
        data = {"root": {"item": {"name": "Test", "value": 123}}}
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "pretty.xml"
            smart_save(data, output_path, pretty=True)

            content = output_path.read_text()
            assert "<?xml" in content
            assert "<root>" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
