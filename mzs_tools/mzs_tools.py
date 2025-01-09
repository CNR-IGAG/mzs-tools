import configparser
import os
import shutil
import traceback
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
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QCoreApplication, QSettings, QTranslator
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QFileDialog, QMessageBox

from mzs_tools.core.mzs_project_manager import MzSProjectManager
from mzs_tools.gui.dlg_settings import PlgOptionsFactory
from mzs_tools.plugin_utils.logging import MzSToolsLogger
from mzs_tools.plugin_utils.settings import PlgOptionsManager

from .__about__ import DIR_PLUGIN_ROOT, __title__, __version__
from .constants import NO_OVERLAPS_LAYER_GROUPS, SUGGESTED_QGIS_VERSION
from .gui.dlg_create_project import DlgCreateProject
from .gui.dlg_metadata_edit import DlgMetadataEdit
from .gui.dlg_info import PluginInfo
from .tb_edit_win import edit_win
from .tb_esporta_shp import esporta_shp
from .tb_importa_shp import importa_shp

# from .editing.instab_l1 import instab_l1_form_init


class MzSTools:
    def __init__(self, iface):
        self.iface = iface
        self.log = MzSToolsLogger().log

        # keep track of connected layers to avoid reconnecting signals
        self.editing_signals_connected_layers = {}

        # initialize locale
        try:
            locale = QSettings().value("locale/userLocale", "en", type=str)[0:2]
        except Exception:
            locale = "en"
        locale_path = DIR_PLUGIN_ROOT / "i18n" / "MzSTools_{}.qm".format(locale)
        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(str(locale_path))
            QCoreApplication.installTranslator(self.translator)

        # install or update svg symbols in current QGIS profile
        self.check_svg_cache()

        self.dlg_create_project = None
        self.dlg_metadata_edit = None
        self.info_dlg = PluginInfo(self.iface.mainWindow())
        self.import_shp_dlg = importa_shp()
        self.export_shp_dlg = esporta_shp()
        self.edit_win_dlg = edit_win()

        self.actions = []
        self.menu = self.tr("&MzS Tools")
        self.toolbar = self.iface.addToolBar("MzSTools")
        self.toolbar.setObjectName("MzSTools")

        self.import_shp_dlg.dir_input.clear()
        self.import_shp_dlg.pushButton_in.clicked.connect(self.select_input_fld_4)

        self.import_shp_dlg.tab_input.clear()
        self.import_shp_dlg.pushButton_tab.clicked.connect(self.select_tab_fld_4)

        self.export_shp_dlg.dir_output.clear()
        self.export_shp_dlg.pushButton_out.clicked.connect(self.select_output_fld_5)

        QgsSettings().setValue("qgis/enableMacros", 3)

        # create the project manager
        self.prj_manager = MzSProjectManager.instance()
        self.prj_manager.init_manager()

        # connect to projectRead signal
        self.iface.projectRead.connect(self.check_project)

        # when an entirely new project is started, disable the actions that require an open mzs tools project
        # https://qgis.org/pyqgis/master/gui/QgisInterface.html#qgis.gui.QgisInterface.newProjectCreated
        self.iface.newProjectCreated.connect(self.on_new_qgis_project)

        # load form init functions
        # self.instab_l1_form_init = instab_l1_form_init

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
        # settings page within the QGIS preferences menu
        self.options_factory = PlgOptionsFactory()
        self.iface.registerOptionsWidgetFactory(self.options_factory)

        icon_path2 = DIR_PLUGIN_ROOT / "img" / "ico_nuovo_progetto.png"
        icon_path3 = DIR_PLUGIN_ROOT / "img" / "ico_info.png"
        icon_path4 = DIR_PLUGIN_ROOT / "img" / "ico_importa.png"
        icon_path5 = DIR_PLUGIN_ROOT / "img" / "ico_esporta.png"
        icon_path10 = DIR_PLUGIN_ROOT / "img" / "ico_xypoint.png"

        self.add_action(
            str(icon_path2),
            text=self.tr("New project"),
            callback=self.open_dlg_create_project,
            parent=self.iface.mainWindow(),
        )

        self.add_action(
            str(icon_path2),
            text=self.tr("test"),
            callback=self.prj_manager.add_default_editing_layers,
            parent=self.iface.mainWindow(),
        )

        self.action_edit_metadata = self.add_action(
            QgsApplication.getThemeIcon("/mActionEditHtml.svg"),
            enabled_flag=self.prj_manager and self.prj_manager.is_mzs_project,
            text=self.tr("Edit project metadata"),
            callback=self.open_dlg_metadata_edit,
            parent=self.iface.mainWindow(),
        )

        self.toolbar.addSeparator()

        self.add_action(
            str(icon_path4),
            text=self.tr("Import project folder from geodatabase"),
            callback=self.import_project,
            parent=self.iface.mainWindow(),
        )

        self.add_action(
            str(icon_path5),
            text=self.tr("Export geodatabase to project folder"),
            callback=self.export_project,
            parent=self.iface.mainWindow(),
        )

        self.add_action(
            str(icon_path10),
            text=self.tr('Add "Sito puntuale" using XY coordinates'),
            callback=self.add_site,
            parent=self.iface.mainWindow(),
        )

        self.toolbar.addSeparator()

        self.add_action(
            QgsApplication.getThemeIcon("/mActionOptions.svg"),
            text=self.tr("MzS Tools Settings"),
            callback=lambda: self.iface.showOptionsDialog(currentPage="mOptionsPage{}".format(__title__)),
            parent=self.iface.mainWindow(),
        )

        self.help_action = self.add_action(
            str(icon_path3),
            text=self.tr("MzS Tools Help"),
            callback=self.info_dlg.show,
            parent=self.iface.mainWindow(),
        )
        # add the help action to the QGIS plugin help menu
        self.iface.pluginHelpMenu().addAction(self.help_action)

    def unload(self):
        # close db connections
        if self.prj_manager:
            self.prj_manager.cleanup_db_connection()

        # Clean up preferences panel in QGIS settings
        self.iface.unregisterOptionsWidgetFactory(self.options_factory)

        for action in self.actions:
            self.iface.removePluginDatabaseMenu(self.tr("&MzS Tools"), action)
            self.iface.removeToolBarIcon(action)
        del self.toolbar

        # remove the help action from the QGIS plugin help menu
        self.iface.pluginHelpMenu().removeAction(self.help_action)
        del self.help_action

        # disconnect QgisInterface signals
        self.iface.projectRead.disconnect(self.check_project)
        self.iface.newProjectCreated.disconnect(self.on_new_qgis_project)

    def on_new_qgis_project(self):
        self.action_edit_metadata.setEnabled(False)

    def open_dlg_create_project(self):
        # check if there is a project already open
        if QgsProject.instance().fileName():
            QMessageBox.warning(
                self.iface.mainWindow(),
                self.tr("MzS Tools"),
                self.tr("Close the current project before creating a new one."),
            )
            return
        if self.dlg_create_project is None:
            self.dlg_create_project = DlgCreateProject(self.iface.mainWindow())
        result = self.dlg_create_project.exec()
        if result:
            dir_out = self.dlg_create_project.output_dir_widget.lineEdit().text()
            comune_name = self.dlg_create_project.comune_line_edit.text().split(" (")[0]
            cod_istat = self.dlg_create_project.cod_istat_line_edit.text()
            study_author = self.dlg_create_project.study_author_line_edit.text()
            author_email = self.dlg_create_project.author_email_line_edit.text()
            self.log(
                f"Creating new MzS Tools project in {dir_out} for {comune_name} ({cod_istat}). Author: {study_author} ({author_email})"
            )
            project_path = None
            try:
                # new_project = self.create_project(dir_out)
                # reload the project
                # self.iface.addProject(new_project)
                project_path = self.prj_manager.create_project_from_template(
                    comune_name, cod_istat, study_author, author_email, dir_out
                )
            except Exception as e:
                err_msg = self.tr("Error during project creation")
                self.log(f"{err_msg}: {e} ", log_level=2)
                self.log(traceback.format_exc(), log_level=2)
                QMessageBox.critical(None, "MzS Tools error", f'{err_msg}:\n"{str(e)}"')
                # cleanup
                QgsProject.instance().clear()
                prj_path = Path(dir_out) / f"{cod_istat}_{self.prj_manager.sanitize_comune_name(comune_name)}"
                if prj_path.exists():
                    self.log(f"Removing incomplete project in {prj_path}")
                    shutil.rmtree(prj_path)

            if project_path:
                self.log(f"Project created successfully in {project_path}")
                QMessageBox.information(None, self.tr("Notice"), self.tr("The project has been created successfully."))

    def open_dlg_metadata_edit(self):
        # self.edit_metadata_dlg.run_edit_metadata_dialog()
        if not self.prj_manager.is_mzs_project:
            self.log(self.tr("The tool must be used within an opened MS project!"), log_level=1)
            return

        if self.dlg_metadata_edit is None:
            self.dlg_metadata_edit = DlgMetadataEdit(self.iface.mainWindow())

        # self.dlg_metadata_edit.set_prj_manager(self.prj_manager)

        result = self.dlg_metadata_edit.exec()
        if result:
            self.dlg_metadata_edit.save_data()

    def import_project(self):
        self.import_shp_dlg.importa_prog()

    def export_project(self):
        self.export_shp_dlg.esporta_prog()

    def add_site(self):
        self.edit_win_dlg.edita()

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

    def check_svg_cache(self):
        self.log("Checking svg symbols...", log_level=4)
        dir_svg_input = DIR_PLUGIN_ROOT / "img" / "svg"

        current_qgis_profile_name = None
        try:
            # only in QGIS >= 3.30
            current_qgis_profile_name = self.iface.userProfileManager().userProfile().name()
        except Exception:
            config = configparser.ConfigParser()
            profiles_directory = Path(QgsApplication.qgisSettingsDirPath()).parent
            config.read(f"{profiles_directory}/profiles.ini")
            current_qgis_profile_name = config["core"]["defaultProfile"]

        dir_svg_output = DIR_PLUGIN_ROOT.parent.parent.parent.parent / current_qgis_profile_name / "svg"

        # qgs_log(f"Profile: {current_qgis_profile_name} - Output dir: {dir_svg_output} - Input dir: {dir_svg_input}")

        if not dir_svg_output.exists():
            self.log(f"Copying svg symbols in {dir_svg_output}")
            shutil.copytree(dir_svg_input, dir_svg_output)
        else:
            # copy only new or updated files
            for file in dir_svg_input.glob("*.svg"):
                dest = dir_svg_output / file.name
                if not dest.exists() or file.stat().st_mtime > dest.stat().st_mtime:
                    self.log(f"Copying {file} to {dest}")
                    shutil.copy2(file, dest)

    def check_project(self):
        """
        Initialize the MzSProjectManager and return immediately if the project is not a MzSTools project.
        If the project is a MzSTools project:
        - check if the project is outdated and ask the user to start the update process
        - connect editing signals to automatically set cross-layer no-overlap rules when needed and
          revert to the original config when editing stops
        - connect layer nameChanged signal to warn the user when renaming required layers
        - warn the user if the QGIS version is less than SUGGESTED_QGIS_VERSION defined in constants.py
        """
        # initialize the project manager
        self.prj_manager.init_manager()

        self.action_edit_metadata.setEnabled(self.prj_manager.is_mzs_project)

        if not self.prj_manager.is_mzs_project:
            return

        if self.prj_manager.project_updateable:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Question)
            msg_box.setWindowTitle(self.tr("MzS Tools - Project Update"))
            msg_box.setText(
                self.tr(
                    f"The project will be updated from version {self.prj_manager.project_version} to version {__version__}."
                )
            )
            msg_box.setInformativeText(self.tr("Do you want to proceed?"))
            msg_box.setDetailedText(
                self.tr(
                    "It is possible to cancel the update process and continue using the current project version, "
                    "but it is highly recommended to proceed with the update to avoid possible issues.\n"
                    "The QGIS project content (layers, styles, symbols, print layout) will be updated to the latest plugin version.\n"
                    "The database will be updated if necessary but all data will be preserved.\n"
                    "The current project will be saved in a backup directory before the update."
                )
            )
            msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msg_box.setDefaultButton(QMessageBox.Yes)

            response = msg_box.exec_()
            if response == QMessageBox.Yes:
                self.log("Starting project update process.", log_level=1)
                self.prj_manager.backup_project()
                self.prj_manager.update_db()
                self.prj_manager.update_project_from_template()
                return
            else:
                self.log("Project update process cancelled.", log_level=1)

        self.connect_editing_signals()

        # connect to layer nameChanged signal to warn the user when renaming required layers
        # TODO: find a better way to protect required layers and stop relying on layer names
        # use layer IDs and/or the underlying database table instead
        for layer in QgsProject.instance().requiredLayers():
            layer.nameChanged.disconnect()
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
                if layer not in self.editing_signals_connected_layers:
                    layer.editingStarted.connect(partial(self.set_advanced_editing_config, layer))
                    layer.editingStopped.connect(self.reset_editing_config)
                    self.editing_signals_connected_layers[layer] = (
                        self.set_advanced_editing_config,
                        self.reset_editing_config,
                    )
            # test for setting the ui form with qgis.core.QgsEditFormConfig.setUiForm

    #         if layer.name() == "Zone instabili liv 1":
    #             layer.editingStarted.connect(partial(self.set_ui_file, layer, "instab_l1.ui"))

    # def set_ui_file(self, layer: QgsVectorLayer, ui_file_name: str):
    #     form_config = layer.editFormConfig()
    #     ui_path = DIR_PLUGIN_ROOT / "editing" / ui_file_name
    #     self.log(f"Setting UI form for layer {layer.name()}: {ui_path}")
    #     form_config.setUiForm(str(ui_path))
    #     layer.setEditFormConfig(form_config)

    def disconnect_editing_signals(self):
        """Disconnect specific editing signals."""
        for layer, (start_func, stop_func) in self.editing_signals_connected_layers.items():
            layer.editingStarted.disconnect(start_func)
            layer.editingStopped.disconnect(stop_func)
        self.editing_signals_connected_layers.clear()

    def set_advanced_editing_config(self, layer):
        # settings = get_settings()
        # if not settings.get(AUTO_ADVANCED_EDITING_KEY, True):
        #     return

        auto_advanced_editing_setting = PlgOptionsManager.get_value_from_key(
            "auto_advanced_editing", default=True, exp_type=bool
        )
        if not auto_advanced_editing_setting:
            return

        self.log("Setting advanced editing options")
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
            self.log(f"Error setting advanced editing config: {e}", log_level=2)

    def reset_editing_config(self):
        # settings = get_settings()
        # if not settings.get(AUTO_ADVANCED_EDITING_KEY, True):
        #     return
        auto_advanced_editing_setting = PlgOptionsManager.get_value_from_key(
            "auto_advanced_editing", default=True, exp_type=bool
        )
        if not auto_advanced_editing_setting:
            return

        self.log("Resetting advanced editing settings")

        try:
            proj = QgsProject.instance()
            proj.setSnappingConfig(self.proj_snapping_config)
            proj.setAvoidIntersectionsMode(self.avoid_intersections_mode)
            proj.setAvoidIntersectionsLayers(self.proj_avoid_intersections_layers)
            proj.setTopologicalEditing(self.topological_editing)
        except Exception as e:
            self.log(f"Error resetting advanced editing config: {e}", log_level=2)

    def tr(self, message):
        return QCoreApplication.translate("MzSTools", message)
