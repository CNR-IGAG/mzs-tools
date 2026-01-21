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

import platform
import re
import subprocess
from datetime import datetime
from pathlib import Path

from ..__about__ import DIR_PLUGIN_ROOT
from ..plugin_utils.dependency_manager import DependencyManager
from ..plugin_utils.logging import MzSToolsLogger
from ..plugin_utils.misc import find_libjvm
from ..plugin_utils.settings import PlgOptionsManager

MIN_JAVA_VERSION = 11
UCANACCESS_JAR_PATH = DIR_PLUGIN_ROOT / "ext_libs" / "ucanaccess-5.1.5-uber.jar"
EXT_LIBS_LOADED = True

try:
    import jaydebeapi
    import jpype
    import jpype.imports
    from jpype.types import *  # type: ignore # noqa: F403
except ImportError:
    EXT_LIBS_LOADED = False


class AccessDbConnection:
    def __init__(self, db_path: str, password: str | None = None):
        global EXT_LIBS_LOADED, jaydebeapi, jpype
        self.log = MzSToolsLogger().log
        self.plg_settings = PlgOptionsManager()

        # Check if dependencies are available
        if not EXT_LIBS_LOADED:
            # Check if dependencies were installed after initial import
            dependency_manager = DependencyManager()
            if dependency_manager.check_python_dependencies():
                # Try importing again
                try:
                    import jaydebeapi
                    import jpype
                    import jpype.imports

                    EXT_LIBS_LOADED = True
                except ImportError:
                    pass

            # If still not loaded, raise clear error
            if not EXT_LIBS_LOADED:
                raise ImportError("Required Python libraries not loaded")

        self.driver = "net.ucanaccess.jdbc.UcanaccessDriver"
        self.url = f"jdbc:ucanaccess://{db_path}"
        self.options = {}
        if password:
            self.options["password"] = password
        self.classpath = UCANACCESS_JAR_PATH
        self.connection = None
        self.cursor = None
        self.java_home_override = None

    def _check_java_version(self, java_path: str | None = None) -> tuple[bool, str, int | None]:
        """
        Check Java version to ensure compatibility before starting JVM.
        Old Java versions (< 11) can cause fatal crashes especially on Windows.

        Args:
            java_path: Optional path to Java executable or libjvm. If not provided,
                      will attempt to find it automatically.

        Returns:
            Tuple of (is_compatible, version_string, major_version)
            - is_compatible: True if Java version >= 11 or version couldn't be determined
            - version_string: The Java version string
            - major_version: The major version number (e.g., 8, 11, 17) or None if parsing failed
        """
        try:
            # Determine Java executable path
            java_executable = None
            java_executables_to_try = []

            if java_path:
                java_path_obj = Path(java_path)
                # If a specific path is provided, try to find the java executable
                if java_path_obj.is_file():
                    # If it's a libjvm path, navigate to find java executable
                    current_dir = java_path_obj.parent
                    # Navigate up to find bin directory
                    for _ in range(5):  # Search up to 5 levels
                        potential_bin = current_dir / "bin"
                        if potential_bin.is_dir():
                            potential_exe = potential_bin / ("java.exe" if platform.system() == "Windows" else "java")
                            if potential_exe.is_file():
                                java_executable = str(potential_exe)
                                break
                        current_dir = current_dir.parent
                elif java_path_obj.is_dir():
                    # If it's a directory (JAVA_HOME), look for bin/java
                    potential_exe = java_path_obj / "bin" / ("java.exe" if platform.system() == "Windows" else "java")
                    if potential_exe.is_file():
                        java_executable = str(potential_exe)

            # Build list of java executables to try
            if java_executable:
                java_executables_to_try.append(java_executable)

            # On Windows, search common Java installation paths as fallback
            if platform.system() == "Windows" and not java_executables_to_try:
                common_java_paths = [
                    r"C:\Program Files\Java\jdk*\bin\java.exe",
                    r"C:\Program Files\Java\jre*\bin\java.exe",
                    r"C:\Program Files (x86)\Java\jdk*\bin\java.exe",
                    r"C:\Program Files (x86)\Java\jre*\bin\java.exe",
                ]

                for path_pattern in common_java_paths:
                    matches = sorted(Path().glob(path_pattern), reverse=True)
                    for match in matches:
                        if match.is_file():
                            java_executables_to_try.append(str(match))
                            self.log(f"Found Java at common installation path: {match}", log_level=4)
                            break  # Only add the first (latest) match from each pattern
                    if java_executables_to_try:
                        break  # Stop searching once we find a Java installation

            # Finally, try system java command as last resort
            if not java_executables_to_try:
                java_executables_to_try.append("java")

            # Try each java executable until one works
            result = None
            for java_exec in java_executables_to_try:
                try:
                    self.log(f"Trying Java executable: {java_exec}", log_level=4)

                    # On Windows, subprocess may have issues finding executables in QGIS environment
                    # Try with shell=True which uses the system shell to locate executables
                    if platform.system() == "Windows":
                        result = subprocess.run(
                            f'"{java_exec}" -version', shell=True, capture_output=True, text=True, timeout=5
                        )
                    else:
                        result = subprocess.run([java_exec, "-version"], capture_output=True, text=True, timeout=5)

                    # Check if command succeeded
                    if result.returncode == 0 or result.stderr:
                        java_executable = java_exec
                        self.log(f"Successfully executed Java at: {java_exec}", log_level=4)
                        break
                    else:
                        self.log(f"Java executable {java_exec} returned error code {result.returncode}", log_level=4)
                        result = None

                except (FileNotFoundError, OSError) as e:
                    self.log(f"Failed to execute {java_exec}: {e}", log_level=4)
                    continue
                except Exception as e:
                    self.log(f"Unexpected error executing {java_exec}: {e}", log_level=4)
                    continue

            if result is None:
                self.log(f"Could not find or execute Java. Tried: {', '.join(java_executables_to_try)}", log_level=1)
                raise FileNotFoundError("Could not find or execute Java")

            # Java version info is typically in stderr
            version_output = result.stderr if result.stderr else result.stdout
            self.log(f"Java version check output: {version_output}", log_level=4)

            # Parse version string (examples: "1.8.0_291", "11.0.10", "17.0.2")
            # Format: java version "VERSION" or openjdk version "VERSION"
            version_match = re.search(r'version "([^"]+)"', version_output)

            if version_match:
                version_string = version_match.group(1)
                self.log(f"Detected Java version: {version_string}", log_level=4)

                # Parse major version
                # Old format: 1.8.x -> major version is 8
                # New format: 11.x or 17.x -> major version is the first number
                version_parts = version_string.split(".")
                if version_parts[0] == "1" and len(version_parts) > 1:
                    # Old Java version format (1.6, 1.7, 1.8)
                    major_version = int(version_parts[1])
                else:
                    # New Java version format (9, 11, 17, etc.)
                    major_version = int(version_parts[0])

                self.log(f"Java major version: {major_version}", log_level=4)

                # Check if version meets minimum requirement
                if major_version < MIN_JAVA_VERSION:
                    self.log(
                        f"Java version {major_version} is below minimum required version {MIN_JAVA_VERSION}",
                        log_level=1,
                    )
                    return False, version_string, major_version
                else:
                    return True, version_string, major_version
            else:
                self.log("Could not parse Java version from output", log_level=1)
                # If we can't determine version, allow to proceed (fail gracefully)
                return True, "unknown", None

        except subprocess.TimeoutExpired:
            self.log("Java version check timed out", log_level=1)
            return True, "timeout", None
        except FileNotFoundError:
            self.log("Java executable not found", log_level=1)
            return True, "not_found", None
        except Exception as e:
            self.log(f"Error checking Java version: {e}", log_level=1)
            # If we can't check version, allow to proceed (fail gracefully)
            return True, "error", None

    def open(self):
        # Get plugin settings first
        settings = self.plg_settings.get_plg_settings()

        # Try using Java path from plugin settings first (if configured)
        if settings.java_home_path:
            self.log(f"Attempting to use Java home from settings: {settings.java_home_path}", log_level=4)
            libjvm_path = find_libjvm(settings.java_home_path)
            if libjvm_path:
                self.log(f"Found libjvm at: {libjvm_path}", log_level=4)
                self.java_home_override = libjvm_path
            else:
                self.log(
                    f"Could not find libjvm in the provided Java home path: {settings.java_home_path}",
                    log_level=1,
                )

        # Fall back to jpype auto-detection if plugin settings didn't work or weren't configured
        if not self.java_home_override:
            try:
                detected_jvm_path = jpype.getDefaultJVMPath()
                self.log(f"Detected JAVA_HOME from jpype: {detected_jvm_path}", log_level=4)
                self.java_home_override = detected_jvm_path
            except Exception as e:
                self.log(f"Error detecting JAVA_HOME from jpype: {e}", log_level=1)

        # Check Java version before starting JVM
        # Old Java versions (< 11) can cause fatal crashes
        self.log("Checking Java version compatibility before starting JVM", log_level=4)
        check_path = self.java_home_override if self.java_home_override else None

        is_compatible, version_str, major_version = self._check_java_version(check_path)

        if not is_compatible and major_version is not None:
            error_msg = (
                f"Incompatible Java version detected: {version_str} (Java {major_version}). "
                f"Java 11 or newer is required to avoid system crashes. "
                f"Please install Java 11 or later and configure it in the plugin settings."
            )
            self.log(error_msg, log_level=2)
            raise JavaVersionError(error_msg)
        elif version_str in ("not_found", "error"):
            self.log(
                "Could not verify Java version. Proceeding with caution. "
                "If QGIS crashes, please ensure Java 11 or later is installed.",
                log_level=1,
            )

        try:
            if not jpype.isJVMStarted():
                self.log("Starting Java JVM")
                if self.java_home_override:
                    jpype.startJVM(self.java_home_override, classpath=self.classpath, convertStrings=False)
                else:
                    jpype.startJVM(classpath=self.classpath, convertStrings=False)
                self.log(f"JVM version: {jpype.getJVMVersion()}", log_level=4)

                from java.lang import System  # type: ignore

                self.log(f"JVM classpath: {System.getProperty('java.class.path')}", log_level=4)
        except Exception as e:
            self.log(f"Error starting JVM: {e} ", log_level=2)
            raise JVMError("Error starting JVM") from e

        # Connect to the database
        self.log("Opening Access Db connection", log_level=4)
        try:
            self.connection = jaydebeapi.connect(self.driver, self.url, self.options)
        except Exception as e:
            # can import only when the JVM is running
            from net.ucanaccess.exception import AuthenticationException  # type: ignore

            self.log(f"{e} - {e.getMessage()}", log_level=4)  # type: ignore
            self.log(f"cause: {e.getCause()}", log_level=4)  # type: ignore
            # self.log(f"getErrorCode: {e.getErrorCode()}", log_level=4)

            if isinstance(e.getCause(), AuthenticationException):  # type: ignore
                raise MdbAuthError("Invalid password") from e

            raise e

        # Create a cursor
        self.cursor = self.connection.cursor()

        return True

    def close(self):
        self.log("Closing Access Db connection", log_level=4)
        # Close the cursor
        self.cursor.close()

        # Close the connection
        self.connection.close()

        # Shut down the JVM
        # jpype.shutdownJVM()

    def execute(self, query):
        # Execute the query
        self.cursor.execute(query)

        # Fetch the results
        return self.cursor.fetchall()

    def commit(self):
        # Commit the transaction
        self.connection.commit()

    def rollback(self):
        # Rollback the transaction
        self.connection.rollback()

    def _validate_date(self, date_value: str | None) -> str | None:
        """
        Validate and parse a date string. Returns None if the date is empty, None,
        or cannot be parsed in a recognizable format. If a datetime string is provided,
        the time part is stripped and only the date is validated and returned.

        The date is always returned in ISO format (yyyy-MM-dd).

        Args:
            date_value: Date string to validate

        Returns:
            The date string in ISO format (yyyy-MM-dd) if valid and parsable, None otherwise
        """
        if not date_value or date_value.strip() == "":
            return None

        # Strip and check for datetime strings (containing time parts)
        # Common patterns: "dd/MM/yyyy HH:mm:ss", "yyyy-MM-dd HH:mm:ss"
        stripped_value = date_value.strip()

        # Try to detect and strip time part
        # Look for space followed by time pattern (HH:mm:ss or HH:mm)
        date_part = stripped_value.split(" ")[0] if " " in stripped_value else stripped_value

        # List of common date formats to try
        date_formats = [
            "%Y-%m-%d",  # ISO format (yyyy-MM-dd)
            "%d/%m/%Y",  # dd/MM/yyyy
            "%m/%d/%Y",  # MM/dd/yyyy
            "%Y/%m/%d",  # yyyy/MM/dd
            "%d-%m-%Y",  # dd-MM-yyyy
            "%Y%m%d",  # yyyyMMdd
        ]

        for fmt in date_formats:
            try:
                parsed_date = datetime.strptime(date_part, fmt)
                # If parsing succeeds, return the date in ISO format (yyyy-MM-dd)
                return parsed_date.strftime("%Y-%m-%d")
            except (ValueError, TypeError):
                continue

        # If no format matched, log a warning and return None
        self.log(f"Unable to parse date value '{date_value}' - setting to NULL", log_level=1)
        return None

    def _validate_float(self, float_value: str | None) -> float | None:
        """
        Validate and parse a float string. Returns None if the value is empty, None,
        or cannot be parsed as a float.

        Args:
            float_value: Float string to validate

        Returns:
            The float value if valid and parsable, None otherwise
        """
        if not float_value or float_value.strip() == "":
            return None

        stripped_value = float_value.strip()

        try:
            return float(stripped_value)
        except (ValueError, TypeError):
            self.log(f"Unable to parse float value '{float_value}' - setting to NULL", log_level=1)
            return None

    def get_sito_puntuale_data(self):
        field_names = [
            "pkey_spu",
            "ubicazione_prov",
            "ubicazione_com",
            "ID_SPU",
            "indirizzo",
            "coord_X",
            "coord_Y",
            "mod_identcoord",
            "desc_modcoord",
            "modo_quota",
            "data_sito",
            "note_sito",
            "quota_slm",
        ]
        query = """SELECT [pkey_spu], [ubicazione_prov], [ubicazione_com], ID_SPU, [indirizzo], [coord_X], [coord_Y],
                   [mod_identcoord], [desc_modcoord], [modo_quota], [data_sito], [note_sito], [quota_slm] FROM [Sito_Puntuale]"""
        data = self.execute(query)
        return {
            row[3]: {
                field_name: str(value) if str(value) != "None" else ""
                for field_name, value in zip(field_names, row, strict=False)
            }
            for row in data
        }

    def get_sito_lineare_data(self):
        field_names = [
            "pkey_sln",
            "ubicazione_prov",
            "ubicazione_com",
            "ID_SLN",
            "Acoord_X",
            "Acoord_Y",
            "Bcoord_X",
            "Bcoord_Y",
            "mod_identcoord",
            "desc_modcoord",
            "data_sito",
            "note_sito",
            "Aquota",
            "Bquota",
        ]
        query = """SELECT [pkey_sln], [ubicazione_prov], [ubicazione_com], ID_SLN, [Acoord_X], [Acoord_Y], [Bcoord_X],
                [Bcoord_Y], [mod_identcoord], [desc_modcoord], [data_sito], [note_sito], [Aquota], [Bquota] FROM
                [Sito_Lineare]"""
        data = self.execute(query)
        return {
            row[3]: {
                field_name: str(value) if str(value) != "None" else ""
                for field_name, value in zip(field_names, row, strict=False)
            }
            for row in data
        }

    def get_indagini_puntuali_data(self):
        field_names = [
            "pkey_spu",
            "pkey_indpu",
            "classe_ind",
            "tipo_ind",
            "ID_INDPU",
            "id_indpuex",
            "arch_ex",
            "note_ind",
            "prof_top",
            "prof_bot",
            "spessore",
            "quota_slm_top",
            "quota_slm_bot",
            "data_ind",
            "doc_pag",
            "doc_ind",
        ]
        query = """SELECT [pkey_spu], [pkey_indpu], [classe_ind], [tipo_ind], ID_INDPU, [id_indpuex], [arch_ex],
                   [note_ind], [prof_top], [prof_bot], [spessore], [quota_slm_top], [quota_slm_bot], [data_ind],
                   [doc_pag], [doc_ind] FROM [Indagini_Puntuali]"""
        data = self.execute(query)
        return {
            (row[0], row[4]): {
                field_name: str(value) if str(value) != "None" else ""
                for field_name, value in zip(field_names, row, strict=False)
            }
            for row in data
        }

    def get_indagini_lineari_data(self):
        field_names = [
            "pkey_sln",
            "pkey_indln",
            "classe_ind",
            "tipo_ind",
            "ID_INDLN",
            "id_indlnex",
            "arch_ex",
            "note_indln",
            "data_ind",
            "doc_pag",
            "doc_ind",
        ]
        query = """SELECT [pkey_sln], [pkey_indln], [classe_ind], [tipo_ind], ID_INDLN, [id_indlnex], [arch_ex],
                [note_indln], [data_ind], [doc_pag], [doc_ind] FROM [Indagini_Lineari]"""
        data = self.execute(query)
        return {
            (row[0], row[4]): {
                field_name: str(value) if str(value) != "None" else ""
                for field_name, value in zip(field_names, row, strict=False)
            }
            for row in data
        }

    def get_parametri_puntuali_data(self):
        field_names = [
            "pkey_indpu",
            "pkey_parpu",
            "tipo_parpu",
            "ID_PARPU",
            "prof_top",
            "prof_bot",
            "spessore",
            "quota_slm_top",
            "quota_slm_bot",
            "valore",
            "attend_mis",
            "tab_curve",
            "note_par",
            "data_par",
        ]
        query = """SELECT [pkey_indpu], [pkey_parpu], [tipo_parpu], ID_PARPU, [prof_top], [prof_bot], [spessore],
                   [quota_slm_top], [quota_slm_bot], [valore], [attend_mis], [tab_curve], [note_par], [data_par]
                   FROM [Parametri_Puntuali]"""
        data = self.execute(query)
        return {
            (row[0], row[3]): {
                field_name: str(value) if str(value) != "None" else ""
                for field_name, value in zip(field_names, row, strict=False)
            }
            for row in data
        }

    def get_parametri_lineari_data(self):
        field_names = [
            "pkey_indln",
            "pkey_parln",
            "tipo_parln",
            "ID_PARLN",
            "prof_top",
            "prof_bot",
            "spessore",
            "quota_slm_top",
            "quota_slm_bot",
            "valore",
            "attend_mis",
            "note_par",
            "data_par",
        ]
        query = """SELECT [pkey_indln], [pkey_parln], [tipo_parln], ID_PARLN, [prof_top], [prof_bot], [spessore],
                [quota_slm_top], [quota_slm_bot], [valore], [attend_mis], [note_par], [data_par]
                   FROM [Parametri_Lineari]"""
        data = self.execute(query)
        return {
            (row[0], row[3]): {
                field_name: str(value) if str(value) != "None" else ""
                for field_name, value in zip(field_names, row, strict=False)
            }
            for row in data
        }

    def get_curve_data(self):
        field_names = [
            "pkey_parpu",
            "pkey_curve",
            "cond_curve",
            "varx",
            "vary",
        ]
        query = """SELECT [pkey_parpu], [pkey_curve], [cond_curve], [varx], [vary] FROM [Curve]"""
        data = self.execute(query)
        return {
            (row[0], row[1]): {
                field_name: str(value) if str(value) != "None" else ""
                for field_name, value in zip(field_names, row, strict=False)
            }
            for row in data
        }

    def insert_siti_puntuali(self, data):
        """Insert 'sito_puntuale' data into the database."""
        insert_errors = []
        for row in data:
            try:
                self.cursor.execute(
                    """
                    INSERT INTO [Sito_Puntuale] ([pkey_spu], ID_SPU, [ubicazione_prov], [ubicazione_com], [indirizzo],
                    [coord_X], [coord_Y], [mod_identcoord], [desc_modcoord], [quota_slm], [modo_quota], [data_sito],
                    [note_sito]) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row[0],
                        row[1],
                        row[2],
                        row[3],
                        row[4],
                        row[5],
                        row[6],
                        row[7],
                        row[8],
                        row[9],
                        row[10],
                        self._validate_date(row[11]),  # data_sito
                        row[12],
                    ),
                )
                self.commit()
            except Exception as e:
                self.log(f"Error inserting sito {row[1]}: {row} - {e}", log_level=2)
                insert_errors.append((row[1], e))
                continue
        return insert_errors

    def insert_indagini_puntuali(self, data):
        """Insert 'indagini_puntuali' data into the database."""
        insert_errors = []
        for row in data:
            try:
                self.cursor.execute(
                    """
                    INSERT INTO [Indagini_Puntuali] ([pkey_spu], [pkey_indpu], [classe_ind], [tipo_ind], ID_INDPU,
                    [id_indpuex], [arch_ex], [note_ind], [prof_top], [prof_bot], [spessore], [quota_slm_top],
                    [quota_slm_bot], [data_ind], [doc_pag], [doc_ind]) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?)""",
                    (
                        row[0],
                        row[1],
                        row[2],
                        row[3],
                        row[4],
                        row[5],
                        row[6],
                        row[7],
                        row[8],
                        row[9],
                        row[10],
                        row[11],
                        row[12],
                        self._validate_date(row[13]),  # data_ind
                        row[14],
                        row[15],
                    ),
                )
                self.commit()
            except Exception as e:
                self.log(f"Error inserting indagine {row[4]}: {row} - {e}", log_level=2)
                insert_errors.append((row[4], e))
                continue
        return insert_errors

    def insert_parametri_puntuali(self, data):
        """Insert 'parametri_puntuali' data into the database."""
        insert_errors = []
        for row in data:
            try:
                self.cursor.execute(
                    """
                    INSERT INTO [Parametri_Puntuali] ([pkey_indpu], [pkey_parpu], [tipo_parpu], ID_PARPU, [prof_top],
                    [prof_bot], [spessore], [quota_slm_top], [quota_slm_bot], [valore], [attend_mis], [tab_curve],
                    [note_par], [data_par]) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        row[0],
                        row[1],
                        row[2],
                        row[3],
                        row[4],
                        row[5],
                        row[6],
                        row[7],
                        row[8],
                        row[9],
                        row[10],
                        row[11],
                        row[12],
                        self._validate_date(row[13]),  # data_par
                    ),
                )
                self.commit()
            except Exception as e:
                self.log(f"Error inserting parametro {row[3]}: {row} - {e}", log_level=2)
                insert_errors.append((row[3], e))
                continue
        return insert_errors

    def insert_curve(self, data):
        """Insert 'curve' data into the database."""
        insert_errors = []
        for row in data:
            try:
                self.cursor.execute(
                    """
                    INSERT INTO [Curve] ([pkey_parpu], [pkey_curve], [cond_curve], [varx], [vary]) VALUES(?, ?, ?, ?, ?)
                    """,
                    (
                        row[0],
                        row[1],
                        row[2],
                        row[3],
                        row[4],
                    ),
                )
                self.commit()
            except Exception as e:
                self.log(f"Error inserting curve {row[1]}: {row} - {e}", log_level=2)
                insert_errors.append((row[1], e))
                continue
        return insert_errors

    def insert_siti_lineari(self, data):
        """Insert 'sito_lineare' data into the database."""
        insert_errors = []
        for row in data:
            try:
                self.cursor.execute(
                    """
                    INSERT INTO [Sito_Lineare] ([pkey_sln], ID_SLN, [ubicazione_prov], [ubicazione_com], [Acoord_X],
                    [Acoord_Y], [Bcoord_X], [Bcoord_Y], [mod_identcoord], [desc_modcoord], [Aquota], [Bquota], [data_sito],
                    [note_sito]) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row[0],
                        row[1],
                        row[2],
                        row[3],
                        row[4],
                        row[5],
                        row[6],
                        row[7],
                        row[8],
                        row[9],
                        row[10],
                        row[11],
                        self._validate_date(row[12]),  # data_sito
                        row[13],
                    ),
                )
                self.commit()
            except Exception as e:
                self.log(f"Error inserting sito {row[1]}: {row} - {e}", log_level=2)
                insert_errors.append((row[1], e))
                continue
        return insert_errors

    def insert_indagini_lineari(self, data):
        """Insert 'indagini_lineari' data into the database."""
        insert_errors = []
        for row in data:
            try:
                self.cursor.execute(
                    """
                    INSERT INTO [Indagini_Lineari] ([pkey_sln], [pkey_indln], [classe_ind], [tipo_ind], ID_INDLN,
                    [id_indlnex], [arch_ex], [note_indln], [data_ind], [doc_pag], [doc_ind]) VALUES(?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?)""",
                    (
                        row[0],
                        row[1],
                        row[2],
                        row[3],
                        row[4],
                        row[5],
                        row[6],
                        row[7],
                        self._validate_date(row[8]),  # data_ind
                        row[9],
                        row[10],
                    ),
                )
                self.commit()
            except Exception as e:
                self.log(f"Error inserting indagine {row[4]}: {row} - {e}", log_level=2)
                insert_errors.append((row[4], e))
                continue
        return insert_errors

    def insert_parametri_lineari(self, data):
        """Insert 'parametri_lineari' data into the database."""
        insert_errors = []
        for row in data:
            try:
                self.cursor.execute(
                    """
                    INSERT INTO [Parametri_Lineari] ([pkey_indln], [pkey_parln], [tipo_parln], ID_PARLN, [prof_top],
                    [prof_bot], [spessore], [quota_slm_top], [quota_slm_bot], [valore], [attend_mis], [note_par],
                    [data_par]) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        row[0],
                        row[1],
                        row[2],
                        row[3],
                        row[4],
                        row[5],
                        row[6],
                        row[7],
                        row[8],
                        row[9],
                        row[10],
                        row[11],
                        self._validate_date(row[12]),  # data_par
                    ),
                )
                self.commit()
            except Exception as e:
                self.log(f"Error inserting parametro {row[3]}: {row} - {e}", log_level=2)
                insert_errors.append((row[3], e))
                continue
        return insert_errors

    def insert_metadata(self, data):
        """Insert 'metadata' data into the database."""
        insert_errors = []
        for row in data:
            try:
                self.cursor.execute(
                    """
                    INSERT INTO [Metadati] (id_metadato, liv_gerarchico, resp_metadato_nome, resp_metadato_email,
                    resp_metadato_sito, data_metadato, srs_dati, proprieta_dato_nome, proprieta_dato_email,
                    proprieta_dato_sito, data_dato, ruolo, desc_dato, formato, tipo_dato, contatto_dato_nome,
                    contatto_dato_email, contatto_dato_sito, keywords, keywords_inspire, limitazione, vincoli_accesso,
                    vincoli_fruibilita, vincoli_sicurezza, scala, categoria_iso, estensione_ovest, estensione_est,
                    estensione_sud, estensione_nord, formato_dati, distributore_dato_nome, distributore_dato_telefono,
                    distributore_dato_email, distributore_dato_sito, url_accesso_dato, funzione_accesso_dato,
                    precisione, genealogia) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row[0],
                        row[1],
                        row[2],
                        row[3],
                        row[4],
                        self._validate_date(row[5]),  # data_metadato
                        row[6],
                        row[7],
                        row[8],
                        row[9],
                        self._validate_date(row[10]),  # data_dato
                        row[11],
                        row[12],
                        row[13],
                        row[14],
                        row[15],
                        row[16],
                        row[17],
                        row[18],
                        row[19],
                        row[20],
                        row[21],
                        row[22],
                        row[23],
                        row[24],
                        row[25],
                        row[26],
                        row[27],
                        row[28],
                        row[29],
                        row[30],
                        row[31],
                        row[32],
                        row[33],
                        row[34],
                        row[35],
                        row[36],
                        self._validate_float(row[37]),  # precisione
                        row[38],
                    ),
                )
                self.commit()
            except Exception as e:
                self.log(f"Error inserting metadata {row[0]}: {row} - {e}", log_level=2)
                insert_errors.append((row[0], e))
                continue
        return insert_errors


class MdbAuthError(Exception):
    pass


class JVMError(Exception):
    pass


class JavaVersionError(Exception):
    pass
