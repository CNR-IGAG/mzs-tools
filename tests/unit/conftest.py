"""Pytest configuration for MzS Tools unit tests."""

import pytest


def pytest_collection_modifyitems(items):
    for item in items:
        item.add_marker("unit")


@pytest.fixture
def sample_comune_names():
    """Fixture providing sample comune names for testing."""
    return {
        "Roma (RM - Lazio)": "Roma",
        "Milano (MI - Lombardia)": "Milano",
        "Sant'Angelo (LE)": "Sant_Angelo",
        "Città Sant'Angelo": "Città_Sant_Angelo",
        "L'Aquila (AQ - Abruzzo)": "L_Aquila",
        "San Giovanni Rotondo": "San_Giovanni_Rotondo",
        "": "",
        "Roma": "Roma",
        "(Test)": "",
        "Test (": "Test",
    }


@pytest.fixture
def temp_file_structure(tmp_path):
    """Fixture creating a temporary file structure for testing."""
    # Create directories
    (tmp_path / "level1" / "level2").mkdir(parents=True)
    (tmp_path / "TestDir").mkdir()

    # Create files
    (tmp_path / "test.txt").write_text("test content")
    (tmp_path / "level1" / "nested.txt").write_text("nested content")
    (tmp_path / "level1" / "level2" / "deep.txt").write_text("deep content")

    return tmp_path
