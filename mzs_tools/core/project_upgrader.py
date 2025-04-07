"""
Project upgrader module for MzS Tools.
Contains classes that implement the Strategy Pattern for QGIS project structure upgrades.
"""

import os
import shutil
import traceback
from pathlib import Path
from typing import List, Optional, Union, Dict, Any

from qgis.core import QgsProject
from qgis.PyQt.QtCore import QCoreApplication
from qgis.utils import iface
from packaging.version import parse, Version

from ..__about__ import __version__, __base_version__, DIR_PLUGIN_ROOT


class ProjectUpgrader:
    """Base class for version-specific project upgraders implementing Strategy Pattern"""

    def __init__(self, from_version: str, to_version: str):
        """Initialize the upgrader with version information

        Args:
            from_version: The minimum version this upgrader applies to
            to_version: The version this upgrader will update to
        """
        self.from_version = from_version
        self.to_version = to_version

    def can_upgrade(self, current_version: str) -> bool:
        """Determines if this upgrader can handle the specified version

        Args:
            current_version: The current version of the project

        Returns:
            True if this upgrader applies to the current version
        """
        # Parse versions using packaging.version which correctly handles pre-release versions
        parsed_current = parse(current_version)
        parsed_from = parse(self.from_version)
        parsed_to = parse(self.to_version)

        # The upgrader applies if:
        # 1. Current version is less than to_version (including if current is a pre-release of to_version)
        # 2. Current version is greater than or equal to from_version
        return parsed_current < parsed_to and parsed_current >= parsed_from

    def upgrade(self, project_manager) -> bool:
        """Performs the upgrade operations

        Args:
            project_manager: Reference to the project manager

        Returns:
            True if upgrade was successful
        """
        # Base implementation does nothing
        return True

    def rollback(self, project_manager) -> bool:
        """Rolls back changes if upgrade fails

        Args:
            project_manager: Reference to the project manager

        Returns:
            True if rollback was successful
        """
        # Base implementation does nothing
        return True

    def get_description(self) -> str:
        """Get a human-readable description of this upgrade

        Returns:
            Description of what this upgrader does
        """
        return f"Upgrade project structure from v{self.from_version} to v{self.to_version}"

    def tr(self, message: str) -> str:
        """Translate a message

        Args:
            message: The message to translate

        Returns:
            The translated message
        """
        return QCoreApplication.translate(self.__class__.__name__, message)


class ProjectUpgrader_v200(ProjectUpgrader):
    """Major upgrader for projects to version 2.0.0"""

    def __init__(self):
        super().__init__("0.0.0", "2.0.0")

    def get_description(self) -> str:
        return "Upgrade project structure to version 2.0.0 (complete rebuild)"

    def upgrade(self, project_manager) -> bool:
        """Perform major upgrade to v2.0.0 by completely rebuilding the project

        Args:
            project_manager: Reference to the project manager

        Returns:
            True if upgrade was successful
        """
        # Record the update in history
        if project_manager.db_connection:
            project_manager.update_history_table(
                "project", project_manager.project_version, __version__, "clearing and rebuilding project"
            )

        # Backup print layouts
        layout_file_paths = project_manager.backup_print_layouts(
            backup_label=f"backup_v.{project_manager.project_version}", backup_all=True, backup_models=True
        )

        # Clear the project (db connection is automatically closed!)
        project_manager.current_project.clear()

        # Add default layers and customize the project
        project_manager._setup_db_connection()
        project_manager.add_default_layers()
        project_manager.customize_project()

        # Load the print layouts from the backup
        try:
            for layout_file_path in layout_file_paths:
                if layout_file_path.exists():
                    project_manager.load_print_layout_model(layout_file_path)
        except Exception as e:
            project_manager.log(f"Error loading print layout model backups: {e}", log_level=1)

        project_manager.refresh_project_layouts()

        # Update version file
        with open(project_manager.project_path / "progetto" / "versione.txt", "w") as f:
            f.write(__base_version__)

        # Save the project
        project_path = str(project_manager.project_path / "progetto_MS.qgz")
        project_manager.current_project.write(project_path)

        # Cleanup old project files
        self._cleanup_old_files(project_manager)

        # Reload the project
        iface.addProject(os.path.join(project_manager.project_path, "progetto_MS.qgz"))

        return True

    def _cleanup_old_files(self, project_manager):
        """Clean up old project files that are no longer needed

        Args:
            project_manager: Reference to the project manager
        """
        old_files = [
            project_manager.project_path / "progetto_MS.qgs",
            project_manager.project_path / "progetto_MS.qgs~",
            project_manager.project_path / "progetto_MS_attachments.zip",
            project_manager.project_path / "progetto" / "script",
            project_manager.project_path / "progetto" / "maschere",
        ]

        for path in old_files:
            if path.exists():
                if path.is_file():
                    path.unlink()
                elif path.is_dir():
                    shutil.rmtree(path)


class ProjectUpgrader_v210(ProjectUpgrader):
    """Incremental upgrader for projects from v2.0.0 to v2.1.0"""

    def __init__(self):
        super().__init__("2.0.0", "2.1.0")

    def get_description(self) -> str:
        return "Upgrade project structure from v2.0.0 to v2.1.0"

    def upgrade(self, project_manager) -> bool:
        """Perform incremental update to v2.1.0

        Args:
            project_manager: Reference to the project manager

        Returns:
            True if upgrade was successful
        """
        # Example of a more targeted upgrade - add only new layout groups
        project_manager.add_default_layers(add_base_layers=False, add_editing_layers=False, add_layout_groups=True)

        # Update version file
        with open(project_manager.project_path / "progetto" / "versione.txt", "w") as f:
            f.write(self.to_version)

        # Save project
        project_path = str(project_manager.project_path / "progetto_MS.qgz")
        project_manager.current_project.write(project_path)

        return True


class ProjectUpgraderRegistry:
    """Registry for all available project upgraders"""

    def __init__(self):
        self.upgraders = []
        self._register_default_upgraders()

    def _register_default_upgraders(self):
        """Register all built-in upgraders"""
        self.upgraders.extend(
            [
                ProjectUpgrader_v200(),
                ProjectUpgrader_v210(),
                # Add new upgraders here as they become available
            ]
        )

    def register_upgrader(self, upgrader: ProjectUpgrader):
        """Add an upgrader to the registry

        Args:
            upgrader: The upgrader to register
        """
        self.upgraders.append(upgrader)

    def get_applicable_upgraders(
        self, current_version: str, target_version: Optional[str] = None
    ) -> List[ProjectUpgrader]:
        """Find the appropriate project upgrader for the current version

        Project upgrades are handled differently than database upgrades:
        - For major version jumps (e.g. 1.x → 2.0), use the major upgrader (v200)
        - For minor versions (e.g. 2.0 → 2.1), use only the specific minor upgrader

        Args:
            current_version: The current version of the project
            target_version: The desired target version

        Returns:
            List containing the single most appropriate upgrader
        """
        parsed_current = parse(current_version)
        parsed_target = parse(target_version) if target_version else None

        # Get major version numbers (e.g., 1.x.x → 1, 2.x.x → 2)
        current_major = parsed_current.release[0] if parsed_current.release else 0

        # Find the most appropriate upgrader based on version transition
        best_upgrader = None

        for upgrader in self.upgraders:
            parsed_from = parse(upgrader.from_version)
            parsed_to = parse(upgrader.to_version)

            # Skip if this upgrader's target version is higher than our target
            if parsed_target and parsed_to > parsed_target:
                continue

            # If crossing major versions (e.g., 1.x → 2.0), prefer the major upgrader
            if current_major < parsed_to.release[0]:
                if parsed_from.release[0] == 0:  # Most general upgrader (e.g., 0.0.0 → 2.0.0)
                    best_upgrader = upgrader
                    break

            # For same major version, use the upgrader that covers our specific version
            elif parsed_from <= parsed_current < parsed_to:
                # If we already found an upgrader, pick the one with higher from_version
                if best_upgrader is None or parsed_from > parse(best_upgrader.from_version):
                    best_upgrader = upgrader

        return [best_upgrader] if best_upgrader else []
