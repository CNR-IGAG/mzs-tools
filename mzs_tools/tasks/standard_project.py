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

"""Helpers to inspect "standard" SM projects (shapefiles and CdI_Tabelle survey data), without Qt widgets."""

from pathlib import Path

from ..plugin_utils.logging import MzSToolsLogger
from ..plugin_utils.misc import get_path_for_name

# CSV/TXT file prefixes, in order of dependency
PUNTUALI_CSV_SERIES = ["sito_puntuale", "indagini_puntuali", "parametri_puntuali", "curve"]
LINEARI_CSV_SERIES = ["sito_lineare", "indagini_lineari", "parametri_lineari"]


def build_standard_project_paths(input_dir: Path) -> dict:
    """Find the layers and files of a standard project.

    Each entry is ``{"parent": <parent folder name or None>, "path": <Path or None>}``, plus ``"table"`` (the
    destination table name) for the shapefiles that can be imported in a MzS Tools project.
    """
    paths = {
        "GeoTec": {"parent": None, "path": None},
        "Elineari.shp": {"parent": "GeoTec", "path": None, "table": "elineari"},
        "Epuntuali.shp": {"parent": "GeoTec", "path": None, "table": "epuntuali"},
        "Forme.shp": {"parent": "GeoTec", "path": None, "table": "forme"},
        "Geotec.shp": {"parent": "GeoTec", "path": None, "table": "geotec"},
        "Geoidr.shp": {"parent": "GeoTec", "path": None, "table": "geoidr"},
        "Instab_geotec.shp": {"parent": "GeoTec", "path": None, "table": "instab_geotec"},
        "Indagini": {"parent": None, "path": None},
        "Documenti": {"parent": "Indagini", "path": None},
        "CdI_Tabelle.mdb": {"parent": "Indagini", "path": None},
        "CdI_Tabelle.sqlite": {"parent": "Indagini", "path": None},
        "Ind_pu.shp": {"parent": "Indagini", "path": None},
        "Ind_ln.shp": {"parent": "Indagini", "path": None},
        "MS1": {"parent": None, "path": None},
        "MS1-Instab.shp": {"parent": "MS1", "path": None, "table": "instab_l1"},
        "MS1-Isosub.shp": {"parent": "MS1", "path": None, "table": "isosub_l1"},
        "MS1-Stab.shp": {"parent": "MS1", "path": None, "table": "stab_l1"},
        "MS23": {"parent": None, "path": None},
        "MS23-Instab.shp": {"parent": "MS23", "path": None, "table": "instab_l23"},
        "MS23-Isosub.shp": {"parent": "MS23", "path": None, "table": "isosub_l23"},
        "MS23-Stab.shp": {"parent": "MS23", "path": None, "table": "stab_l23"},
        "Spettri": {"parent": "MS23", "path": None},
        "Plot": {"parent": None, "path": None},
    }

    for name, data in paths.items():
        parent_path = input_dir if not data["parent"] else input_dir / data["parent"]

        # if parent_path does not exist check for lower case name
        if not parent_path.exists():
            parent_path = parent_path.parent / str(parent_path.name).lower()

        data["path"] = get_path_for_name(parent_path, name.split("-")[1] if "-" in name else name)

    return paths


def find_csv_files(csv_dir: Path) -> dict:
    """Find the survey data CSV/TXT files in csv_dir.

    Files are matched by lower-case name prefix; for each series the search stops at the first missing file in the
    dependency chain.

    Returns:
        ``{"puntuali": {prefix: Path}, "lineari": {prefix: Path}}``
    """
    all_files = []
    all_file_paths = {}
    for ext in ["*.csv", "*.txt"]:
        for file_path in csv_dir.glob(ext):
            lowercase_name = file_path.name.lower()
            all_files.append(lowercase_name)
            all_file_paths[lowercase_name] = file_path

    MzSToolsLogger.log(f"Files found in CSV directory: {all_files}", log_level=4)

    found_files: dict[str, dict[str, Path]] = {"puntuali": {}, "lineari": {}}

    sito_puntuale_file = next((f for f in all_files if f.startswith("sito_puntuale")), None)
    if sito_puntuale_file:
        found_files["puntuali"]["sito_puntuale"] = all_file_paths[sito_puntuale_file]
        for file_prefix in PUNTUALI_CSV_SERIES[1:]:
            found_file = next((f for f in all_files if f.startswith(file_prefix)), None)
            if found_file:
                found_files["puntuali"][file_prefix] = all_file_paths[found_file]
            else:
                MzSToolsLogger.log(f"Missing file: {file_prefix}", log_level=1)
                break  # Stop when a file in the dependency chain is missing

    sito_lineare_file = next((f for f in all_files if f.startswith("sito_lineare")), None)
    if sito_lineare_file:
        found_files["lineari"]["sito_lineare"] = all_file_paths[sito_lineare_file]
        for file_prefix in LINEARI_CSV_SERIES[1:]:
            found_file = next((f for f in all_files if f.startswith(file_prefix)), None)
            if found_file:
                found_files["lineari"][file_prefix] = all_file_paths[found_file]
            else:
                break  # Stop when a file in the dependency chain is missing

    return found_files
