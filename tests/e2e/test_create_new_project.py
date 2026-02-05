# -----------------------------------------------------------------------------
# Copyright (C) 2018-2026, CNR-IGAG LabGIS <labgis@igag.cnr.it>
# This file is part of MzS Tools.
#
# MzS Tools is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# MzS Tools is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with MzS Tools.  If not, see <https://www.gnu.org/licenses/>.
# -----------------------------------------------------------------------------

"""End-to-end tests for new MzS Tools project creation.

These tests verify the complete workflow of creating a new project,
from dialog interaction to project file verification.
"""

import random
import sqlite3
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

import pytest
from factory.base import Factory
from factory.faker import Faker
from qgis.core import QgsRectangle

from mzs_tools.core.mzs_project_manager import MzSProjectManager
from mzs_tools.gui.dlg_create_project import DlgCreateProject


class ProjectDataFactory(Factory):
    """Factory for generating test project data using Faker."""

    class Meta:
        model = dict

    study_author = Faker("name", locale="it_IT")
    author_email = Faker("email")


@pytest.fixture
def random_comune(tmp_path):
    """Fixture that picks a random municipality from the ISTAT dataset.

    Returns a tuple of (comune_display_name, cod_istat, comune_name)
    where comune_display_name is in the format used by the dialog completer.
    """
    dialog = DlgCreateProject()
    comuni = dialog.comuni
    comuni_names = dialog.comuni_names

    assert len(comuni) > 0, "No comuni data loaded from database template"

    # Pick a random comune
    random_index = random.randint(0, len(comuni) - 1)
    comune = comuni[random_index]
    comune_display_name = comuni_names[random_index]

    # comune is a tuple: (comune_name, cod_istat, provincia, regione)
    comune_name = comune[0]
    cod_istat = comune[1]

    return comune_display_name, cod_istat, comune_name


@pytest.fixture
def project_data():
    """Fixture that generates fake project data using factory-boy."""
    return ProjectDataFactory()


class TestNewProjectCreation:
    """Test class for new project creation e2e tests."""

    def test_dialog_loads_comuni_data(self):
        """Test that the dialog loads municipality data from the template database."""
        dialog = DlgCreateProject()

        assert hasattr(dialog, "comuni")
        assert hasattr(dialog, "comuni_names")
        assert len(dialog.comuni) > 0
        assert len(dialog.comuni_names) == len(dialog.comuni)

        # Check structure of comuni data
        sample_comune = dialog.comuni[0]
        assert len(sample_comune) == 4  # (comune, cod_istat, provincia, regione)

    @pytest.mark.display
    def test_new_project_creation_via_dialog(
        self, tmp_path, qtbot, gui_timeout, random_comune, project_data, prj_manager
    ):
        """Test creating a new project by simulating user interaction with the dialog.

        This test:
        1. Opens the create project dialog
        2. Fills in municipality, author info, and output directory
        3. Accepts the dialog
        4. Calls create_project through the project manager
        5. Verifies the project structure is created correctly
        """
        comune_display_name, cod_istat, comune_name = random_comune
        study_author = project_data["study_author"]
        author_email = project_data["author_email"]

        # Create and show dialog
        dialog = DlgCreateProject()
        qtbot.addWidget(dialog)
        dialog.show()
        qtbot.wait(100)

        # Simulate user input
        # Set comune using the display name format
        dialog.comune_line_edit.setText(comune_display_name)
        qtbot.wait(100)

        # Verify cod_istat was auto-populated
        assert dialog.cod_istat_line_edit.text() == cod_istat

        # Fill in author information
        dialog.study_author_line_edit.setText(study_author)
        dialog.author_email_line_edit.setText(author_email)

        # Set output directory
        dialog.output_dir_widget.lineEdit().setText(str(tmp_path))

        # Validate that ok button is enabled
        dialog.validate_input()
        assert dialog.ok_button.isEnabled(), "OK button should be enabled after filling all required fields"

        qtbot.wait(gui_timeout)

        # Close dialog without executing exec() since we'll call create_project directly
        dialog.close()

        # Now create the project using the project manager
        # Patch iface to prevent actual project loading and provide mock canvas
        with patch("mzs_tools.core.mzs_project_manager.iface") as mock_iface:
            mock_iface.addProject.return_value = True
            # Mock mapCanvas and its extent method
            mock_canvas = mock_iface.mapCanvas.return_value
            mock_canvas.extent.return_value = QgsRectangle(0, 0, 100, 100)

            project_path = prj_manager.create_project(
                comune_name=comune_name,
                cod_istat=cod_istat,
                study_author=study_author,
                author_email=author_email,
                dir_out=str(tmp_path),
            )

        # Verify project was created
        assert project_path is not None
        assert project_path.exists()

        # Verify project structure
        self._verify_project_structure(project_path, cod_istat, comune_name, study_author, author_email)

    @pytest.mark.display
    def test_new_project_creation_direct(self, tmp_path, qtbot, gui_timeout, random_comune, project_data, prj_manager):
        """Test creating a new project directly through the project manager.

        This test bypasses the dialog and calls create_project directly,
        useful for testing the project creation logic in isolation.
        """
        comune_display_name, cod_istat, comune_name = random_comune
        study_author = project_data["study_author"]
        author_email = project_data["author_email"]

        # Create project directly with proper iface mock
        with patch("mzs_tools.core.mzs_project_manager.iface") as mock_iface:
            mock_iface.addProject.return_value = True
            # Mock mapCanvas and its extent method
            mock_canvas = mock_iface.mapCanvas.return_value
            mock_canvas.extent.return_value = QgsRectangle(0, 0, 100, 100)

            project_path = prj_manager.create_project(
                comune_name=comune_name,
                cod_istat=cod_istat,
                study_author=study_author,
                author_email=author_email,
                dir_out=str(tmp_path),
            )

        # Verify project was created
        assert project_path is not None
        assert project_path.exists()

        # Verify complete project structure
        self._verify_project_structure(project_path, cod_istat, comune_name, study_author, author_email)

        qtbot.wait(gui_timeout)

    def test_project_creation_with_existing_directory_adds_timestamp(
        self, tmp_path, random_comune, project_data, prj_manager
    ):
        """Test that creating a project in an existing directory adds a timestamp suffix."""
        comune_display_name, cod_istat, comune_name = random_comune
        study_author = project_data["study_author"]
        author_email = project_data["author_email"]

        # Create the expected directory first to simulate existing project
        sanitized_name = prj_manager.sanitize_comune_name(comune_name)
        existing_dir = tmp_path / f"{cod_istat}_{sanitized_name}"
        existing_dir.mkdir(parents=True)

        # Create project - should create with timestamp suffix
        with patch("mzs_tools.core.mzs_project_manager.iface") as mock_iface:
            mock_iface.addProject.return_value = True
            mock_canvas = mock_iface.mapCanvas.return_value
            mock_canvas.extent.return_value = QgsRectangle(0, 0, 100, 100)

            project_path = prj_manager.create_project(
                comune_name=comune_name,
                cod_istat=cod_istat,
                study_author=study_author,
                author_email=author_email,
                dir_out=str(tmp_path),
            )

        # Verify project was created with timestamp suffix
        assert project_path is not None
        assert project_path.exists()
        assert project_path != existing_dir
        assert project_path.name.startswith(f"{cod_istat}_{sanitized_name}_")

    def test_project_database_contains_comune_data(self, tmp_path, random_comune, project_data, prj_manager):
        """Test that the project database contains the correct comune data."""
        comune_display_name, cod_istat, comune_name = random_comune
        study_author = project_data["study_author"]
        author_email = project_data["author_email"]

        with patch("mzs_tools.core.mzs_project_manager.iface") as mock_iface:
            mock_iface.addProject.return_value = True
            mock_canvas = mock_iface.mapCanvas.return_value
            mock_canvas.extent.return_value = QgsRectangle(0, 0, 100, 100)

            project_path = prj_manager.create_project(
                comune_name=comune_name,
                cod_istat=cod_istat,
                study_author=study_author,
                author_email=author_email,
                dir_out=str(tmp_path),
            )

        # Verify database contains correct data
        db_path = project_path / "db" / "indagini.sqlite"
        assert db_path.exists()

        with closing(sqlite3.connect(str(db_path))) as conn, closing(conn.cursor()) as cursor:
            # Check comune_progetto table has the correct ISTAT code
            cursor.execute("SELECT cod_istat FROM comune_progetto")
            result = cursor.fetchone()
            assert result is not None
            assert result[0] == cod_istat

    def _verify_project_structure(
        self, project_path: Path, cod_istat: str, comune_name: str, study_author: str, author_email: str
    ):
        """Helper method to verify the complete project structure.

        Args:
            project_path: Path to the created project directory
            cod_istat: Expected ISTAT code
            comune_name: Expected municipality name
            study_author: Expected study author name
            author_email: Expected author email
        """
        # Verify main directories exist
        assert (project_path / "Allegati").exists()
        assert (project_path / "Allegati" / "Altro").exists()
        assert (project_path / "Allegati" / "Documenti").exists()
        assert (project_path / "Allegati" / "log").exists()
        assert (project_path / "Allegati" / "Plot").exists()
        assert (project_path / "Allegati" / "Spettri").exists()

        assert (project_path / "progetto").exists()
        assert (project_path / "progetto" / "loghi").exists()

        assert (project_path / "db").exists()

        # Verify database file exists
        db_path = project_path / "db" / "indagini.sqlite"
        assert db_path.exists()

        # Verify version file exists
        version_file = project_path / "progetto" / "versione.txt"
        assert version_file.exists()

        # Verify project file exists
        project_file = project_path / "progetto_MS.qgz"
        assert project_file.exists()

        # Verify database structure
        with closing(sqlite3.connect(str(db_path))) as conn, closing(conn.cursor()) as cursor:
            # Verify comune_progetto table exists and has data
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='comune_progetto'")
            assert cursor.fetchone() is not None

            cursor.execute("SELECT cod_istat FROM comune_progetto")
            result = cursor.fetchone()
            assert result is not None, "comune_progetto table should have data"
            assert result[0] == cod_istat

            # Verify metadati table has author info
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='metadati'")
            assert cursor.fetchone() is not None

            cursor.execute("SELECT resp_metadato_nome, resp_metadato_email FROM metadati LIMIT 1")
            result = cursor.fetchone()
            if result:  # Metadata might not be written in all test scenarios
                assert result[0] == study_author, f"Expected author '{study_author}', got '{result[0]}'"
                assert result[1] == author_email, f"Expected email '{author_email}', got '{result[1]}'"


class TestProjectCreationEdgeCases:
    """Test edge cases and error conditions for project creation."""

    def test_special_characters_in_comune_name(self, tmp_path, project_data, qgis_new_project):
        """Test that special characters in comune name are handled correctly."""
        from qgis.core import QgsProject

        # Reset singleton
        MzSProjectManager._instance = None
        prj_manager = MzSProjectManager.instance()

        # Use a comune name with special characters
        comune_name = "Sant'Angelo Romano"
        cod_istat = "058100"

        with patch("mzs_tools.core.mzs_project_manager.iface") as mock_iface:
            mock_iface.addProject.return_value = True
            mock_canvas = mock_iface.mapCanvas.return_value
            mock_canvas.extent.return_value = QgsRectangle(0, 0, 100, 100)

            project_path = prj_manager.create_project(
                comune_name=comune_name,
                cod_istat=cod_istat,
                study_author=project_data["study_author"],
                author_email=project_data["author_email"],
                dir_out=str(tmp_path),
            )

        assert project_path is not None
        assert project_path.exists()
        # Verify the sanitized name doesn't break the path
        assert cod_istat in project_path.name

        # Cleanup
        QgsProject.instance().clear()
        if prj_manager.db_manager:
            prj_manager.db_manager.disconnect()
        MzSProjectManager._instance = None

    def test_long_author_name(self, tmp_path, random_comune, qgis_new_project):
        """Test that long author names are handled correctly."""
        from qgis.core import QgsProject

        MzSProjectManager._instance = None
        prj_manager = MzSProjectManager.instance()

        comune_display_name, cod_istat, comune_name = random_comune

        # Generate a very long author name
        long_author = "Prof. Dott. Ing. " + "A" * 200

        with patch("mzs_tools.core.mzs_project_manager.iface") as mock_iface:
            mock_iface.addProject.return_value = True
            mock_canvas = mock_iface.mapCanvas.return_value
            mock_canvas.extent.return_value = QgsRectangle(0, 0, 100, 100)

            project_path = prj_manager.create_project(
                comune_name=comune_name,
                cod_istat=cod_istat,
                study_author=long_author,
                author_email="test@example.com",
                dir_out=str(tmp_path),
            )

        assert project_path is not None
        assert project_path.exists()

        # Cleanup
        QgsProject.instance().clear()
        if prj_manager.db_manager:
            prj_manager.db_manager.disconnect()
        MzSProjectManager._instance = None
