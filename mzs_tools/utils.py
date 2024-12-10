""" "Utilities for MzS Tools plugin

.. note:: This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

"""

import configparser
import datetime
import os
import sqlite3
from pathlib import Path
from typing import Dict, Optional

from qgis.core import (
    Qgis,
    QgsLayout,
    QgsLayoutExporter,
    QgsLayoutItemMap,
    QgsLayoutItemPage,
    QgsLayoutSize,
    QgsMessageLog,
    QgsProject,
    QgsUnitTypes,
)
from qgis.PyQt.QtCore import QRectF, QSize, QStandardPaths

# Constants for settings keys
SETTINGS_SECTION = "Settings"
AUTO_ADVANCED_EDITING_KEY = "auto_advanced_editing"


def save_map_image(image_path, zoom_to_layer, canvas):
    """Creates and saves a PNG image of the map canvas
    zoomed to the `zoom_to_layer` layer's extent.

    :param image_path: destination file path for the image
    :type image_path: str
    :param zoom_to_layer: vector layer for the map extent
    :type zoom_to_layer: QgsVectorLayer
    :param canvas: map canvas
    :type canvas: QgsMapCanvas
    """

    extent = zoom_to_layer.extent()
    canvas.setExtent(extent)

    p = QgsProject.instance()
    layout = QgsLayout(p)
    page = QgsLayoutItemPage(layout)
    page.setPageSize(QgsLayoutSize(1200, 700, QgsUnitTypes.LayoutMillimeters))
    collection = layout.pageCollection()
    collection.addPage(page)

    item_map = QgsLayoutItemMap(layout)
    item_map.attemptSetSceneRect(QRectF(0, 0, 1200, 700))
    item_map.setCrs(zoom_to_layer.crs())
    item_map.zoomToExtent(extent)
    layout.addItem(item_map)

    dpmm = 200 / 25.4
    width = int(dpmm * page.pageSize().width())
    height = int(dpmm * page.pageSize().height())

    size = QSize(width, height)
    exporter = QgsLayoutExporter(layout)
    image = exporter.renderPageToImage(0, size)
    image.save(image_path, "PNG")


def qgs_log(message, level="info"):
    """Log a MzSTools plugin message to the QGIS log panel.

    :param message: message to log
    :type message: str
    :param level: log level ('info', 'warning', 'error' - default is 'info')
    :type level: str
    """
    if level == "info":
        QgsMessageLog.logMessage(message, "MzSTools", level=Qgis.Info)
    elif level == "warning":
        QgsMessageLog.logMessage(message, "MzSTools", level=Qgis.Warning)
    elif level == "error":
        QgsMessageLog.logMessage(message, "MzSTools", level=Qgis.Critical)


def create_basic_sm_metadata(cod_istat, study_author=None, author_email=None):
    """Create a basic metadata record for a MzSTools project."""
    orig_gdb = QgsProject.instance().readPath(os.path.join("db", "indagini.sqlite"))
    conn = sqlite3.connect(orig_gdb)

    date_now = datetime.datetime.now().strftime(r"%d/%m/%Y")

    extent = QgsProject.instance().mapLayersByName("Comune del progetto")[0].dataProvider().extent()

    values = {
        "id_metadato": f"{cod_istat}M1",
        "liv_gerarchico": "series",
        "resp_metadato_nome": study_author,
        "resp_metadato_email": author_email,
        "data_metadato": date_now,
        "srs_dati": 32633,
        "ruolo": "owner",
        "formato": "mapDigital",
        "tipo_dato": "vector",
        "keywords": "Microzonazione Sismica, Pericolosita Sismica",
        "keywords_inspire": "Zone a rischio naturale, Geologia",
        "limitazione": "nessuna limitazione",
        "vincoli_accesso": "nessuno",
        "vincoli_fruibilita": "nessuno",
        "vincoli_sicurezza": "nessuno",
        "categoria_iso": "geoscientificInformation",
        "estensione_ovest": str(extent.xMinimum()),
        "estensione_est": str(extent.xMaximum()),
        "estensione_sud": str(extent.yMinimum()),
        "estensione_nord": str(extent.yMaximum()),
    }

    conn.execute(
        """
        INSERT INTO metadati (
            id_metadato, liv_gerarchico, resp_metadato_nome, resp_metadato_email, data_metadato, srs_dati, 
            ruolo, formato, tipo_dato, keywords, keywords_inspire, limitazione, vincoli_accesso, vincoli_fruibilita, 
            vincoli_sicurezza, categoria_iso, estensione_ovest, estensione_est, estensione_sud, estensione_nord
        ) VALUES (
            :id_metadato, :liv_gerarchico, :resp_metadato_nome, :resp_metadato_email, :data_metadato, :srs_dati, 
            :ruolo, :formato, :tipo_dato, :keywords, :keywords_inspire, :limitazione, :vincoli_accesso, :vincoli_fruibilita,
            :vincoli_sicurezza, :categoria_iso, :estensione_ovest, :estensione_est, :estensione_sud, :estensione_nord
        );
        """,
        values,
    )

    conn.commit()
    conn.close()


def plugin_version_from_metadata_file() -> Optional[str]:
    """Read the version from the metadata.txt file."""
    metadata_path = Path(__file__).parent / "metadata.txt"
    config = configparser.ConfigParser()
    config.read(metadata_path)
    if "general" in config and "version" in config["general"]:
        return config["general"]["version"]
    return None


def detect_mzs_tools_project() -> Optional[Dict[str, str]]:
    """Detect if the current project is a MzSTools project.

    :return: A dictionary with project info if it's a MzSTools project, None otherwise
    """
    project = QgsProject.instance()
    project_file_name = project.baseName()
    project_path = Path(project.absolutePath())
    db_path = project_path / "db" / "indagini.sqlite"
    version_file_path = project_path / "progetto" / "versione.txt"

    if project_file_name != "progetto_MS" or not db_path.exists() or not version_file_path.exists():
        return None

    with version_file_path.open("r") as f:
        version = f.read().strip()

    return {
        "project_path": str(project_path),
        "db_path": str(db_path),
        "version": version,
    }


def get_settings():
    """Retrieve settings from the .ini file."""
    config_file = Path(QStandardPaths.writableLocation(QStandardPaths.AppConfigLocation)) / "mzs_tools.ini"
    config = configparser.ConfigParser()
    settings = {}

    if not config_file.exists():
        # Create the config file with default settings
        config[SETTINGS_SECTION] = {AUTO_ADVANCED_EDITING_KEY: "True"}
        with config_file.open("w") as configfile:
            config.write(configfile)

    config.read(config_file)
    settings[AUTO_ADVANCED_EDITING_KEY] = config.getboolean(SETTINGS_SECTION, AUTO_ADVANCED_EDITING_KEY, fallback=True)

    return settings


def ensure_config_directory():
    """Ensure the configuration directory exists."""
    config_dir = Path(QStandardPaths.writableLocation(QStandardPaths.AppConfigLocation))
    config_dir.mkdir(parents=True, exist_ok=True)
