"""
Database upgrader module for MzS Tools.
Contains classes that implement the Strategy Pattern for database schema upgrades.
"""

from pathlib import Path
from typing import List, Optional
from qgis.PyQt.QtCore import QCoreApplication
from packaging.version import parse, Version

from ..__about__ import DIR_PLUGIN_ROOT


class DatabaseUpgrader:
    """Base class for version-specific database upgraders implementing Strategy Pattern"""

    def __init__(self, from_version: str, to_version: str, script_name: Optional[str] = None):
        """Initialize the upgrader with version information and optional script name

        Args:
            from_version: The minimum version this upgrader applies to
            to_version: The version this upgrader will update to
            script_name: Name of the SQL script to execute, if any
        """
        self.from_version = from_version
        self.to_version = to_version
        self.script_name = script_name

    def can_upgrade(self, current_version: str) -> bool:
        """Determines if this upgrader can handle the specified version

        Args:
            current_version: The current version of the database

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
        if self.script_name:
            # Execute the SQL script to upgrade the database
            project_manager.log(f"Executing database upgrade script: {self.script_name}", log_level=1)
            project_manager._exec_db_upgrade_script(self.script_name)

            # Note: We no longer call update_history_table() here
            # The calling code in update_db() method will handle adding history entries

        return True

    def get_description(self) -> str:
        """Get a human-readable description of this upgrade

        Returns:
            Description of what this upgrader does
        """
        return f"Upgrade database from v{self.from_version} to v{self.to_version}"

    def tr(self, message: str) -> str:
        """Translate a message

        Args:
            message: The message to translate

        Returns:
            The translated message
        """
        return QCoreApplication.translate(self.__class__.__name__, message)


class DbUpgrader_v08(DatabaseUpgrader):
    """Upgrader for database version 0.8"""

    def __init__(self):
        super().__init__("0.0.0", "0.8.0", "query_v08.sql")

    def get_description(self) -> str:
        return "Add new tables and fields for version 0.8"


class DbUpgrader_v09(DatabaseUpgrader):
    """Upgrader for database version 0.9"""

    def __init__(self):
        super().__init__("0.8.0", "0.9.0", "query_v09.sql")

    def get_description(self) -> str:
        return "Add and modify tables for version 0.9 database schema"


class DbUpgrader_v12(DatabaseUpgrader):
    """Upgrader for database version 1.2"""

    def __init__(self):
        super().__init__("0.9.0", "1.2.0", "query_v10_12.sql")

    def get_description(self) -> str:
        return "Implement database changes for versions 1.0-1.2"


class DbUpgrader_v19(DatabaseUpgrader):
    """Upgrader for database version 1.9"""

    def __init__(self):
        super().__init__("1.2.0", "1.9.0", "query_v19.sql")

    def get_description(self) -> str:
        return "Update database schema for version 1.9"


class DbUpgrader_v192(DatabaseUpgrader):
    """Upgrader for database version 1.9.2"""

    def __init__(self):
        super().__init__("1.9.0", "1.9.2", "query_v192.sql")

    def get_description(self) -> str:
        return "Apply minor fixes for version 1.9.2"


class DbUpgrader_v193(DatabaseUpgrader):
    """Upgrader for database version 1.9.3"""

    def __init__(self):
        super().__init__("1.9.2", "1.9.3", "query_v193.sql")

    def get_description(self) -> str:
        return "Update database tables for version 1.9.3"


class DbUpgrader_v200(DatabaseUpgrader):
    """Upgrader for database version 2.0.0"""

    def __init__(self):
        super().__init__("1.9.3", "2.0.0", "query_v200.sql")

    def get_description(self) -> str:
        return "Major upgrade to version 2.0.0 database schema"


class DatabaseUpgraderRegistry:
    """Registry for all available database upgraders"""

    def __init__(self):
        self.upgraders = []
        self._register_default_upgraders()

    def _register_default_upgraders(self):
        """Register all built-in upgraders"""
        self.upgraders.extend(
            [
                DbUpgrader_v08(),
                DbUpgrader_v09(),
                DbUpgrader_v12(),
                DbUpgrader_v19(),
                DbUpgrader_v192(),
                DbUpgrader_v193(),
                DbUpgrader_v200(),
                # Add new upgraders here as they become available
            ]
        )

    def register_upgrader(self, upgrader: DatabaseUpgrader):
        """Add an upgrader to the registry

        Args:
            upgrader: The upgrader to register
        """
        self.upgraders.append(upgrader)

    def get_applicable_upgraders(
        self, current_version: str, target_version: Optional[str] = None
    ) -> List[DatabaseUpgrader]:
        """Find all upgraders needed to upgrade from current_version to target_version (or latest)

        When upgrading a database (e.g., from 1.9.1 to 2.0.0-beta5), we need to apply
        ALL intermediate upgrade scripts (e.g., 1.9.1->1.9.2, 1.9.2->1.9.3, 1.9.3->2.0.0)

        Args:
            current_version: The current version of the database
            target_version: The desired target version

        Returns:
            List of applicable upgraders sorted in version order
        """
        applicable = []
        parsed_current = parse(current_version)
        parsed_target = parse(target_version) if target_version else None

        # Find all upgraders where:
        # 1. The 'from_version' is <= the current version
        # 2. The 'to_version' is > the current version
        # 3. If target_version is specified, the 'to_version' is <= target_version
        for upgrader in self.upgraders:
            parsed_from = parse(upgrader.from_version)
            parsed_to = parse(upgrader.to_version)

            if parsed_from <= parsed_current < parsed_to:
                if parsed_target and parsed_to > parsed_target:
                    continue
                applicable.append(upgrader)

        # Sort upgraders by their 'to_version' to ensure proper upgrade sequence
        return sorted(applicable, key=lambda u: parse(u.to_version))
