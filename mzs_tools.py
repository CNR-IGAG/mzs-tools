import os
import shutil
from functools import partial
from itertools import chain
from pathlib import Path

from qgis.core import (
    Qgis,
    QgsApplication,
    QgsProject,
    QgsSettings,
    QgsSnappingConfig,
    QgsTolerance,
)
from qgis.PyQt.QtCore import QCoreApplication, QSettings, QTranslator
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QFileDialog, QMessageBox, qApp

from .constants import NO_OVERLAPS_LAYER_GROUPS, SUGGESTED_QGIS_VERSION
from .tb_aggiorna_progetto import aggiorna_progetto
from .tb_copia_ms import copia_ms
from .tb_edit_metadata import EditMetadataDialog
from .tb_edit_win import edit_win
from .tb_esporta_shp import esporta_shp
from .tb_importa_shp import importa_shp
from .tb_info import info
from .tb_nuovo_progetto import NewProject
from .utils import detect_mzs_tools_project, plugin_version_from_metadata_file, qgs_log


class MzSTools:
    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)

        # initialize locale
        try:
            locale = QSettings().value("locale/userLocale", "en", type=str)[0:2]
        except Exception:
            locale = "en"
        locale_path = os.path.join(self.plugin_dir, "i18n", "MzSTools_{}.qm".format(locale))
        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        self.project_update_dlg = aggiorna_progetto()
        self.new_project_dlg = NewProject()
        self.edit_metadata_dlg = EditMetadataDialog()
        self.info_dlg = info()
        self.import_shp_dlg = importa_shp()
        self.export_shp_dlg = esporta_shp()
        self.ms_copy_dlg = copia_ms()
        self.edit_win_dlg = edit_win()

        self.actions = []
        self.menu = self.tr("&MzS Tools")
        self.toolbar = self.iface.addToolBar("MzSTools")
        self.toolbar.setObjectName("MzSTools")

        self.new_project_dlg.dir_output.clear()
        self.new_project_dlg.pushButton_out.clicked.connect(self.select_output_fld_2)

        self.import_shp_dlg.dir_input.clear()
        self.import_shp_dlg.pushButton_in.clicked.connect(self.select_input_fld_4)

        self.import_shp_dlg.tab_input.clear()
        self.import_shp_dlg.pushButton_tab.clicked.connect(self.select_tab_fld_4)

        self.export_shp_dlg.dir_output.clear()
        self.export_shp_dlg.pushButton_out.clicked.connect(self.select_output_fld_5)

        QgsSettings().setValue("qgis/enableMacros", 3)

        # connect to projectRead signal
        self.iface.projectRead.connect(self.check_project)

    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None,
    ):
        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToDatabaseMenu(self.menu, action)

        self.actions.append(action)

        return action

    def initGui(self):
        icon_path2 = os.path.join(self.plugin_dir, "img", "ico_nuovo_progetto.png")
        icon_path3 = os.path.join(self.plugin_dir, "img", "ico_info.png")
        icon_path4 = os.path.join(self.plugin_dir, "img", "ico_importa.png")
        icon_path5 = os.path.join(self.plugin_dir, "img", "ico_esporta.png")
        icon_path6 = os.path.join(self.plugin_dir, "img", "ico_copia_ms.png")
        # icon_path8 = os.path.join(self.plugin_dir, "img", "ico_edita.png")
        # icon_path9 = os.path.join(self.plugin_dir, "img", "ico_salva_edita.png")
        icon_path10 = os.path.join(self.plugin_dir, "img", "ico_xypoint.png")

        self.add_action(
            icon_path2,
            text=self.tr("New project"),
            callback=self.new_project,
            parent=self.iface.mainWindow(),
        )

        self.add_action(
            QgsApplication.getThemeIcon("/mActionEditHtml.svg"),
            text=self.tr("Edit project metadata"),
            callback=self.edit_metadata,
            parent=self.iface.mainWindow(),
        )

        self.toolbar.addSeparator()

        self.add_action(
            icon_path4,
            text=self.tr("Import project folder from geodatabase"),
            callback=self.import_project,
            parent=self.iface.mainWindow(),
        )

        self.add_action(
            icon_path5,
            text=self.tr("Export geodatabase to project folder"),
            callback=self.export_project,
            parent=self.iface.mainWindow(),
        )

        self.toolbar.addSeparator()

        # self.add_action(
        #     icon_path8,
        #     text=self.tr("Add feature or record"),
        #     callback=self.add_feature_or_record,
        #     parent=self.iface.mainWindow(),
        # )

        # self.add_action(
        #     icon_path9,
        #     text=self.tr("Save"),
        #     callback=self.save,
        #     parent=self.iface.mainWindow(),
        # )

        self.add_action(
            icon_path10,
            text=self.tr('Add "Sito puntuale" using XY coordinates'),
            callback=self.add_site,
            parent=self.iface.mainWindow(),
        )

        self.add_action(
            icon_path6,
            text=self.tr('Copy "Stab" or "Instab" layer'),
            callback=self.copy_stab,
            parent=self.iface.mainWindow(),
        )

        self.toolbar.addSeparator()

        self.add_action(
            icon_path3,
            text=self.tr("Help"),
            callback=self.help,
            parent=self.iface.mainWindow(),
        )

    def unload(self):
        for action in self.actions:
            self.iface.removePluginDatabaseMenu(self.tr("&MzS Tools"), action)
            self.iface.removeToolBarIcon(action)
        del self.toolbar

    def select_output_fld_2(self):
        out_dir = QFileDialog.getExistingDirectory(self.new_project_dlg, "", "", QFileDialog.ShowDirsOnly)
        self.new_project_dlg.dir_output.setText(out_dir)

    def select_input_fld_4(self):
        in_dir = QFileDialog.getExistingDirectory(self.import_shp_dlg, "", "", QFileDialog.ShowDirsOnly)
        self.import_shp_dlg.dir_input.setText(in_dir)

    def select_tab_fld_4(self):
        tab_dir = QFileDialog.getExistingDirectory(self.import_shp_dlg, "", "", QFileDialog.ShowDirsOnly)
        self.import_shp_dlg.tab_input.setText(tab_dir)

    def select_input_fld_5(self):
        in_dir = QFileDialog.getExistingDirectory(self.export_shp_dlg, "", "", QFileDialog.ShowDirsOnly)
        self.export_shp_dlg.dir_input.setText(in_dir)

    def select_output_fld_5(self):
        out_dir = QFileDialog.getExistingDirectory(self.export_shp_dlg, "", "", QFileDialog.ShowDirsOnly)
        self.export_shp_dlg.dir_output.setText(out_dir)

    def check_project(self):
        """
        Check if the current project is a MzSTools project to:
        - update svg symbols in the QGIS profile
        - check if the project version is older than the plugin version and start the update process
        - connect editing signals to automatically set cross-layer no-overlap rules when needed and
          revert to the original config when editing stops
        - connect to layer nameChanged signal to warn the user when renaming required layers
        - warn the user if the QGIS version is less than SUGGESTED_QGIS_VERSION defined in constants.py
        """
        project_info = detect_mzs_tools_project()
        if not project_info:
            return

        qgs_log(f"MzSTools project detected. Project version: {project_info['version']}")

        qgs_log("Checking svg symbols...")
        dir_svg_input = os.path.join(self.plugin_dir, "img", "svg")
        dir_svg_output = self.plugin_dir.split("python")[0] + "svg"

        if not os.path.exists(dir_svg_output):
            qgs_log(f"Copying svg symbols in {dir_svg_output}")
            shutil.copytree(dir_svg_input, dir_svg_output)
        else:
            qgs_log(f"Updating svg symbols in {dir_svg_output}")
            src_files = os.listdir(dir_svg_input)
            for file_name in src_files:
                full_file_name = os.path.join(dir_svg_input, file_name)
                if os.path.isfile(full_file_name):
                    shutil.copy(full_file_name, dir_svg_output)

        qgs_log("Comparing project and plugin versions...")
        plugin_version = plugin_version_from_metadata_file()

        if project_info["version"] < plugin_version:
            qgs_log(f"Project should be updated to version {plugin_version}")
            output_path = Path(project_info["project_path"]).parent
            project_folder_name = Path(project_info["project_path"]).name
            qApp.processEvents()
            self.project_update_dlg.aggiorna(
                project_info["project_path"], str(output_path), project_folder_name, project_info["version"]
            )

        self.connect_editing_signals()

        # connect to layer nameChanged signal to warn the user when renaming required layers
        # TODO: find a better way to protect required layers and stop relying on layer names
        # use layer IDs and/or the underlying database table instead
        for layer in QgsProject.instance().requiredLayers():
            layer.nameChanged.connect(self.warning_layer_renamed)

        # get qgis version, warn the user if it's less than SUGGESTED_QGIS_VERSION
        qgis_version = Qgis.version()
        if qgis_version and qgis_version < SUGGESTED_QGIS_VERSION:
            QMessageBox.warning(
                None,
                self.tr("Warning"),
                self.tr(
                    "MzS Tools is designed to work with QGIS 3.26 or later. Please consider upgrading QGIS to the latest LTR version to avoid possible issues."
                ),
            )

    def warning_layer_renamed(self):
        """Function to handle the nameChanged signal for required layers."""
        QMessageBox.warning(
            None,
            self.tr("Warning"),
            self.tr(
                "It is not possible at the moment to rename a required MzS Tools layer! Please revert the name to avoid possible issues."
            ),
        )

    def connect_editing_signals(self):
        """connect editing signals to automatically set advanced overlap config for configured layer groups"""
        for layer in QgsProject.instance().mapLayers().values():
            if layer.name() in list(chain.from_iterable(NO_OVERLAPS_LAYER_GROUPS)):
                layer.editingStarted.connect(partial(self.set_advanced_editing_config, layer))
                layer.editingStopped.connect(self.reset_editing_config)

    def new_project(self):
        self.new_project_dlg.run_new_project_tool()
        self.connect_editing_signals()

    def edit_metadata(self):
        self.edit_metadata_dlg.run_edit_metadata_dialog()

    def help(self):
        self.info_dlg.help()

    def import_project(self):
        self.import_shp_dlg.importa_prog()

    def export_project(self):
        self.export_shp_dlg.esporta_prog()

    def copy_stab(self):
        self.ms_copy_dlg.copia()

    def set_advanced_editing_config(self, layer):
        proj = QgsProject.instance()
        # save the current config
        self.proj_snapping_config = proj.snappingConfig()
        self.proj_avoid_intersections_layers = proj.avoidIntersectionsLayers()
        self.topological_editing = proj.topologicalEditing()
        self.avoid_intersections_mode = proj.avoidIntersectionsMode()

        # just fail gracefully if something goes wrong
        try:
            snapping_config = QgsSnappingConfig(self.proj_snapping_config)

            # snapping_config.clearIndividualLayerSettings()
            snapping_config.setEnabled(True)
            snapping_config.setMode(QgsSnappingConfig.AdvancedConfiguration)
            snapping_config.setIntersectionSnapping(True)
            snapping_config.setTolerance(20)

            """
            TODO: deprecation warning when using IndividualLayerSettings constructor
            This works in QGIS but not here:

            proj = QgsProject.instance()
            proj_snapping_config = proj.snappingConfig()

            layer = iface.activeLayer()

            layer_settings = proj_snapping_config.individualLayerSettings(layer)
            layer_settings.setEnabled(True)
            layer_settings.setType(QgsSnappingConfig.Vertex)
            layer_settings.setTolerance(20)
            layer_settings.setUnits(QgsTolerance.ProjectUnits)

            proj_snapping_config.setIndividualLayerSettings(layer, layer_settings)
            #proj_snapping_config.addLayers([layer])

            proj.setSnappingConfig(proj_snapping_config)
            """
            layer_settings = QgsSnappingConfig.IndividualLayerSettings(
                True,
                QgsSnappingConfig.VertexFlag,
                20,
                QgsTolerance.ProjectUnits,
            )

            # set advanced overlap config for the layer and other layers in the same group
            for layer_group in NO_OVERLAPS_LAYER_GROUPS:
                if layer.name() in layer_group:
                    layers = [proj.mapLayersByName(layer_name)[0] for layer_name in layer_group]
                    for layer in layers:
                        snapping_config.setIndividualLayerSettings(layer, layer_settings)
                    proj.setAvoidIntersectionsLayers(layers)

            # actually set "follow advanced config" for overlaps
            proj.setAvoidIntersectionsMode(QgsProject.AvoidIntersectionsMode.AvoidIntersectionsLayers)

            # enable topological editing
            proj.setTopologicalEditing(True)

            # apply the new config
            proj.setSnappingConfig(snapping_config)

        except Exception as e:
            qgs_log(f"Error setting advanced editing config: {e}", level="error")

    def reset_editing_config(self):
        proj = QgsProject.instance()
        proj.setSnappingConfig(self.proj_snapping_config)
        proj.setAvoidIntersectionsMode(self.avoid_intersections_mode)
        proj.setAvoidIntersectionsLayers(self.proj_avoid_intersections_layers)
        proj.setTopologicalEditing(self.topological_editing)

    # def add_feature_or_record(self):
    #     proj = QgsProject.instance()

    #     snapping_config = proj.instance().snappingConfig()
    #     snapping_config.clearIndividualLayerSettings()

    #     snapping_config.setTolerance(20.0)
    #     snapping_config.setMode(QgsSnappingConfig.AdvancedConfiguration)

    #     DIZIO_LAYER = {
    #         "Zone stabili liv 1": "Zone instabili liv 1",
    #         "Zone instabili liv 1": "Zone stabili liv 1",
    #         "Zone stabili liv 2": "Zone instabili liv 2",
    #         "Zone instabili liv 2": "Zone stabili liv 2",
    #         "Zone stabili liv 3": "Zone instabili liv 3",
    #         "Zone instabili liv 3": "Zone stabili liv 3",
    #     }
    #     POLY_LYR = [
    #         "Unita' geologico-tecniche",
    #         "Instabilita' di versante",
    #         "Zone stabili liv 1",
    #         "Zone instabili liv 1",
    #         "Zone stabili liv 2",
    #         "Zone instabili liv 2",
    #         "Zone stabili liv 3",
    #         "Zone instabili liv 3",
    #     ]

    #     layer = self.iface.activeLayer()

    #     # Configure snapping
    #     if layer is not None:
    #         if layer.name() in POLY_LYR:
    #             # self.wait_dlg.show()
    #             for fc in proj.mapLayers().values():
    #                 if fc.name() in POLY_LYR:
    #                     layer_settings = QgsSnappingConfig.IndividualLayerSettings(
    #                         True,
    #                         QgsSnappingConfig.VertexFlag,
    #                         20,
    #                         QgsTolerance.ProjectUnits,
    #                     )

    #                     snapping_config.setIndividualLayerSettings(fc, layer_settings)
    #                     snapping_config.setIntersectionSnapping(False)

    #             for chiave, valore in list(DIZIO_LAYER.items()):
    #                 if layer.name() == chiave:
    #                     other_layer = proj.mapLayersByName(valore)[0]

    #                     layer_settings = QgsSnappingConfig.IndividualLayerSettings(
    #                         True,
    #                         QgsSnappingConfig.VertexFlag,
    #                         20,
    #                         QgsTolerance.ProjectUnits,
    #                     )
    #                     snapping_config.setIndividualLayerSettings(layer, layer_settings)
    #                     snapping_config.setIndividualLayerSettings(other_layer, layer_settings)

    #                     snapping_config.setIntersectionSnapping(True)

    #                 elif layer.name() == "Unita' geologico-tecniche":
    #                     layer_settings = QgsSnappingConfig.IndividualLayerSettings(
    #                         True,
    #                         QgsSnappingConfig.VertexFlag,
    #                         20,
    #                         QgsTolerance.ProjectUnits,
    #                     )
    #                     snapping_config.setIndividualLayerSettings(layer, layer_settings)
    #                     snapping_config.setIntersectionSnapping(True)

    #                 elif layer.name() == "Instabilita' di versante":
    #                     layer_settings = QgsSnappingConfig.IndividualLayerSettings(
    #                         True,
    #                         QgsSnappingConfig.VertexFlag,
    #                         20,
    #                         QgsTolerance.ProjectUnits,
    #                     )
    #                     snapping_config.setIndividualLayerSettings(layer, layer_settings)
    #                     snapping_config.setIntersectionSnapping(True)

    #             layer.startEditing()
    #             self.iface.actionAddFeature().trigger()
    #             # self.wait_dlg.hide()

    #         else:
    #             layer.startEditing()
    #             self.iface.actionAddFeature().trigger()

    #         proj.setSnappingConfig(snapping_config)

    # def save(self):
    #     proj = QgsProject.instance()

    #     snapping_config = proj.snappingConfig()
    #     snapping_config.clearIndividualLayerSettings()

    #     snapping_config.setTolerance(20.0)
    #     snapping_config.setMode(QgsSnappingConfig.AllLayers)

    #     POLYGON_LYR = [
    #         "Unita' geologico-tecniche",
    #         "Instabilita' di versante",
    #         "Zone stabili liv 1",
    #         "Zone instabili liv 1",
    #         "Zone stabili liv 2",
    #         "Zone instabili liv 2",
    #         "Zone stabili liv 3",
    #         "Zone instabili liv 3",
    #     ]

    #     layer = self.iface.activeLayer()
    #     if layer is not None:
    #         if layer.name() in POLYGON_LYR:
    #             # self.wait_dlg.show()
    #             layers = proj.mapLayers().values()
    #             snapping_config = proj.snappingConfig()
    #             snapping_config.clearIndividualLayerSettings()
    #             snapping_config.setIntersectionSnapping(False)

    #             for fc in layers:
    #                 if fc.name() in POLYGON_LYR:
    #                     layer_settings = QgsSnappingConfig.IndividualLayerSettings(
    #                         True,
    #                         QgsSnappingConfig.VertexFlag,
    #                         20,
    #                         QgsTolerance.ProjectUnits,
    #                     )
    #                     snapping_config.setIndividualLayerSettings(fc, layer_settings)

    #             layer.commitChanges()
    #             # self.wait_dlg.hide()

    #         else:
    #             layer.commitChanges()

    def add_site(self):
        self.edit_win_dlg.edita()

    def tr(self, message):
        return QCoreApplication.translate("MzSTools", message)
