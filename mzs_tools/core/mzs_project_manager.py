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

import os
import shutil
import zipfile
from dataclasses import dataclass
from datetime import datetime
from functools import partial
from pathlib import Path
from typing import cast

from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsEditorWidgetSetup,
    QgsLayerDefinition,
    QgsLayerTreeGroup,
    QgsMapLayer,
    QgsPrintLayout,
    QgsProject,
    QgsReadWriteContext,
    QgsRelation,
    QgsSnappingConfig,
    QgsTolerance,
    QgsVectorLayer,
)
from qgis.gui import QgisInterface
from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtWidgets import QProgressBar
from qgis.PyQt.QtXml import QDomDocument
from qgis.utils import iface as _iface

from ..__about__ import DIR_PLUGIN_ROOT, __base_version__, __version__
from ..core.db_manager import DatabaseManager
from ..plugin_utils.logging import MzSToolsLogger
from ..plugin_utils.misc import save_map_image, save_map_image_direct
from ..plugin_utils.qt_compat import get_alignment_flag
from ..plugin_utils.settings import PlgOptionsManager
from .constants import (
    DB_MIGRATION_SCRIPTS,
    DEFAULT_BASE_LAYERS,
    DEFAULT_EDITING_LAYERS,
    DEFAULT_LAYOUT_GROUPS,
    DEFAULT_RELATIONS,
    DEFAULT_TABLE_LAYERS_NAMES,
    NO_OVERLAPS_LAYER_GROUPS,
    PRINT_LAYOUT_MODELS,
    REMOVED_EDITING_LAYERS,
)

# Properly typed iface for better type checking
iface: QgisInterface = cast(QgisInterface, _iface)


@dataclass
class ComuneData:
    cod_regio: str
    cod_prov: str
    cod_com: str
    comune: str
    provincia: str
    regione: str
    cod_istat: str


class MzSProjectManager:
    """Singleton class to manage MzS Tools project data and structure. It provides various functionalities to handle
    project initialization, database connections, layer management, and project customization."""

    _instance = None

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        if MzSProjectManager._instance is not None:
            raise Exception("This class is a singleton!")
        else:
            MzSProjectManager._instance = self

        self.log = MzSToolsLogger().log

        self.current_project: QgsProject | None = None
        self.project_path: Path | None = None
        self.project_version: str | None = None
        self.project_updateable = False
        self.db_path: Path | None = None

        # Database manager
        self.db_manager = None

        self.comune_data: ComuneData | None = None
        self.project_metadata = None
        self.required_layer_registry = {}
        self.project_issues = None

        self.is_mzs_project: bool = False

    @property
    def db(self) -> DatabaseManager:
        """Get database manager with validation.

        Returns:
            DatabaseManager: The active database manager instance

        Raises:
            RuntimeError: If database manager is not initialized or not connected

        Example:
            # Instead of checking manually:
            if self.db_manager and self.db_manager.is_connected():
                self.db_manager.execute_query(...)

            # Just use:
            self.db.execute_query(...)  # Raises if not ready
        """
        if not self.db_manager:
            self.log("Database manager not initialized", log_level=2)
            raise RuntimeError("Database manager not initialized")
        if not self.db_manager.is_connected():
            self.log("Database is not connected", log_level=2)
            raise RuntimeError("Database is not connected")
        return self.db_manager

    def init_manager(self):
        """Detect if the current project is a MzS Tools project and setup the manager."""
        self.current_project = QgsProject.instance()

        # be careful using Path with QgsProject functions such as absolutePath(), fileName(), baseName(), etc.
        # when clicking on New Project these functions will return empty strings but Path.resolve() will return
        # the paths relative to the last opened project!
        project_path_str = self.current_project.absolutePath()
        self.log(f"Current project path: {project_path_str}", log_level=4)
        db_path = Path(project_path_str) / "db" / "indagini.sqlite"

        # TODO: better project detection
        # if project_file_name != "progetto_MS" or not db_path.exists() or not version_file_path.exists():
        if not project_path_str or not db_path.exists():
            self.log("No MzS Tools project detected", log_level=4)
            self.is_mzs_project = False
            self.project_path = None
            self.db_path = None
            # self.db_connection = None
            self.db_manager = None
            self.project_updateable = False
            self.project_issues = None
            return False

        self.is_mzs_project = True

        self.project_path = Path(project_path_str)
        self.db_path = db_path

        # setup db connection and save it to the manager
        connected = self._setup_db_connection()
        if not connected:
            return False

        # cleanup db connection on project close
        self.current_project.cleared.connect(self.cleanup_db_connection)

        # load metadata from db if exists
        # self.sm_project_metadata = self.get_sm_project_metadata()

        # check project structure
        self.check_project_structure()

        # keep track of connected layers to avoid reconnecting signals
        self.editing_signals_connected_layers = {}

        self.log(f"MzS Tools project version {self.project_version} detected. Manager initialized.")

    def _add_project_issue(
        self,
        issue_type: str,
        issue: str,
        trace: str | None = None,
        log: bool = True,
    ) -> None:
        """Store a project issue in the internal registry.

        Args:
            issue_type: Category of the issue (e.g. "project", "layers", "db").
            issue: Human readable description of the issue.
            tb: Optional traceback or extra diagnostic information appended on a new line.
            log: If True the issue is logged immediately.
        """
        # Lazily initialize the issues dictionary if it is not yet available
        if self.project_issues is None:
            self.project_issues = {}

        issues_list = self.project_issues.setdefault(issue_type, [])
        if trace:
            issue = f"{issue}\n{trace}"
        issues_list.append(issue)
        if log:
            self.log(f"Project issue found: {issue_type} - {issue}", log_level=2)

    def check_project_structure(self):
        # init project issues dict
        self.project_issues = {}

        # check project version
        if self.project_path is None:
            self._add_project_issue("project", "Project path is not set")
            return

        version_file_path = self.project_path / "progetto" / "versione.txt"
        try:
            with version_file_path.open("r") as f:
                self.project_version = f.read().strip()
        except Exception as e:
            # self.log(f"Error reading project version: {e}", log_level=2)
            # self.project_issues["general"].append("Error reading project version file")
            self._add_project_issue("project", f"Error reading project version file: {e}")

        self.project_updateable = bool(self.project_version and self.project_version < __base_version__)
        if self.project_updateable:
            self.log(
                f"MzS Project is version {self.project_version} and should be updated to version {__base_version__}",
                log_level=1,
            )

        # get comune data from db
        self.comune_data = self.get_project_comune_data()
        if not self.comune_data:
            self._add_project_issue("db", "Error reading comune data from project db")

        # check required layers
        self.required_layer_registry = self._build_required_layers_registry()

        # check relations
        self._check_default_project_relations()

    def connect_editing_signals(self):
        """connect editing signals to automatically set advanced overlap config for configured layer groups"""
        for group in NO_OVERLAPS_LAYER_GROUPS:
            for table_name in group:
                layer_id = self.find_layer_by_table_name_role(table_name, "editing")
                if not layer_id:
                    continue
                layer = self.current_project.mapLayer(layer_id)
                # Ensure we only proceed with vector layers (satisfies type checker)
                if not isinstance(layer, QgsVectorLayer):
                    continue
                if layer not in self.editing_signals_connected_layers:
                    layer.editingStarted.connect(partial(self.set_advanced_editing_config, layer, table_name))
                    layer.editingStopped.connect(self.reset_advanced_editing_config)
                    self.editing_signals_connected_layers[layer] = (
                        self.set_advanced_editing_config,
                        self.reset_advanced_editing_config,
                    )

    def set_advanced_editing_config(self, layer: QgsVectorLayer, table_name: str):
        auto_advanced_editing_setting = PlgOptionsManager.get_value_from_key(
            "auto_advanced_editing", default=True, exp_type=bool
        )
        if not auto_advanced_editing_setting:
            return

        self.log("Setting advanced editing options")

        # TODO: config in plugin options? groups, snapping tolerance, etc.

        # stop editing for any layer in any NO_OVERLAPS_LAYER_GROUPS if it's already in editing mode
        # and populate the editing_group_layers list
        current_layer_id = layer.id()
        editing_group_layers = []
        for layer_group in NO_OVERLAPS_LAYER_GROUPS:
            layer_ids = [self.find_layer_by_table_name_role(t_name, "editing") for t_name in layer_group]
            for layer_id in layer_ids:
                ly = self.current_project.mapLayer(layer_id)
                if ly is None or not isinstance(ly, QgsVectorLayer):
                    continue
                if table_name in layer_group:
                    editing_group_layers.append(ly)
                if ly.id() != current_layer_id and ly.isEditable():
                    self.log(f"Stopping editing for {ly.name()}", log_level=4)
                    ly.commitChanges(stopEditing=True)

        # save the current config
        self.proj_snapping_config = self.current_project.snappingConfig()
        self.proj_avoid_intersections_layers = self.current_project.avoidIntersectionsLayers()
        self.topological_editing = self.current_project.topologicalEditing()
        self.avoid_intersections_mode = self.current_project.avoidIntersectionsMode()

        # just fail gracefully if something goes wrong
        try:
            snapping_config = QgsSnappingConfig(self.proj_snapping_config)

            # snapping_config.clearIndividualLayerSettings()

            # Pylance complains because the QGIS Python type stubs do not expose the nested enum QgsSnappingConfig.SnappingMode.*.
            # Runtime works, but static analysis cannot find SnappingMode, so it flags it.
            # In QGIS < 3.26 the enum values are exported directly as class attributes
            # (QgsSnappingConfig.AdvancedConfiguration, AllLayers, ActiveLayer) instead of under a SnappingMode namespace.
            snapping_config.setEnabled(True)
            try:
                snapping_config.setMode(QgsSnappingConfig.SnappingMode.AdvancedConfiguration)  # type: ignore[attr-defined]
            except AttributeError:
                snapping_config.setMode(QgsSnappingConfig.AdvancedConfiguration)  # type: ignore[attr-defined]
            snapping_config.setIntersectionSnapping(True)
            snapping_config.setTolerance(20)

            # deprecated constructor:
            # layer_settings = QgsSnappingConfig.IndividualLayerSettings(
            #     True,
            #     QgsSnappingConfig.SnappingTypes.VertexFlag,
            #     20,
            #     QgsTolerance.UnitType.ProjectUnits,
            # )
            layer_settings = snapping_config.individualLayerSettings(layer)
            layer_settings.setEnabled(True)
            layer_settings.setTypeFlag(Qgis.SnappingType.Vertex)
            layer_settings.setTolerance(20)
            try:
                layer_settings.setUnits(Qgis.MapToolUnit.Project)
            except AttributeError:
                # QGIS < 3.32
                layer_settings.setUnits(QgsTolerance.ProjectUnits)  # type: ignore

            for ly in editing_group_layers:
                snapping_config.setIndividualLayerSettings(ly, layer_settings)
            self.current_project.setAvoidIntersectionsLayers(editing_group_layers)

            # actually set "follow advanced config" for overlaps
            self.current_project.setAvoidIntersectionsMode(Qgis.AvoidIntersectionsMode.AvoidIntersectionsLayers)

            # enable topological editing
            self.current_project.setTopologicalEditing(True)

            # apply the new config
            self.current_project.setSnappingConfig(snapping_config)

        except Exception as e:
            self.log(f"Error setting advanced editing config: {e}", log_level=2)

    def reset_advanced_editing_config(self):
        auto_advanced_editing_setting = PlgOptionsManager.get_value_from_key(
            "auto_advanced_editing", default=True, exp_type=bool
        )
        if not auto_advanced_editing_setting:
            return

        self.log("Resetting advanced editing settings")

        try:
            self.current_project.setSnappingConfig(self.proj_snapping_config)
            self.current_project.setAvoidIntersectionsMode(self.avoid_intersections_mode)
            self.current_project.setAvoidIntersectionsLayers(self.proj_avoid_intersections_layers)
            self.current_project.setTopologicalEditing(self.topological_editing)
        except Exception as e:
            self.log(f"Error resetting advanced editing config: {e}", log_level=2)

    def disconnect_editing_signals(self):
        """Disconnect specific editing signals."""
        for layer, (start_func, stop_func) in self.editing_signals_connected_layers.items():
            layer.editingStarted.disconnect(start_func)
            layer.editingStopped.disconnect(stop_func)
        self.editing_signals_connected_layers.clear()

    def _build_required_layers_registry(self):
        table_layer_map = {}
        # search the editing layers
        for table_name, layer_data in DEFAULT_EDITING_LAYERS.items():
            if layer_data["role"] == "editing" and layer_data["type"] not in ["group", "service_group"]:
                # layer_id = self.find_layer_by_table_name_role(table_name, "editing")
                layers = self.find_layers_by_table_name(table_name)
                valid_layers = [
                    layer for layer in layers if layer and layer.customProperty("mzs_tools/layer_role") == "editing"
                ]

                if not valid_layers:
                    msg = f"No 'editing' layers found for table '{table_name}'"
                    self._add_project_issue("layers", msg)
                elif len(valid_layers) > 1:
                    msg = f"Multiple 'editing' layers found for table '{table_name}'"
                    self._add_project_issue("layers", msg)
                else:
                    table_layer_map[table_name] = valid_layers[0].id()

        # search the lookup tables
        for table_name in DEFAULT_TABLE_LAYERS_NAMES:
            # layer_id = self.find_layer_by_table_name_role(table_name, "editing")
            layers = self.find_layers_by_table_name(table_name)
            valid_layers = [
                layer for layer in layers if layer and layer.customProperty("mzs_tools/layer_role") == "editing"
            ]
            if not valid_layers:
                msg = f"No 'editing' layers found for lookup table '{table_name}'"
                self._add_project_issue("layers", msg)
            elif len(valid_layers) > 1:
                msg = f"Multiple 'editing' layers found for lookup table '{table_name}'"
                self._add_project_issue("layers", msg)
            else:
                table_layer_map[table_name] = valid_layers[0].id()

        # search the base layers (comuni, comune_progetto)
        for table_name, layer_data in DEFAULT_BASE_LAYERS.items():
            if layer_data["role"] == "base" and layer_data["type"] not in ["group", "service_group"]:
                layer_id = self.find_layer_by_table_name_role(table_name, "base")
                if layer_id:
                    table_layer_map[table_name] = layer_id

        return table_layer_map

    # def _set_form_ui_file(self, layer: QgsVectorLayer, table_name: str):
    #     form_config = layer.editFormConfig()
    #     current_ui_path = form_config.uiForm()
    #     if not current_ui_path:
    #         return False
    #     # check if the file exists
    #     current_ui_path = Path(current_ui_path)
    #     if not current_ui_path.exists():
    #         ui_path = DIR_PLUGIN_ROOT / "editing" / f"{table_name}.ui"
    #         self.log(
    #             f"UI form file '{current_ui_path}' for layer {layer.name()} does not exist. Setting new file: '{ui_path}'",
    #             log_level=1,
    #         )
    #         form_config.setUiForm(str(ui_path.absolute()))
    #         layer.setEditFormConfig(form_config)
    #     return True

    @staticmethod
    def set_project_layer_capabilities(
        layer: QgsMapLayer, identifiable=True, required=False, searchable=True, private=False
    ):
        """
        Set QgsMapLayer.LayerFlag(s) for a layer, as in Project Properties - Data Sources
        The "Read Only" status must be set with layer.setReadOnly() and is not a QgsMapLayer.LayerFlag

        Flags:
        - Identifiable = 1
        - Removable = 2
        - Searchable = 4
        - Private = 8
        """
        # https://gis.stackexchange.com/questions/318506/setting-layer-identifiable-seachable-and-removable-with-python-in-qgis-3
        flags = 0
        if identifiable:
            flags += QgsMapLayer.LayerFlag.Identifiable
        if searchable:
            flags += QgsMapLayer.LayerFlag.Searchable
        if not required:
            flags += QgsMapLayer.LayerFlag.Removable
        if private:
            flags += QgsMapLayer.LayerFlag.Private

        layer.setFlags(QgsMapLayer.LayerFlag(flags))

    def set_layer_custom_property(self, layer: QgsMapLayer, property_name: str, property_value: str):
        if layer:
            self.log(
                f"Setting custom property 'mzs_tools/{property_name}': '{property_value}' for layer {layer.name()}",
                log_level=4,
            )
            layer.setCustomProperty(f"mzs_tools/{property_name}", property_value)

    # def _set_custom_layer_properties(self):
    #     """only for testing"""
    #     self._set_custom_layer_properties_for_group(DEFAULT_BASE_LAYERS, {"layer_role": "base"})
    #     self._set_custom_layer_properties_for_group(DEFAULT_EDITING_LAYERS, {"layer_role": "editing"})

    #     # set properties for lookup tables
    #     for table_name in DEFAULT_TABLE_LAYERS_NAMES:
    #         layers = self.find_layers_by_table_name(table_name)
    #         for layer in layers:
    #             self.set_layer_custom_property(layer, "layer_role", "editing")

    #     self._set_custom_layer_properties_for_group(DEFAULT_LAYOUT_GROUPS, {"layer_role": "layout"})

    # def _set_custom_layer_properties_for_group(self, group_dict: dict, custom_properties: dict):
    #     """only for testing"""
    #     for table_name, layer_data in group_dict.items():
    #         if type(layer_data) is dict and layer_data["role"] not in ["group", "service_group"]:
    #             layers = self.find_layers_by_table_name(table_name)
    #             for layer in layers:
    #                 for prop_name, prop_value in custom_properties.items():
    #                     self.set_layer_custom_property(layer, prop_name, prop_value)
    #         elif type(layer_data) is str:
    #             group = self.current_project.layerTreeRoot().findGroup(table_name)
    #             if group:
    #                 for layer_node in group.findLayers():
    #                     map_layer = layer_node.layer()
    #                     if map_layer is None:
    #                         continue  # skip missing layer
    #                     for prop_name, prop_value in custom_properties.items():
    #                         self.set_layer_custom_property(map_layer, prop_name, prop_value)

    def add_default_layers(self, add_base_layers=True, add_editing_layers=True, add_layout_groups=True):
        """Add the default layers to the project, removing first any existing layers of the
           same category (base, editing or layout) pointing to the same database tables.

        Args:
            add_base_layers (bool, optional): Add the default base layers. Defaults to True.
            add_editing_layers (bool, optional): Add the default editing layers. Defaults to True.
            add_layout_groups (bool, optional): Add the default layout layers. Defaults to True.
        """
        if not add_base_layers and not add_editing_layers and not add_layout_groups:
            return
        if add_base_layers:
            self._cleanup_base_layers()
            self.log("Adding default base layers")
            self._add_default_layer_group(DEFAULT_BASE_LAYERS, "Cartografia di base")
        if add_layout_groups:
            self._cleanup_layout_groups()
            self.log("Adding default layout groups")
            self._add_default_layout_groups("LAYOUT DI STAMPA")
        if add_editing_layers:
            self._cleanup_editing_layers()
            self.log("Adding default editing layers")
            self._add_default_layer_group(DEFAULT_EDITING_LAYERS, "BANCA DATI GEOGRAFICA")
            self._add_default_value_relations(DEFAULT_EDITING_LAYERS)
            self._add_default_project_relations()
            # the project must be reloaded after adding the default relations to refresh the relation editor widgets
            # self.current_project.write()
            # iface.addProject(str(self.current_project.absoluteFilePath()))

        # remove empty groups from root
        empty_groups = [group for group in self.current_project.layerTreeRoot().children() if group.children() == []]
        for group in empty_groups:
            self.current_project.layerTreeRoot().removeChildNode(group)

    def _add_default_layer_group(self, group_dict: dict, group_name: str):
        # create new group layer
        root_layer_group = QgsLayerTreeGroup(group_name)
        root_layer_group.setItemVisibilityChecked(False)
        self.current_project.layerTreeRoot().insertChildNode(0, root_layer_group)

        for _table_name, layer_data in group_dict.items():
            layer_group = None
            if layer_data["group"]:
                layer_group = root_layer_group.findGroup(layer_data["group"])
                if layer_group is None:
                    layer_group = QgsLayerTreeGroup(layer_data["group"])
                    layer_group.setItemVisibilityChecked(False)
                    root_layer_group.addChildNode(layer_group)
            qlr_full_path = DIR_PLUGIN_ROOT / "data" / "layer_defs" / layer_data["qlr_path"]
            layer_added = self.add_layer_from_qlr(
                layer_group if layer_group is not None else root_layer_group, qlr_full_path
            )
            if not layer_added or layer_data["group"] == "service_group":
                continue

            # set the data source and layer options for the newly added layer
            # other layers with the same name might be present in the project in other groups,
            # so `self.current_project.mapLayersByName()` might return more than one layer
            for layer_tree_layer in root_layer_group.findLayers():
                if (
                    layer_tree_layer.name() == layer_data["layer_name"]
                    or layer_tree_layer.parent().name() == layer_data["layer_name"]
                ):
                    # self.log(f"Setting data source for layer: {layer_tree_layer.name()}")
                    # uri = QgsDataSourceUri()
                    # uri.setDatabase(str(self.db_path))
                    # schema = ""
                    # if layer_data["type"] == "vector" and "geom_name" in layer_data:
                    #     geom_column = layer_data["geom_name"]
                    # elif layer_data["type"] == "vector":
                    #     geom_column = "geom"
                    # else:
                    #     geom_column = None
                    # uri.setDataSource(
                    #     schema, table_name if layer_data["type"] != "group" else layer_tree_layer.name(), geom_column
                    # )
                    # layer_tree_layer.layer().setDataSource(
                    #     uri.uri(),
                    #     layer_data["layer_name"] if layer_data["type"] == "vector" else layer_tree_layer.name(),
                    #     "spatialite",
                    # )

                    # set .ui files and editing functions for editing layers
                    # layer = layer_tree_layer.layer()
                    # if layer_data["role"] == "editing":
                    #     form_config = layer.editFormConfig()
                    #     # ui_path = DIR_PLUGIN_ROOT / "editing" / f"{table_name}.ui"
                    #     # self.log(f"Setting UI form for layer {layer.name()}: {ui_path}")
                    #     # form_config.setUiForm(str(ui_path))

                    #     try:
                    #         # QGIS >= 3.32
                    #         form_config.setInitCodeSource(Qgis.AttributeFormPythonInitCodeSource.Dialog)
                    #     except:
                    #         # QGIS < 3.32
                    #         form_config.setInitCodeSource(QgsEditFormConfig.CodeSourceDialog)

                    #     form_config.setInitFunction(f"{table_name}_form_init")
                    #     form_config.setInitCode(f"from mzs_tools import {table_name}_form_init")

                    #     layer.setEditFormConfig(form_config)

                    # set subset string if needed
                    map_layer = layer_tree_layer.layer()
                    subset_string = layer_data.get("subset_string", None)
                    if (
                        subset_string is not None
                        and subset_string == "cod_regio"
                        and isinstance(map_layer, QgsVectorLayer)
                    ):
                        subset_string = f"cod_regio = '{self.comune_data.cod_regio}'"
                        map_layer.setSubsetString(subset_string)

                    # set custom properties
                    # for prop_name, prop_value in custom_properties.items():
                    #     self.set_layer_custom_property(layer_tree_layer.layer(), prop_name, prop_value)

                    # reset flags for testing
                    # self.set_project_layer_capabilities(layer_tree_layer.layer())

                    if layer_data["type"] != "group":
                        break

    def _add_default_value_relations(self, group_dict: dict):
        for table_name, layer_data in group_dict.items():
            if "value_relations" in layer_data:
                layers = self.find_layers_by_table_name(table_name)
                for layer in layers:
                    if layer and layer.customProperty("mzs_tools/layer_role") == "editing":
                        current_layer = layer

                for field_name, relation_data in layer_data["value_relations"].items():
                    table = relation_data["relation_table"]
                    table_layers = self.find_layers_by_table_name(table)
                    if len(table_layers) == 0:
                        self.log(
                            f"Error adding value relations: table not found for relation '{field_name}'",
                            log_level=2,
                        )
                        continue
                    if len(table_layers) > 1:
                        self.log(
                            f"Error adding value relations: multiple layers found for relation '{field_name}'",
                            log_level=2,
                        )
                        continue
                    for layer in table_layers:
                        if layer:
                            self.set_value_relation(current_layer, layer, field_name, relation_data)

    def set_value_relation(
        self, layer: QgsVectorLayer, relation_table_layer: QgsVectorLayer, field_name: str, relation_data: dict
    ):
        self.log(f"Setting value relation for field '{field_name}' in layer '{layer.name()}'", log_level=4)
        setup = QgsEditorWidgetSetup(
            "ValueRelation",
            {
                "Layer": relation_table_layer.id(),
                "Key": relation_data["relation_key"],
                "Value": relation_data["relation_value"],
                "OrderByValue": relation_data.get("order_by_value", False),
                "AllowNull": relation_data.get("allow_null", False),
                "FilterExpression": relation_data.get("filter_expression", ""),
            },
        )
        layer.setEditorWidgetSetup(layer.fields().indexOf(field_name), setup)

    def _check_default_project_relations(self):
        rel_manager = self.current_project.relationManager()
        relations_ok = True
        for relation_name, relation_data in DEFAULT_RELATIONS.items():
            rels = rel_manager.relationsByName(relation_name)
            if not rels:
                # self.log(f"Error: relation '{relation_name}' not found", log_level=2)
                self._add_project_issue("project", f"Relation '{relation_name}' not found")
                relations_ok = False
                continue
            if not rels[0].isValid():
                # self.log(f"Error: relation '{relation_name}' is not valid: {rels[0].validationError()}", log_level=2)
                self._add_project_issue(
                    "project", f"Relation '{relation_name}' is not valid: {rels[0].validationError()}"
                )
                relations_ok = False
                continue

            parent_layers = self.find_layers_by_table_name(relation_data["parent"])
            if not parent_layers:
                self._add_project_issue("project", f"Parent layer not found for relation '{relation_name}'")
                relations_ok = False
                continue
            child_layers = self.find_layers_by_table_name(relation_data["child"])
            if not child_layers:
                self._add_project_issue("project", f"Child layer not found for relation '{relation_name}'")
                relations_ok = False
                continue
            parent_layer_ids = [
                layer.id() for layer in parent_layers if layer.customProperty("mzs_tools/layer_role") == "editing"
            ]
            if rels[0].referencedLayerId() not in parent_layer_ids:
                self._add_project_issue("project", f"Relation '{relation_name}' parent layer is not set correctly")
                relations_ok = False
                continue
            child_layer_ids = [
                layer.id() for layer in child_layers if layer.customProperty("mzs_tools/layer_role") == "editing"
            ]
            if rels[0].referencingLayerId() not in child_layer_ids:
                self._add_project_issue("project", f"Relation '{relation_name}' child layer is not set correctly")
                relations_ok = False
                continue

        return relations_ok

    def _add_default_project_relations(self):
        rel_manager = self.current_project.relationManager()

        for relation_name, relation_data in DEFAULT_RELATIONS.items():
            parent_layer_id = self.find_layer_by_table_name_role(relation_data["parent"], "editing")
            child_layer_id = self.find_layer_by_table_name_role(relation_data["child"], "editing")
            if not parent_layer_id or not child_layer_id:
                msg = f"Error adding relations: parent or child layer not found for relation '{relation_name}'"
                self._add_project_issue("project", msg)
                continue

            rel = QgsRelation()
            rel.setId(relation_name)
            rel.setName(relation_name)
            rel.setReferencedLayer(parent_layer_id)
            rel.setReferencingLayer(child_layer_id)
            rel.addFieldPair(relation_data["parent_key"], relation_data["child_key"])

            if not rel.isValid():
                msg = f"Error creating relation '{relation_name}': {rel.validationError()}"
                self._add_project_issue("project", msg)
                continue

            rel_manager.addRelation(rel)

    def _add_default_layout_groups(self, group_name):
        root_layer_group = QgsLayerTreeGroup(group_name)
        root_layer_group.setIsMutuallyExclusive(True)
        root_layer_group.setItemVisibilityChecked(False)
        # check if the editing group exists
        editing_group = QgsProject.instance().layerTreeRoot().findGroup("BANCA DATI GEOGRAFICA")
        # put the layout group at the top of the tree only if the editing group does not exist
        idx = 1 if editing_group else 0
        self.current_project.layerTreeRoot().insertChildNode(idx, root_layer_group)
        for _group_name, qlr_path in DEFAULT_LAYOUT_GROUPS.items():
            qlr_full_path = DIR_PLUGIN_ROOT / "data" / "layer_defs" / "print_layout" / qlr_path
            self.add_layer_from_qlr(root_layer_group, qlr_full_path)

    def load_ogc_services(self, regional_wms=True, webms_wms=True, webms_wfs=True, geo_ispra=True):
        root_layer_group = self.current_project.layerTreeRoot().findGroup("Cartografia di base")
        if not root_layer_group:
            # add new OGC services groups
            root_layer_group = QgsLayerTreeGroup("SERVIZI OGC")
            root_layer_group.setItemVisibilityChecked(False)
            self.current_project.layerTreeRoot().addChildNode(root_layer_group)

        if regional_wms:
            self.add_layer_from_qlr(
                root_layer_group, DIR_PLUGIN_ROOT / "data" / "layer_defs" / "ogc_services" / "ctr_regioni.qlr"
            )
        if webms_wms:
            self.add_layer_from_qlr(
                root_layer_group, DIR_PLUGIN_ROOT / "data" / "layer_defs" / "ogc_services" / "ms_cle_wms.qlr"
            )
        if webms_wfs:
            self.add_layer_from_qlr(
                root_layer_group, DIR_PLUGIN_ROOT / "data" / "layer_defs" / "ogc_services" / "ms_cle_wfs.qlr"
            )
        if geo_ispra:
            self.add_layer_from_qlr(
                root_layer_group,
                DIR_PLUGIN_ROOT / "data" / "layer_defs" / "ogc_services" / "servizio_geologico_25k.qlr",
            )

        return root_layer_group.name()

    def add_layer_from_qlr(self, layer_group: QgsLayerTreeGroup, qlr_full_path: Path):
        if self.project_path is None:
            self.log("Project path is not set, cannot add layer from QLR", log_level=2)
            return

        # copy .qlr file in project folder
        shutil.copy(qlr_full_path, self.project_path)
        success, error_msg = QgsLayerDefinition.loadLayerDefinition(
            str(self.project_path / qlr_full_path.name),
            self.current_project,
            layer_group,
        )
        # remove the copied qlr file
        os.remove(self.project_path / qlr_full_path.name)
        if not success:
            self.log(f"Error loading layer from .qlr ({qlr_full_path}): {error_msg}", log_level=2)
        return success

    def _cleanup_base_layers(self):
        self.log("Cleaning up base layers...", log_level=4)
        for table_name, layer_data in DEFAULT_BASE_LAYERS.items():
            if layer_data["type"] == "service_group":
                group = self.current_project.layerTreeRoot().findGroup(layer_data["layer_name"])
                if group:
                    self.log(f"Removing group '{table_name}'", log_level=4)
                    parent_node = group.parent()
                    if parent_node and isinstance(parent_node, QgsLayerTreeGroup):
                        parent_node.removeChildNode(group)
                continue
            layers = self.find_layers_by_table_name(table_name)
            for layer in layers:
                # To remove old layers without the custom property, the "required" flag could be used.
                # However, this is not necessary if the projects are cleared on update to 2.0.0
                if layer and layer.customProperty("mzs_tools/layer_role") == "base":
                    self.log(f"Removing layer '{layer.name()}' (table: '{table_name}')", log_level=4)
                    layer_node = self.current_project.layerTreeRoot().findLayer(layer.id())
                    parent_node = None
                    if layer_node:
                        parent_node = layer_node.parent()
                    self.current_project.removeMapLayer(layer)
                    # remove parent group if empty
                    if parent_node and isinstance(parent_node, QgsLayerTreeGroup) and len(parent_node.children()) == 0:
                        gp = parent_node.parent()
                        if gp and isinstance(gp, QgsLayerTreeGroup):
                            gp.removeChildNode(parent_node)

    def _cleanup_editing_layers(self):
        self.log("Cleaning up removed layers...", log_level=4)
        for table_name in REMOVED_EDITING_LAYERS:
            layers = self.find_layers_by_table_name(table_name)
            for layer in layers:
                if layer:
                    self.log(f"Removing old layer '{layer.name()}' (table: '{table_name}')", log_level=4)
                    layer_node = self.current_project.layerTreeRoot().findLayer(layer.id())
                    parent_node = None
                    if layer_node:
                        parent_node = layer_node.parent()
                    self.current_project.removeMapLayer(layer)
                    # remove parent group if empty
                    if parent_node and isinstance(parent_node, QgsLayerTreeGroup) and len(parent_node.children()) == 0:
                        gp = parent_node.parent()
                        if gp and isinstance(gp, QgsLayerTreeGroup):
                            gp.removeChildNode(parent_node)

        self.log("Cleaning up editing layers...", log_level=4)
        for table_name in DEFAULT_EDITING_LAYERS:
            layers = self.find_layers_by_table_name(table_name)
            for layer in layers:
                if layer and layer.customProperty("mzs_tools/layer_role") == "editing":
                    self.log(f"Removing layer '{layer.name()}' (table: '{table_name}')", log_level=4)
                    layer_node = self.current_project.layerTreeRoot().findLayer(layer.id())
                    parent_node = None
                    if layer_node:
                        parent_node = layer_node.parent()
                    self.current_project.removeMapLayer(layer)
                    # remove parent group if empty
                    if parent_node and isinstance(parent_node, QgsLayerTreeGroup) and len(parent_node.children()) == 0:
                        gp = parent_node.parent()
                        if gp and isinstance(gp, QgsLayerTreeGroup):
                            gp.removeChildNode(parent_node)

        self.log("Cleaning up table layers...", log_level=4)
        for table_name in DEFAULT_TABLE_LAYERS_NAMES:
            layers = self.find_layers_by_table_name(table_name)
            for layer in layers:
                if layer and layer.customProperty("mzs_tools/layer_role") == "editing":
                    self.log(f"Removing layer '{layer.name()}' (table: '{table_name}')", log_level=4)
                    layer_node = self.current_project.layerTreeRoot().findLayer(layer.id())
                    parent_node = None
                    if layer_node:
                        parent_node = layer_node.parent()
                    self.current_project.removeMapLayer(layer)
                    # remove parent group if empty
                    if parent_node and isinstance(parent_node, QgsLayerTreeGroup) and len(parent_node.children()) == 0:
                        gp = parent_node.parent()
                        if gp and isinstance(gp, QgsLayerTreeGroup):
                            gp.removeChildNode(parent_node)

    def _cleanup_layout_groups(self):
        self.log("Cleaning up layout groups...", log_level=4)
        for group_name in DEFAULT_LAYOUT_GROUPS:
            group = self.current_project.layerTreeRoot().findGroup(group_name)
            if group:
                parent_node = group.parent()
                if not parent_node:
                    continue
                self.log(f"Removing layout group '{group_name}'", log_level=4)
                if isinstance(parent_node, QgsLayerTreeGroup):
                    parent_node.removeChildNode(group)
                    # remove parent group if empty
                    if parent_node and isinstance(parent_node, QgsLayerTreeGroup) and len(parent_node.children()) == 0:
                        gp = parent_node.parent()
                        if gp and isinstance(gp, QgsLayerTreeGroup):
                            gp.removeChildNode(parent_node)

    def find_layers_by_table_name(self, table_name: str) -> list:
        """Find all vector layers in the currrent project with the given table name in datasource uri."""
        layers = []
        for layer in self.current_project.mapLayers().values():
            if type(layer) is QgsVectorLayer:
                # Check if layer is valid and has a data provider
                if not layer.isValid():
                    continue
                provider = layer.dataProvider()
                if provider is None:
                    continue

                uri_table = provider.uri().table()
                if not uri_table:
                    # try to get the table name from 'layername' in dataSourceUri()...
                    strings = provider.dataSourceUri().split("layername=")
                    if len(strings) > 1:
                        uri_table = strings[1]
                if uri_table == table_name:
                    layers.append(layer)
        return layers

    def find_layer_by_table_name_role(self, table_name: str, role: str) -> str | None:
        """Find a single vector layer by table name and custom property mzs_tools/layer_role

        Args:
            table_name (str): Name of the database table
            role (str): Value of the custom property 'mzs_tools/layer_role' assigned to the layer

        Returns:
            Optional[str]: Layer ID or None if not found or multiple layers found
        """
        layers = self.find_layers_by_table_name(table_name)
        valid_layers = [layer for layer in layers if layer and layer.customProperty("mzs_tools/layer_role") == role]
        if not valid_layers or len(valid_layers) > 1:
            return None
        return valid_layers[0].id()

    def create_project(
        self, comune_name: str, cod_istat: str, study_author: str, author_email: str, dir_out: str
    ) -> Path:
        """Create a new MzS Tools project for a municipality in the specified directory.

        Args:
            comune_name (str): Name of the municipality
            cod_istat (str): ISTAT code of the municipality
            study_author (str): Name of the study author
            author_email (str): Email of the study author
            dir_out (str): Output directory

        Returns:
            Path: Path to the created project directory
        """
        comune_name = self.sanitize_comune_name(comune_name)
        new_project_path = Path(dir_out) / f"{cod_istat}_{comune_name}"

        if new_project_path.exists():
            self.log(f"Project directory '{new_project_path}' already exists!", log_level=1)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            new_project_path = Path(dir_out) / f"{cod_istat}_{comune_name}_{timestamp}"
        # create the project directory
        new_project_path.mkdir(parents=True, exist_ok=False)

        # Allegati paths
        allegati_paths = ["Altro", "Documenti", "log", "Plot", "Spettri"]
        for sub_dir in allegati_paths:
            sub_dir_path = new_project_path / "Allegati" / sub_dir
            sub_dir_path.mkdir(parents=True, exist_ok=False)

        loghi_path = new_project_path / "progetto" / "loghi"
        loghi_path.mkdir(parents=True, exist_ok=False)

        # copy the db file
        db_path = new_project_path / "db"
        db_path.mkdir(parents=True, exist_ok=False)
        self.extract_database_template(db_path)

        self.current_project = QgsProject.instance()

        self.project_path = new_project_path
        self.db_path = new_project_path / "db" / "indagini.sqlite"
        self._setup_db_connection()

        self.update_db_version_info()

        self._insert_comune_progetto(cod_istat)
        self.comune_data = self.get_project_comune_data()

        self.add_default_layers()
        self.customize_project()
        self.create_basic_project_metadata(cod_istat, study_author, author_email)
        self.refresh_project_layouts()

        # write the version file
        with open(os.path.join(self.project_path, "progetto", "versione.txt"), "w") as f:
            f.write(__base_version__)

        # Save the project
        self.current_project.write(os.path.join(new_project_path, "progetto_MS.qgz"))

        # completely reload the project
        iface.addProject(os.path.join(new_project_path, "progetto_MS.qgz"))

        return new_project_path

    def update_project(self):
        """Update the project without loading the project template.
        The database structure should be already updated.
        """
        if not self.project_updateable:
            self.log("Requested project update for non-updateable project!", log_level=1)
            return

        if self.project_path is None:
            self.log("Project path is not set, cannot update project", log_level=2)
            return

        if self.project_version is None:
            self.log("Cannot determine project version", log_level=2)
            return

        old_version = self.project_version

        # Create a progress message that will stay visible during operations
        progress_msg = iface.messageBar().createMessage(
            "MzS Tools", self.tr("Project update in progress. Please wait...")
        )

        # Add a progress bar to show activity
        progress_bar = QProgressBar()
        progress_bar.setRange(0, 0)  # Indeterminate progress bar
        progress_bar.setAlignment(get_alignment_flag("AlignLeft", "AlignVCenter"))
        progress_msg.layout().addWidget(progress_bar)

        # Push the message to the message bar
        message_item = iface.messageBar().pushWidget(progress_msg, Qgis.MessageLevel.Info)

        # Update the UI to ensure the message is visible
        iface.mainWindow().repaint()

        try:
            if old_version < "2.0.0":
                # version is too old, clear the project and start from scratch
                self.update_history_table("project", old_version, __version__, "clearing and rebuilding project")

                # backup print layouts
                layout_file_paths = self.backup_print_layouts(
                    backup_label=f"backup_v.{old_version}", backup_all=True, backup_models=True
                )

                self.current_project.clear()  # db connection is automatically closed!

                self.add_default_layers()
                self.customize_project()

                # load the print layouts from the backup
                try:
                    for layout_file_path in layout_file_paths:
                        if layout_file_path.exists():
                            self.load_print_layout_model(layout_file_path)
                except Exception as e:
                    self.log(f"Error loading print layout model backups: {e}", log_level=1)

                self.refresh_project_layouts()

                # Save the project
                self.current_project.write(str(self.project_path / "progetto_MS.qgz"))

                # cleanup project files
                old_files = [
                    self.project_path / "progetto_MS.qgs",
                    self.project_path / "progetto_MS.qgs~",
                    self.project_path / "progetto_MS_attachments.zip",
                    self.project_path / "progetto" / "script",
                    self.project_path / "progetto" / "maschere",
                ]
                for path in old_files:
                    if path.exists():
                        if path.is_file():
                            path.unlink()
                        elif path.is_dir():
                            shutil.rmtree(path)

                # write the version file (must be done *before* addProject())
                with open(self.project_path / "progetto" / "versione.txt", "w") as f:
                    f.write(__base_version__)

                # completely reload the project
                # this will trigger projectRead() signal, the main module will execute check_project() and finally
                # init_project() here, thus updating the detected plugin version
                iface.addProject(os.path.join(self.project_path, "progetto_MS.qgz"))

            # for versions >= 2.0.0 update only what's needed without clearing the project
            elif old_version == "2.0.0":
                # update from 2.0.0 to current __base_version__: update both the editing and the layout groups
                # - in 2.0.1 the hvsr layer for MOPS layout was updated to point to the new vw_hvsr_punti_misura view
                #   and the geotec editing layer had a small update
                # - in 2.0.2 "Cono o edificio vulcanico..." symbol in Carta Geologico-Tecnica and Carta delle MOPS
                #   was updated to use an embedded SVG symbol
                self.add_default_layers(add_base_layers=False, add_editing_layers=True, add_layout_groups=True)
                self.current_project.write(str(self.project_path / "progetto_MS.qgz"))

            elif old_version >= "2.0.1" and old_version < __base_version__:
                # update from 2.0.1 to current __base_version__: update only the layout groups
                self.add_default_layers(add_base_layers=False, add_editing_layers=False, add_layout_groups=True)
                self.current_project.write(str(self.project_path / "progetto_MS.qgz"))

            else:
                self.log(
                    f"No actions needed to update MzSTools QGIS project from version {old_version} to {__base_version__}."
                )

            # Resize the overview municipality map image used in print layouts if it's too large (applies to all version updates)
            # In versions < 2.0.2 the generated overview map was too large and causing slowdown during project loading
            # and enormous memory usage.
            self._resize_overview_map_image_if_needed()

            # write the version file (if not already done)
            with open(self.project_path / "progetto" / "versione.txt", "w") as f:
                f.write(__base_version__)

            self.update_history_table("project", old_version, __version__, "project updated successfully")
            # update mzs_tools_version table
            self.update_db_version_info()

            msg = self.tr("Project upgrades completed! Project upgraded to version")
            self.log(f"{msg} {__base_version__}", push=True, duration=0)
        finally:
            # Clear the message bar once the operation is complete
            iface.messageBar().popWidget(message_item)

    def customize_project(self):
        """Customize the project with the selected comune data."""
        if self.project_path is None:
            self.log("Project path is not set, cannot customize project", log_level=2)
            return

        crs = QgsCoordinateReferenceSystem("EPSG:32633")
        self.current_project.setCrs(crs)

        logo_regio_in = DIR_PLUGIN_ROOT / "resources" / "logo_regioni" / f"{self.comune_data.cod_regio}.png"
        logo_regio_out = self.project_path / "progetto" / "loghi" / "logo_regio.png"
        shutil.copyfile(logo_regio_in, logo_regio_out)

        # TODO: define a resource list for a project
        logo_regioni_path = DIR_PLUGIN_ROOT / "resources" / "img" / "logo_conferenza_regioni_province_autonome.jpg"
        shutil.copy(logo_regioni_path, self.project_path / "progetto" / "loghi")
        logo_dpc_path = DIR_PLUGIN_ROOT / "resources" / "img" / "logo_dpc.jpg"
        shutil.copy(logo_dpc_path, self.project_path / "progetto" / "loghi")
        legenda_hvsr_path = DIR_PLUGIN_ROOT / "resources" / "img" / "Legenda_valori_HVSR_rev01.svg"
        shutil.copy(legenda_hvsr_path, self.project_path / "progetto" / "loghi")

        mainPath = QgsProject.instance().homePath()
        canvas = iface.mapCanvas()

        image_file_path = os.path.join(mainPath, "progetto", "loghi", "mappa_reg.png")
        layer_limiti_comunali_id = self.find_layer_by_table_name_role("comuni", "base")
        layer_limiti_comunali_node = self.current_project.layerTreeRoot().findLayer(layer_limiti_comunali_id)
        # layer_limiti_comunali = layer_limiti_comunali_node.layer()  # Only needed for visibility

        layer_comune_progetto_id = self.find_layer_by_table_name_role("comune_progetto", "base")
        layer_comune_progetto_node = self.current_project.layerTreeRoot().findLayer(layer_comune_progetto_id)
        layer_comune_progetto = layer_comune_progetto_node.layer()

        # Ensure layers have data before proceeding
        if (
            not layer_comune_progetto
            or not isinstance(layer_comune_progetto, QgsVectorLayer)
            or layer_comune_progetto.featureCount() == 0
        ):
            self.log("Warning: comune_progetto layer is empty or not found", log_level=1)
            return

        layer_comune_progetto.dataProvider().updateExtents()
        layer_comune_progetto.updateExtents()

        # Get the extent from layer_comune_progetto for canvas positioning
        extent = layer_comune_progetto.extent()
        if extent.isEmpty():
            self.log("Warning: comune_progetto layer extent is empty", log_level=1)
            return

        # Get the extent from layer_limiti_comunali for the map image (broader view)
        if layer_limiti_comunali_node and layer_limiti_comunali_node.layer():
            layer_limiti_comunali = layer_limiti_comunali_node.layer()
            layer_limiti_comunali.dataProvider().updateExtents()
            if isinstance(layer_limiti_comunali, QgsVectorLayer):
                layer_limiti_comunali.updateExtents()
            map_extent = layer_limiti_comunali.extent()
            zoom_layer_for_image = layer_limiti_comunali
            self.log(f"Using layer_limiti_comunali extent for map image: {map_extent}")
        else:
            # Fallback to comune_progetto if limiti_comunali is not available
            map_extent = extent
            zoom_layer_for_image = layer_comune_progetto
            self.log("Fallback: using layer_comune_progetto extent for map image")

        # Set canvas extent to the project municipality (for canvas display)
        canvas.setExtent(extent)

        # Ensure both layers are visible for the map image
        if layer_limiti_comunali_node:
            layer_limiti_comunali_node.setItemVisibilityCheckedParentRecursive(True)
        layer_comune_progetto_node.setItemVisibilityCheckedParentRecursive(True)

        # Force canvas to use specific layers for rendering
        layers_to_render = []
        if layer_limiti_comunali_node and layer_limiti_comunali_node.layer():
            layer = layer_limiti_comunali_node.layer()
            layers_to_render.append(layer)
            # self.log(f"Added layer_limiti_comunali: {layer.name()}, features: {layer.featureCount()}")
        if layer_comune_progetto is not None:
            layers_to_render.append(layer_comune_progetto)
            # self.log(
            #     f"Added layer_comune_progetto: {layer_comune_progetto.name()}, features: {layer_comune_progetto.featureCount()}"
            # )

        if not layers_to_render:
            self.log("Error: No valid layers found for rendering", log_level=1)
            return

        canvas.setLayers(layers_to_render)

        # Refresh canvas to ensure layers are rendered
        canvas.refresh()

        # self.log(f"Canvas layers set to: {[layer.name() for layer in layers_to_render]}")
        # self.log(f"Canvas extent: {canvas.extent()}")
        # self.log(f"Map image extent: {map_extent}")
        # self.log(f"Canvas scale: {canvas.scale()}")

        # Try the canvas-based approach first
        try:
            # Use layer_limiti_comunali extent for the map image (broader regional view)
            save_map_image(image_file_path, zoom_layer_for_image, canvas)
        except Exception as e:
            self.log(f"Canvas-based image generation failed: {e}, trying direct approach", log_level=1)
            # Fallback to direct rendering with the broader extent
            save_map_image_direct(image_file_path, layers_to_render, map_extent, zoom_layer_for_image.crs())

        canvas.setExtent(extent)

        self.load_print_layouts()

        # set project title
        project_title = f"MzS Tools - Comune di {self.comune_data.comune} ({self.comune_data.provincia}, {self.comune_data.regione}) - Studio di Microzonazione Sismica"
        self.current_project.setTitle(project_title)

        # enable map decorations
        # https://github.com/qgis/QGIS/issues/53095
        # design in QGIS and then read the settings with:
        # QgsProject.instance().readEntry("TitleLabel", "Font")
        # QgsProject.instance().readEntry("TitleLabel", "BackgroundColor")
        # QgsProject.instance().readEntry("TitleLabel", "Placement")
        # QgsProject.instance().readEntry("TitleLabel", "MarginH")
        # QgsProject.instance().readEntry("TitleLabel", "MarginV")
        font_style = '<text-style allowHtml="0" fontFamily="Noto Sans" fontSizeUnit="Point" textColor="17,98,152,255,rgb:0.06666666666666667,0.3843137254901961,0.59607843137254901,1" tabStopDistanceUnit="Point" namedStyle="Bold" fontKerning="1" tabStopDistanceMapUnitScale="3x:0,0,0,0,0,0" fontLetterSpacing="0" tabStopDistance="80" capitalization="0" forcedItalic="0" previewBkgrdColor="255,255,255,255,rgb:1,1,1,1" fontWeight="75" fontStrikeout="0" multilineHeightUnit="Percentage" forcedBold="0" textOpacity="1" fontItalic="0" multilineHeight="1" fontSizeMapUnitScale="3x:0,0,0,0,0,0" fontWordSpacing="0" fontSize="10" textOrientation="horizontal" fontUnderline="0" blendMode="0">\n <families/>\n <text-buffer bufferBlendMode="0" bufferDraw="0" bufferSize="1" bufferColor="255,255,255,255,rgb:1,1,1,1" bufferOpacity="1" bufferNoFill="1" bufferJoinStyle="128" bufferSizeMapUnitScale="3x:0,0,0,0,0,0" bufferSizeUnits="MM"/>\n <text-mask maskedSymbolLayers="" maskJoinStyle="128" maskSizeMapUnitScale="3x:0,0,0,0,0,0" maskSize="1.5" maskEnabled="0" maskSize2="1.5" maskType="0" maskSizeUnits="MM" maskOpacity="1"/>\n <background shapeSizeMapUnitScale="3x:0,0,0,0,0,0" shapeRotationType="0" shapeBlendMode="0" shapeRadiiMapUnitScale="3x:0,0,0,0,0,0" shapeSizeX="0" shapeRadiiUnit="MM" shapeOffsetX="0" shapeRadiiX="0" shapeFillColor="255,255,255,255,rgb:1,1,1,1" shapeOpacity="1" shapeRadiiY="0" shapeBorderColor="128,128,128,255,rgb:0.50196078431372548,0.50196078431372548,0.50196078431372548,1" shapeOffsetY="0" shapeSizeUnit="MM" shapeBorderWidthMapUnitScale="3x:0,0,0,0,0,0" shapeSizeType="0" shapeRotation="0" shapeDraw="0" shapeOffsetMapUnitScale="3x:0,0,0,0,0,0" shapeOffsetUnit="MM" shapeType="0" shapeBorderWidth="0" shapeSizeY="0" shapeJoinStyle="64" shapeSVGFile="" shapeBorderWidthUnit="MM">\n  <symbol alpha="1" force_rhr="0" type="marker" name="markerSymbol" clip_to_extent="1" is_animated="0" frame_rate="10">\n   <data_defined_properties>\n    <Option type="Map">\n     <Option type="QString" name="name" value=""/>\n     <Option name="properties"/>\n     <Option type="QString" name="type" value="collection"/>\n    </Option>\n   </data_defined_properties>\n   <layer locked="0" class="SimpleMarker" enabled="1" pass="0" id="">\n    <Option type="Map">\n     <Option type="QString" name="angle" value="0"/>\n     <Option type="QString" name="cap_style" value="square"/>\n     <Option type="QString" name="color" value="229,182,54,255,rgb:0.89803921568627454,0.71372549019607845,0.21176470588235294,1"/>\n     <Option type="QString" name="horizontal_anchor_point" value="1"/>\n     <Option type="QString" name="joinstyle" value="bevel"/>\n     <Option type="QString" name="name" value="circle"/>\n     <Option type="QString" name="offset" value="0,0"/>\n     <Option type="QString" name="offset_map_unit_scale" value="3x:0,0,0,0,0,0"/>\n     <Option type="QString" name="offset_unit" value="MM"/>\n     <Option type="QString" name="outline_color" value="35,35,35,255,rgb:0.13725490196078433,0.13725490196078433,0.13725490196078433,1"/>\n     <Option type="QString" name="outline_style" value="solid"/>\n     <Option type="QString" name="outline_width" value="0"/>\n     <Option type="QString" name="outline_width_map_unit_scale" value="3x:0,0,0,0,0,0"/>\n     <Option type="QString" name="outline_width_unit" value="MM"/>\n     <Option type="QString" name="scale_method" value="diameter"/>\n     <Option type="QString" name="size" value="2"/>\n     <Option type="QString" name="size_map_unit_scale" value="3x:0,0,0,0,0,0"/>\n     <Option type="QString" name="size_unit" value="MM"/>\n     <Option type="QString" name="vertical_anchor_point" value="1"/>\n    </Option>\n    <data_defined_properties>\n     <Option type="Map">\n      <Option type="QString" name="name" value=""/>\n      <Option name="properties"/>\n      <Option type="QString" name="type" value="collection"/>\n     </Option>\n    </data_defined_properties>\n   </layer>\n  </symbol>\n  <symbol alpha="1" force_rhr="0" type="fill" name="fillSymbol" clip_to_extent="1" is_animated="0" frame_rate="10">\n   <data_defined_properties>\n    <Option type="Map">\n     <Option type="QString" name="name" value=""/>\n     <Option name="properties"/>\n     <Option type="QString" name="type" value="collection"/>\n    </Option>\n   </data_defined_properties>\n   <layer locked="0" class="SimpleFill" enabled="1" pass="0" id="">\n    <Option type="Map">\n     <Option type="QString" name="border_width_map_unit_scale" value="3x:0,0,0,0,0,0"/>\n     <Option type="QString" name="color" value="255,255,255,255,rgb:1,1,1,1"/>\n     <Option type="QString" name="joinstyle" value="bevel"/>\n     <Option type="QString" name="offset" value="0,0"/>\n     <Option type="QString" name="offset_map_unit_scale" value="3x:0,0,0,0,0,0"/>\n     <Option type="QString" name="offset_unit" value="MM"/>\n     <Option type="QString" name="outline_color" value="128,128,128,255,rgb:0.50196078431372548,0.50196078431372548,0.50196078431372548,1"/>\n     <Option type="QString" name="outline_style" value="no"/>\n     <Option type="QString" name="outline_width" value="0"/>\n     <Option type="QString" name="outline_width_unit" value="MM"/>\n     <Option type="QString" name="style" value="solid"/>\n    </Option>\n    <data_defined_properties>\n     <Option type="Map">\n      <Option type="QString" name="name" value=""/>\n      <Option name="properties"/>\n      <Option type="QString" name="type" value="collection"/>\n     </Option>\n    </data_defined_properties>\n   </layer>\n  </symbol>\n </background>\n <shadow shadowBlendMode="6" shadowDraw="0" shadowRadius="1.5" shadowOffsetMapUnitScale="3x:0,0,0,0,0,0" shadowRadiusUnit="MM" shadowScale="100" shadowUnder="0" shadowRadiusMapUnitScale="3x:0,0,0,0,0,0" shadowOffsetAngle="135" shadowRadiusAlphaOnly="0" shadowOpacity="0.69999999999999996" shadowColor="0,0,0,255,rgb:0,0,0,1" shadowOffsetUnit="MM" shadowOffsetGlobal="1" shadowOffsetDist="1"/>\n <dd_properties>\n  <Option type="Map">\n   <Option type="QString" name="name" value=""/>\n   <Option name="properties"/>\n   <Option type="QString" name="type" value="collection"/>\n  </Option>\n </dd_properties>\n</text-style>\n'
        self.current_project.writeEntry("TitleLabel", "/Font", font_style)
        self.current_project.writeEntry("TitleLabel", "/Label", "[%@project_title%]")
        self.current_project.writeEntry(
            "TitleLabel",
            "/BackgroundColor",
            "133,133,133,73,rgb:0.52156862745098043,0.52156862745098043,0.52156862745098043,0.28627450980392155",
        )
        self.current_project.writeEntry("TitleLabel", "/Enabled", True)

    def load_print_layouts(self):
        for _layout_name, model_file_name in PRINT_LAYOUT_MODELS.items():
            self.load_print_layout_model(model_file_name)

    def load_print_layout_model(self, model_file_name: str):
        self.log(f"Loading print layout model: {model_file_name}", log_level=4)

        # check if the layout requested is one of the default models
        is_default_model = model_file_name in PRINT_LAYOUT_MODELS.values()

        layout_manager = self.current_project.layoutManager()
        layout = QgsPrintLayout(self.current_project)
        # load the layout model
        if is_default_model:
            layout_model_path = DIR_PLUGIN_ROOT / "data" / "print_layouts" / model_file_name
        else:
            layout_model_path = Path(model_file_name)
        with layout_model_path.open("r") as f:
            layout_model = f.read()
        doc = QDomDocument()
        doc.setContent(layout_model)
        layout.loadFromTemplate(doc, QgsReadWriteContext())

        # set layout elements for the current project if it's a default model
        if is_default_model:
            canvas = iface.mapCanvas()
            map_item = layout.itemById("mappa_0")
            # TODO: get extent from comune_progetto table
            # TODO: properly check map item types
            map_item.zoomToExtent(canvas.extent())  # type: ignore
            map_item_2 = layout.itemById("regio_title")
            map_item_2.setText("Regione " + self.comune_data.regione)  # type: ignore
            map_item_3 = layout.itemById("com_title")
            map_item_3.setText("Comune di " + self.comune_data.comune)  # type: ignore
            map_item_4 = layout.itemById("logo")
            map_item_4.refreshPicture()  # type: ignore
            map_item_5 = layout.itemById("mappa_1")
            map_item_5.refreshPicture()  # type: ignore

        layout_manager.addLayout(layout)

    def backup_print_layouts(
        self,
        backup_label: str | None = None,
        backup_timestamp: bool = False,
        backup_models: bool = False,
        backup_all: bool = False,
    ):
        layout_manager = self.current_project.layoutManager()
        layouts = layout_manager.printLayouts()
        if backup_label:
            backup_label = f"{backup_label}"
        if backup_timestamp:
            backup_label = f"{backup_label}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        layout_file_paths = []
        for layout in layouts:
            if "backup" in layout.name() and not backup_all:
                continue
            else:
                layout_file_path = self.backup_print_layout(layout, backup_label, backup_models)
                if layout_file_path:
                    layout_file_paths.append(layout_file_path)
        return layout_file_paths

    def backup_print_layout(
        self, layout: QgsPrintLayout, backup_label: str | None = None, backup_model_file: bool = False
    ):
        self.log(f"Backing up layout: {layout.name()}", log_level=4)
        layout_name = layout.name()
        layout_clone = layout.clone()
        layout_clone.setName(f"[{backup_label or 'backup'}]_{layout_name}")
        layout_file_path = None
        if backup_model_file and layout_clone:
            layout_file_path = self.save_print_layout(layout_clone)
        layout_manager = self.current_project.layoutManager()
        layout_manager.addLayout(layout_clone)
        return layout_file_path

    def save_print_layout(self, layout: QgsPrintLayout):
        if self.project_path is None:
            self.log("Project path is not set", log_level=2)
            return
        layout_name = layout.name()
        layout_models_path = self.project_path / "progetto" / "layout"
        layout_models_path.mkdir(parents=True, exist_ok=True)
        layout_path = layout_models_path / f"{layout_name}.qpt"
        self.log(f"Backing up layout: {layout_name} to {layout_path}", log_level=4)
        layout.saveAsTemplate(str(layout_path), QgsReadWriteContext())
        return layout_path

    def refresh_project_layouts(self):
        layout_manager = self.current_project.layoutManager()
        layouts = layout_manager.printLayouts()
        for layout in layouts:
            layout.refresh()

    def _resize_overview_map_image_if_needed(self):
        """Resize the municipality overview map image used in print layouts if it's larger than 2000px."""
        if self.project_path is None:
            self.log("Project path is not set, cannot resize overview map image", log_level=2)
            return

        map_image_path = self.project_path / "progetto" / "loghi" / "mappa_reg.png"

        if not map_image_path.exists():
            self.log("Map image not found, skipping resize", log_level=4)
            return

        try:
            from qgis.PyQt.QtGui import QPixmap

            # Load the image to check its dimensions
            pixmap = QPixmap(str(map_image_path))
            if pixmap.isNull():
                self.log("Failed to load map image for size check", log_level=1)
                return

            original_width = pixmap.width()
            original_height = pixmap.height()

            self.log(f"Map image current size: {original_width}x{original_height}")

            # Check if the image is larger than 2000px width
            if original_width > 2000:
                # Calculate new height maintaining aspect ratio
                new_width = 1280
                new_height = int((new_width * original_height) / original_width)

                self.log(f"Resizing map image from {original_width}x{original_height} to {new_width}x{new_height}")

                # Resize the image
                # PyQt5:
                #   aspectRatioMode=Qt.KeepAspectRatio,
                #   transformMode=Qt.SmoothTransformation,
                # PyQt6:
                #   aspectRatioMode=Qt.AspectRatioMode.KeepAspectRatio,
                #   transformMode=Qt.TransformationMode.SmoothTransformation,
                scaled_pixmap = pixmap.scaled(
                    new_width,
                    new_height,
                    aspectRatioMode=1,  # type: ignore
                    transformMode=1,  # type: ignore
                )

                # Create backup of original
                backup_path = map_image_path.with_suffix(".png.backup")
                if not backup_path.exists():
                    import shutil

                    shutil.copy2(map_image_path, backup_path)
                    self.log(f"Created backup of original map image: {backup_path}")

                # Save the resized image
                success = scaled_pixmap.save(str(map_image_path), "PNG")
                if success:
                    self.log(f"Successfully resized map image to {new_width}x{new_height}")
                else:
                    self.log("Failed to save resized map image", log_level=1)
            else:
                self.log(f"Map image size ({original_width}px) is within acceptable limits, no resize needed")

        except Exception as e:
            self.log(f"Error resizing map image: {e}", log_level=1)

    # database operations --------------------------------------------------------------------------------------------

    def _setup_db_connection(self):
        """Setup database connection."""
        if not self.db_path:
            self.log("Database path is not set, cannot setup db connection", log_level=2)
            return False

        if not self.db_manager:
            self.log(f"Creating db connection to {self.db_path}...", log_level=4)

            # Create new DatabaseManager
            self.db_manager = DatabaseManager(self.db_path, logger=self)

            try:
                self.db_manager.connect()
                return True
            except Exception as e:
                err_msg = self.tr(f"Error connecting to db! {self.db_path}")
                self.log(f"{err_msg}: {e}", log_level=2, push=True, duration=0)
                self.cleanup_db_connection()
                return False
        return True

    def cleanup_db_connection(self):
        """Cleanup both legacy and new database connections."""
        if self.db_manager:
            self.db_manager.disconnect()
            self.db_manager = None

    def get_project_comune_data(self) -> ComuneData | None:
        """Get municipality data from the project database."""
        row = self.db.execute_query("SELECT * FROM comune_progetto LIMIT 1", fetch_mode="one")

        if row:
            # workaround for very old projects (< 1.0)
            provincia = ""
            regione = ""
            cod_istat = ""
            try:
                cod_istat = row[6]
                provincia = row[7]
                regione = row[8]
            except IndexError:
                cod_istat = row[5]

            return ComuneData(
                cod_regio=row[1],
                cod_prov=row[2],
                cod_com=row[3],
                comune=row[4],
                provincia=provincia,
                regione=regione,
                cod_istat=cod_istat,
            )
        return None

    def _insert_comune_progetto(self, cod_istat):
        """Insert municipality data into the project database."""
        try:
            self.db.execute_update(
                """INSERT INTO comune_progetto (cod_regio, cod_prov, "cod_com ", comune, geom, cod_istat, provincia, regione)
                SELECT cod_regio, cod_prov, cod_com, comune, GEOMETRY, cod_istat, provincia, regione
                FROM comuni WHERE cod_istat = ?""",
                (cod_istat,),
            )
        except Exception as e:
            self.log(f"Failed to insert comune data: {e}", log_level=2, push=True, duration=0)
            raise

    def update_db(self):
        """Update database schema to current version."""
        if self.project_version is None:
            self.log("Project version is not set, cannot update database", log_level=2)
            return

        sql_scripts = []

        for version, script in DB_MIGRATION_SCRIPTS.items():
            if self.project_version < version:
                sql_scripts.append(script)

        for upgrade_script in sql_scripts:
            self.log(f"Executing: {upgrade_script}", log_level=1)
            # self._exec_db_upgrade_script(upgrade_script)
            script_path = DIR_PLUGIN_ROOT / "data" / "sql_scripts" / upgrade_script
            self.db.execute_script_file(script_path)

        for upgrade_script in sql_scripts:
            # doing this in a separate loop because the mzs_tools_update_history table was created only in v2.0.0
            self.update_history_table("db", self.project_version, __version__, f"executed script {upgrade_script}")

        # update mzs_tools_version table
        self.update_db_version_info()

        msg = self.tr("Database upgrades completed! Database upgraded to version")
        self.log(f"{msg} {__base_version__}", push=True, duration=0)

    def update_history_table(self, component: str, from_version: str, to_version: str, notes: str | None = None):
        """Update the project update history table."""
        try:
            # Check if table exists
            if self.db.table_exists("mzs_tools_update_history"):
                self.db.execute_update(
                    "INSERT INTO mzs_tools_update_history (updated_component, from_version, to_version, notes) VALUES (?, ?, ?, ?)",
                    (component, from_version, to_version, notes),
                )
        except Exception as e:
            self.log(f"Failed to update history table: {e}", log_level=2)

    def update_db_version_info(self):
        """Update the database version information."""
        try:
            self.db.execute_update(
                "INSERT OR REPLACE INTO mzs_tools_version (id, db_version) VALUES (?, ?)", (1, __base_version__)
            )
        except Exception as e:
            self.log(f"Failed to update version info: {e}", log_level=2)

    def create_basic_project_metadata(self, cod_istat, study_author=None, author_email=None):
        """Create a basic metadata record for an MzS Tools project."""
        date_now = datetime.now().strftime(r"%Y-%m-%d")
        layer_comune_id = self.find_layer_by_table_name_role("comune_progetto", "base")
        extent = self.current_project.layerTreeRoot().findLayer(layer_comune_id).layer().extent()

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

        # Note: execute_update doesn't support named parameters yet
        # Use transaction context for complex operations
        with self.db.transaction() as cursor:
            cursor.execute(
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

    def count_indagini_data(self):
        """Count records and sequences for investigation tables."""
        tables = [
            "sito_puntuale",
            "indagini_puntuali",
            "parametri_puntuali",
            "curve",
            "sito_lineare",
            "indagini_lineari",
            "parametri_lineari",
        ]

        result = {}
        for table in tables:
            count = self.db.get_row_count(table)
            seq = self.db.get_sequence_value(table)
            result[table] = [count, seq]

        return result

    def reset_indagini_sequences(self):
        """Reset auto-increment sequences for investigation tables."""
        tables = [
            "sito_puntuale",
            "indagini_puntuali",
            "parametri_puntuali",
            "curve",
            "sito_lineare",
            "indagini_lineari",
            "parametri_lineari",
        ]

        with self.db.transaction() as cursor:
            for table in tables:
                cursor.execute("UPDATE sqlite_sequence SET seq = 0 WHERE name=?", (table,))

    # backup methods -------------------------------------------------------------------------------------------------

    def backup_database(self, out_dir=None):
        if self.project_path is None:
            self.log("Project path is not set, cannot backup database", log_level=2)
            return None

        if self.db_path is None:
            self.log("Database path is not set, cannot backup database", log_level=2)
            return None

        if not out_dir:
            out_dir = self.project_path / "db"

        db_backup_path = (
            out_dir / f"indagini_backup_v{self.project_version}_{datetime.now().strftime('%Y_%m_%d_%H_%M')}.sqlite"
        )

        self.log(f"Backing up database in {db_backup_path}...")
        shutil.copy(self.db_path, db_backup_path)

        return db_backup_path

    def backup_project(self, out_dir=None):
        if self.project_path is None:
            self.log("Project path is not set, cannot backup project", log_level=2)
            return None

        if not out_dir:
            out_dir = self.project_path.parent

        project_folder_name = self.project_path.name
        backup_dir_name = (
            f"{project_folder_name}_backup_v{self.project_version}_{datetime.now().strftime('%Y_%m_%d_%H_%M')}"
        )
        backup_path = out_dir / backup_dir_name

        self.log(f"Backing up project in {backup_path}...")
        shutil.copytree(self.project_path, backup_path)

        return backup_path

    def backup_qgis_project(self) -> Path | None:
        if self.project_path is None:
            self.log("Project path is not set, cannot backup QGIS project", log_level=2)
            return None

        project_file_name = f"{self.current_project.baseName()}_backup_v{self.project_version}_{datetime.now().strftime('%Y_%m_%d-%H_%M')}.qgz"
        project_backup_path = self.project_path / project_file_name

        self.log(f"Backing up QGIS project to {project_backup_path}...")
        shutil.copy(self.current_project.absoluteFilePath(), project_backup_path)

        return project_backup_path

    # static methods -------------------------------------------------------------------------------------------------

    @staticmethod
    def extract_project_template(dir_out):
        project_template_path = DIR_PLUGIN_ROOT / "data" / "progetto_MS.zip"
        with zipfile.ZipFile(str(project_template_path), "r") as zip_ref:
            zip_ref.extractall(dir_out)

    @staticmethod
    def extract_database_template(dir_out):
        database_template_path = DIR_PLUGIN_ROOT / "data" / "indagini.sqlite.zip"
        with zipfile.ZipFile(str(database_template_path), "r") as zip_ref:
            zip_ref.extractall(dir_out)

    @staticmethod
    def sanitize_comune_name(comune_name):
        return comune_name.split(" (")[0].replace(" ", "_").replace("'", "_")

    def tr(self, message: str) -> str:
        return QCoreApplication.translate(self.__class__.__name__, message)
