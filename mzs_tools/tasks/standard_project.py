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

"""Helpers to read and write "standard" SM projects (shapefiles and CdI_Tabelle survey data), without Qt widgets."""

import logging
import shutil
from datetime import datetime
from pathlib import Path

from qgis.core import QgsField, QgsVectorLayer, edit
from qgis.PyQt import QtCore
from qgis.PyQt.QtCore import QMetaType

from ..__about__ import DIR_PLUGIN_ROOT
from ..core.constants import STANDARD_SHAPEFILES_INT_FIELDS
from ..core.mzs_project_manager import MzSProjectManager
from ..plugin_utils.logging import MzSToolsLogger
from ..plugin_utils.misc import get_path_for_name

# the logger the export tasks write to
EXPORT_LOGGER_NAME = "mzs_tools.tasks.export_data"

STANDARD_EXPORT_VERSION = "S42"
CDI_TABELLE_MDB_TEMPLATE = "CdI_Tabelle_4.2.mdb"

# folders of an exported standard project
STANDARD_EXPORT_SUBDIRS = (
    "BasiDati",
    "GeoTec",
    "Indagini",
    "Indagini/Documenti",
    "MS1",
    "MS23",
    "MS23/Spettri",
    "Plot",
    "Progetti",
    "Vestiture",
)

# table → (shapefile path relative to the exported project, layer role)
STANDARD_SHAPEFILE_EXPORTS: dict[str, tuple[str, str]] = {
    "comuni": ("BasiDati/comuni_istat.shp", "base"),
    "comune_progetto": ("BasiDati/comune_progetto.shp", "base"),
    "elineari": ("GeoTec/Elineari.shp", "editing"),
    "epuntuali": ("GeoTec/Epuntuali.shp", "editing"),
    "forme": ("GeoTec/Forme.shp", "editing"),
    "geoidr": ("GeoTec/Geoidr.shp", "editing"),
    "geotec": ("GeoTec/Geotec.shp", "editing"),
    "instab_geotec": ("GeoTec/Instab_geotec.shp", "editing"),
    "sito_puntuale": ("Indagini/Ind_pu.shp", "editing"),
    "sito_lineare": ("Indagini/Ind_ln.shp", "editing"),
    "instab_l1": ("MS1/Instab.shp", "editing"),
    "isosub_l1": ("MS1/Isosub.shp", "editing"),
    "stab_l1": ("MS1/Stab.shp", "editing"),
    "instab_l23": ("MS23/Instab.shp", "editing"),
    "isosub_l23": ("MS23/Isosub.shp", "editing"),
    "stab_l23": ("MS23/Stab.shp", "editing"),
}

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


def create_standard_export_folder(
    output_dir: Path,
    cod_istat: str,
    comune_name: str,
    indagini_format: str,
    standard_version: str,
    mdb_template: str,
) -> Path:
    """Create the folder structure of an exported standard project in output_dir and copy the CdI_Tabelle template.

    The folder is named <cod_istat>_<Comune>_<standard_version>_Shapefile; a timestamp is appended if it already
    exists. output_dir must exist.

    Args:
        indagini_format: "mdb" or "sqlite".
        mdb_template: file name of the CdI_Tabelle Access template, in the plugin data directory.

    Returns:
        The path of the created folder.
    """
    folder_name = f"{cod_istat}_{MzSProjectManager.sanitize_comune_name(comune_name)}_{standard_version}_Shapefile"
    exported_project_path = output_dir / folder_name
    if exported_project_path.exists():
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        exported_project_path = output_dir / f"{folder_name}_{timestamp}"

    exported_project_path.mkdir(parents=True, exist_ok=False)
    for ms_path in STANDARD_EXPORT_SUBDIRS:
        (exported_project_path / ms_path).mkdir(parents=True)

    # copy the db template file to the output directory
    if indagini_format == "mdb":
        shutil.copy(DIR_PLUGIN_ROOT / "data" / mdb_template, exported_project_path / "Indagini" / "CdI_Tabelle.mdb")
    elif indagini_format == "sqlite":
        shutil.copy(
            DIR_PLUGIN_ROOT / "data" / "CdI_Tabelle.sqlite", exported_project_path / "Indagini" / "CdI_Tabelle.sqlite"
        )

    return exported_project_path


def postprocess_exported_shapefile(table_name: str, path: Path) -> None:
    """Fix the field types and values of a shapefile exported from the table_name layer, as required by the
    SM Standards."""
    logging.getLogger(EXPORT_LOGGER_NAME).info(f"Exported {table_name} to {path}")

    # workaround for QgsVectorLayerExporter always exporting integer fields as float
    for layer_name, fields in STANDARD_SHAPEFILES_INT_FIELDS.items():
        if table_name == layer_name:
            layer = QgsVectorLayer(str(path), str(path.stem), "ogr")
            for field_name in fields:
                try:
                    change_field_type(layer, field_name, QMetaType.Type.Int)
                except TypeError:
                    # QGIS < 3.38: use QVariant.Type
                    change_field_type(layer, field_name, QtCore.QVariant.Int)  # type: ignore
            break

    # modify specific datasets
    if table_name == "sito_puntuale":
        rename_field(QgsVectorLayer(str(path), str(path.stem), "ogr"), "id_spu", "ID_SPU")
    elif table_name == "sito_lineare":
        rename_field(QgsVectorLayer(str(path), str(path.stem), "ogr"), "id_sln", "ID_SLN")
    elif table_name in ["stab_l1", "stab_l23", "instab_l1", "instab_l23"]:
        # for some absurd reason, the field "LIVELLO" must be a float
        try:
            change_field_type(QgsVectorLayer(str(path), str(path.stem), "ogr"), "LIVELLO", QMetaType.Type.Double)
        except TypeError:
            # QGIS < 3.38: use QVariant.Type
            change_field_type(
                QgsVectorLayer(str(path), str(path.stem), "ogr"),
                "LIVELLO",
                QtCore.QVariant.Double,  # type: ignore
            )
        if table_name in ["stab_l23", "instab_l23"]:
            # extract file name from path "SPETTRI"
            extract_file_name_from_path(QgsVectorLayer(str(path), str(path.stem), "ogr"), "SPETTRI")


def rename_field(layer: QgsVectorLayer, field_name: str, new_name: str):
    for field in layer.fields():
        if field.name() == field_name:
            logging.getLogger(EXPORT_LOGGER_NAME).debug(f"Renaming {field.name()} to {new_name}")
            with edit(layer):
                layer.renameAttribute(layer.fields().lookupField(field_name), new_name)
            break


def change_field_type(layer, field_name, field_type) -> bool:
    """Change the data type of a field in a vector layer."""
    logger = logging.getLogger(EXPORT_LOGGER_NAME)
    logger.debug(f"Changing field type for field '{field_name}'")

    field_idx = layer.fields().lookupField(field_name)
    if field_idx == -1:
        logger.error(f"Field '{field_name}' not found in layer")
        return False

    temp_field_name = "temp"

    temp_field = QgsField()
    temp_field.setName(temp_field_name)
    temp_field.setType(field_type)

    new_field = QgsField()
    new_field.setName(field_name)
    new_field.setType(field_type)

    with edit(layer):
        layer.addAttribute(temp_field)
        layer.updateFields()
        temp_field_idx = layer.fields().lookupField(temp_field_name)
        for feature in layer.getFeatures():
            layer.changeAttributeValue(feature.id(), temp_field_idx, feature[field_name])

    with edit(layer):
        layer.deleteAttribute(field_idx)
        layer.updateFields()
        layer.addAttribute(new_field)
        layer.updateFields()
        new_field_idx = layer.fields().lookupField(field_name)
        temp_field_idx = layer.fields().lookupField(temp_field_name)
        for feature in layer.getFeatures():
            layer.changeAttributeValue(feature.id(), new_field_idx, feature[temp_field_name])
        layer.deleteAttribute(temp_field_idx)

    logger.debug(f"Successfully changed field type for '{field_name}'")
    return True


def extract_file_name_from_path(layer, field_name):
    """Extract file names from path strings stored in a specified field and
    replace the full paths with just the file names."""
    logger = logging.getLogger(EXPORT_LOGGER_NAME)
    logger.debug(f"Extracting file name from field '{field_name}'")

    field_idx = layer.fields().lookupField(field_name)
    if field_idx == -1:
        logger.error(f"Field '{field_name}' not found in layer")
        return

    layer.startEditing()
    features_updated = 0
    for feature in layer.getFeatures():
        path_value = feature[field_name]
        if not path_value:
            continue
        try:
            file_name = Path(path_value).name
            feature.setAttribute(field_idx, file_name)
            layer.updateFeature(feature)
            features_updated += 1
        except Exception as e:
            logger.error(f"Error extracting filename from '{path_value}': {str(e)}")

    success = layer.commitChanges()
    if success:
        logger.info(f"Successfully updated {features_updated} features in field '{field_name}'")
    else:
        logger.error(f"Failed to commit changes to layer: {layer.commitErrors()}")
        layer.rollBack()
