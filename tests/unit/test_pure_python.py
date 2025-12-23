"""Unit tests for pure Python functions that don't require QGIS."""

import tempfile
from pathlib import Path

import pytest


class TestPurePythonUtils:
    """Test pure Python utility functions."""

    def test_string_split_parentheses_basic(self):
        """Test the core logic behind sanitize_comune_name."""

        # This tests the core string manipulation without importing QGIS-dependent code
        def sanitize_comune_name(comune_name):
            """Pure Python version of the sanitization logic."""
            return comune_name.split(" (")[0].replace(" ", "_").replace("'", "_")

        assert sanitize_comune_name("Roma (RM - Lazio)") == "Roma"
        assert sanitize_comune_name("Milano (MI - Lombardia)") == "Milano"
        assert sanitize_comune_name("Sant'Angelo (LE)") == "Sant_Angelo"
        assert sanitize_comune_name("Città Sant'Angelo") == "Città_Sant_Angelo"
        assert sanitize_comune_name("L'Aquila (AQ - Abruzzo)") == "L_Aquila"
        assert sanitize_comune_name("San Giovanni Rotondo") == "San_Giovanni_Rotondo"

    def test_path_walking_logic(self):
        """Test directory traversal logic without QGIS dependencies."""

        def find_files_by_extension(root_path, extension):
            """Find files with given extension recursively."""
            files = []
            for root, dirs, filenames in Path(root_path).walk():
                for filename in filenames:
                    if filename.lower().endswith(extension.lower()):
                        files.append(root / filename)
            return files

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test files
            (temp_path / "test.qlr").write_text("test")
            (temp_path / "subdir").mkdir()
            (temp_path / "subdir" / "nested.QLR").write_text("nested")
            (temp_path / "other.txt").write_text("other")

            qlr_files = find_files_by_extension(temp_path, ".qlr")
            assert len(qlr_files) == 2
            assert any("test.qlr" in str(f) for f in qlr_files)
            assert any("nested.QLR" in str(f) for f in qlr_files)

    def test_version_parsing_logic(self):
        """Test version parsing logic."""

        def parse_version_string(version_str):
            """Parse a version string into components."""
            # Replace dash with dot for dev versions
            normalized = version_str.replace("-", ".", 1)
            parts = normalized.split(".")

            result = []
            for part in parts:
                if part.isdigit():
                    result.append(int(part))
                else:
                    result.append(part)

            return tuple(result)

        assert parse_version_string("2.0.1") == (2, 0, 1)
        assert parse_version_string("2.0.1-beta1") == (2, 0, 1, "beta1")
        assert parse_version_string("1.0") == (1, 0)

    def test_layer_config_validation(self):
        """Test layer configuration validation logic."""

        def validate_layer_config(config):
            """Validate a layer configuration dictionary."""
            required_fields = ["role", "type", "layer_name", "qlr_path"]
            valid_types = ["vector", "raster", "service_group", "wms", "wfs", "table", "group"]
            valid_roles = ["base", "editing"]

            errors = []

            # Check required fields
            for field in required_fields:
                if field not in config:
                    errors.append(f"Missing required field: {field}")
                elif not config[field]:
                    errors.append(f"Empty required field: {field}")

            # Check valid values
            if "type" in config and config["type"] not in valid_types:
                errors.append(f"Invalid type: {config['type']}")

            if "role" in config and config["role"] not in valid_roles:
                errors.append(f"Invalid role: {config['role']}")

            if "qlr_path" in config and not config["qlr_path"].endswith(".qlr"):
                errors.append(f"QLR path should end with .qlr: {config['qlr_path']}")

            return errors

        # Valid config
        valid_config = {"role": "base", "type": "vector", "layer_name": "Test Layer", "qlr_path": "test.qlr"}
        assert validate_layer_config(valid_config) == []

        # Invalid config - has all required fields but with invalid values
        invalid_config = {
            "role": "invalid_role",
            "type": "invalid_type",
            "layer_name": "",  # Empty but present
            "qlr_path": "test.xml",  # Wrong extension
        }
        errors = validate_layer_config(invalid_config)

        # Should have 4 errors: empty layer_name, invalid role, invalid type, wrong qlr extension
        assert len(errors) == 4
        error_text = " ".join(errors)
        assert "QLR path should end with .qlr" in error_text
        assert "Invalid role" in error_text
        assert "Invalid type" in error_text
        assert "Empty required field: layer_name" in error_text

    def test_file_extension_handling(self):
        """Test file extension handling logic."""

        def normalize_extension(filename, expected_ext):
            """Ensure filename has the correct extension."""
            if not filename.lower().endswith(expected_ext.lower()):
                return filename + expected_ext
            return filename

        assert normalize_extension("test", ".qlr") == "test.qlr"
        assert normalize_extension("test.QLR", ".qlr") == "test.QLR"
        assert normalize_extension("test.xml", ".qlr") == "test.xml.qlr"

    def test_configuration_parsing(self):
        """Test configuration file parsing logic."""

        def parse_simple_config(config_text):
            """Parse a simple key=value configuration."""
            config = {}
            for line in config_text.strip().split("\n"):
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    config[key.strip()] = value.strip()
            return config

        config_text = """
        # This is a comment
        name=Test Plugin
        version=1.0.0
        author=Test Author

        # Another comment
        description=A test plugin
        """

        config = parse_simple_config(config_text)
        assert config["name"] == "Test Plugin"
        assert config["version"] == "1.0.0"
        assert config["author"] == "Test Author"
        assert config["description"] == "A test plugin"
        assert len(config) == 4  # Only non-comment, non-empty lines
