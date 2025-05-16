import json
import os
import shutil
import traceback
from functools import partial
from pathlib import Path

from qgis.core import (
    QgsApplication,
    QgsProject,
)
from qgis.gui import QgisInterface
from qgis.PyQt.QtCore import QCoreApplication, QSettings, QTimer, QTranslator
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import (
    QAction,
    QFileDialog,
    QMenu,
    QMessageBox,
    QToolButton,
)

from .__about__ import DIR_PLUGIN_ROOT, __title__, __version__
from .core.mzs_project_manager import MzSProjectManager
from .gui.dlg_create_project import DlgCreateProject
from .gui.dlg_export_data import DlgExportData
from .gui.dlg_fix_layers import DlgFixLayers
from .gui.dlg_import_data import DlgImportData
from .gui.dlg_info import PluginInfo
from .gui.dlg_load_ogc_services import DlgLoadOgcServices
from .gui.dlg_manage_attachments import DlgManageAttachments
from .gui.dlg_metadata_edit import DlgMetadataEdit
from .gui.dlg_settings import PlgOptionsFactory
from .plugin_utils.logging import MzSToolsLogger


class MzSTools:
    def __init__(self, iface):
        self.iface: QgisInterface = iface
        self.log = MzSToolsLogger.log

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

        self.dlg_create_project = None
        self.dlg_metadata_edit = None
        self.info_dlg = PluginInfo(self.iface.mainWindow())
        self.dlg_import_data = None
        self.dlg_export_data = None

        self.actions = []
        self.menu = self.tr("&MzS Tools")
        self.toolbar = self.iface.addToolBar("MzSTools")
        self.toolbar.setObjectName("MzSTools")

        # QgsSettings().setValue("qgis/enableMacros", 3)

        # create the project manager instance
        self.prj_manager = MzSProjectManager.instance()
        # immediately init the manager to be able to set some gui elements (actions)
        # even when reloading the plugin in an already open project
        self.prj_manager.init_manager()

        # connect to projectRead signal
        self.iface.projectRead.connect(self.check_project)

        # check project also when clicking on "New project" in the QGIS interface, to reinit the project manager
        # and set some gui elements (actions) even when reloading the plugin in an already open project
        # https://qgis.org/pyqgis/master/gui/QgisInterface.html#qgis.gui.QgisInterface.newProjectCreated
        self.iface.newProjectCreated.connect(self.check_project)

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

        ico_nuovo_progetto = DIR_PLUGIN_ROOT / "resources" / "icons" / "ico_nuovo_progetto.png"
        ico_info = DIR_PLUGIN_ROOT / "resources" / "icons" / "ico_info.png"
        ico_importa = DIR_PLUGIN_ROOT / "resources" / "icons" / "ico_importa.png"
        ico_esporta = DIR_PLUGIN_ROOT / "resources" / "icons" / "ico_esporta.png"

        enabled_flag = (self.prj_manager and self.prj_manager.is_mzs_project) or False

        project_menu_button = QToolButton()
        project_menu_button.setIcon(QIcon(str(ico_nuovo_progetto)))
        project_menu_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        project_menu_button.setToolTip(self.tr("Tools for managing MzS Tools project and database"))
        menu_project = QMenu()
        self.toolbar.addWidget(project_menu_button)

        self.new_project_action = self.add_action(
            str(ico_nuovo_progetto),
            text=self.tr("New project"),
            status_tip=self.tr("Create a new MzS Tools project for the provided municipality"),
            callback=self.open_dlg_create_project,
            parent=self.iface.mainWindow(),
            add_to_toolbar=False,
        )
        menu_project.addAction(self.new_project_action)

        self.open_standard_project_action = self.add_action(
            QgsApplication.getThemeIcon("mIconDataDefine.svg"),
            text=self.tr("Open a 'Standard MS' project"),
            status_tip=self.tr(
                "Open an existing 'Standard MS' project and import the data in a new MzS Tools project"
            ),
            callback=partial(self.open_dlg_create_project, import_data=True),
            parent=self.iface.mainWindow(),
            add_to_toolbar=False,
        )
        menu_project.addAction(self.open_standard_project_action)

        menu_project.addSeparator()

        self.backup_db_action = self.add_action(
            QgsApplication.getThemeIcon("mActionNewFileGeodatabase.svg"),
            text=self.tr("Backup database"),
            status_tip=self.tr("Backup the current MzS Tools project database"),
            callback=self.on_backup_db_action,
            parent=self.iface.mainWindow(),
            add_to_toolbar=False,
        )
        menu_project.addAction(self.backup_db_action)

        self.backup_project_action = self.add_action(
            QgsApplication.getThemeIcon("mIconAuxiliaryStorage.svg"),
            text=self.tr("Backup project"),
            status_tip=self.tr("Backup the entire MzS Tools project"),
            callback=self.on_backup_project_action,
            parent=self.iface.mainWindow(),
            add_to_toolbar=False,
        )
        menu_project.addAction(self.backup_project_action)

        self.check_attachments_action = self.add_action(
            QgsApplication.getThemeIcon("mActionFolder.svg"),
            text=self.tr("Check file attachments"),
            status_tip=self.tr("Check, collect and consolidate file attachments"),
            callback=self.on_check_attachments_action,
            parent=self.iface.mainWindow(),
            add_to_toolbar=False,
        )
        menu_project.addAction(self.check_attachments_action)

        menu_project.addSeparator()

        self.edit_metadata_action = self.add_action(
            QgsApplication.getThemeIcon("/mActionEditHtml.svg"),
            enabled_flag=enabled_flag,
            text=self.tr("Edit project metadata"),
            callback=self.open_dlg_metadata_edit,
            parent=self.iface.mainWindow(),
            add_to_toolbar=False,
        )
        menu_project.addAction(self.edit_metadata_action)

        project_menu_button.setMenu(menu_project)

        layers_menu_button = QToolButton()
        layers_menu_button.setIcon(QgsApplication.getThemeIcon("mIconLayerTree.svg"))
        layers_menu_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        layers_menu_button.setToolTip(self.tr("Tools for managing MzS Tools QGIS layers"))
        menu_layers = QMenu()
        self.toolbar.addWidget(layers_menu_button)
        self.check_project_action = self.add_action(
            QgsApplication.getThemeIcon("mIconQgsProjectFile.svg"),
            enabled_flag=enabled_flag,
            text=self.tr("Check the integrity of the current MzS Tools QGIS project"),
            status_tip=self.tr("Check the current MzS Tools QGIS project for common issues"),
            callback=self.check_project_issues,
            parent=self.iface.mainWindow(),
            add_to_toolbar=False,
        )
        menu_layers.addAction(self.check_project_action)
        self.add_default_layers_action = self.add_action(
            QgsApplication.getThemeIcon("mActionAddLayer.svg"),
            enabled_flag=enabled_flag,
            text=self.tr("Replace/repair default MzS Tools project layers"),
            status_tip=self.tr("Replace or repair the default MzS Tools project layers to fix common issues"),
            callback=self.open_dlg_fix_layers,
            parent=self.iface.mainWindow(),
            add_to_toolbar=False,
        )
        menu_layers.addAction(self.add_default_layers_action)

        self.load_default_print_layouts_action = self.add_action(
            QgsApplication.getThemeIcon("mIconLayout.svg"),
            enabled_flag=enabled_flag,
            text=self.tr("Load default MzS Tools print layouts"),
            status_tip=self.tr("Load the default MzS Tools print layouts, existing layouts will be preserved"),
            callback=self.on_load_default_print_layouts,
            parent=self.iface.mainWindow(),
            add_to_toolbar=False,
        )
        menu_layers.addAction(self.load_default_print_layouts_action)

        menu_layers.addSeparator()

        self.add_ogc_services_action = self.add_action(
            QgsApplication.getThemeIcon("mActionAddWmsLayer.svg"),
            enabled_flag=enabled_flag,
            text=self.tr("Load WMS/WFS services"),
            status_tip=self.tr(
                "Load useful OGC services (such as regional CTR and MS services) in the current project"
            ),
            callback=self.open_dlg_load_ogc_services,
            parent=self.iface.mainWindow(),
            add_to_toolbar=False,
        )
        menu_layers.addAction(self.add_ogc_services_action)
        layers_menu_button.setMenu(menu_layers)

        self.toolbar.addSeparator()

        self.import_data_action = self.add_action(
            str(ico_importa),
            enabled_flag=enabled_flag,
            text=self.tr("Import project folder from geodatabase"),
            # callback=self.import_project,
            callback=self.open_dlg_import_data,
            parent=self.iface.mainWindow(),
        )

        self.export_data_action = self.add_action(
            str(ico_esporta),
            enabled_flag=enabled_flag,
            text=self.tr("Export data to Ms standard data structure"),
            callback=self.open_dlg_export_data,
            parent=self.iface.mainWindow(),
        )

        self.toolbar.addSeparator()

        self.settings_action = self.add_action(
            QgsApplication.getThemeIcon("/mActionOptions.svg"),
            text=self.tr("MzS Tools Settings"),
            callback=lambda: self.iface.showOptionsDialog(currentPage="mOptionsPage{}".format(__title__)),
            parent=self.iface.mainWindow(),
        )

        self.help_action = self.add_action(
            str(ico_info),
            text=self.tr("MzS Tools Help"),
            callback=self.info_dlg.show,
            parent=self.iface.mainWindow(),
        )
        # add the help action to the QGIS plugin help menu
        self.iface.pluginHelpMenu().addAction(self.help_action)

        self.check_project()

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
        self.iface.newProjectCreated.disconnect(self.check_project)

    def enable_plugin_actions(self, enabled: bool = False):
        always_enabled_actions = [
            self.new_project_action,
            self.open_standard_project_action,
            self.settings_action,
            self.help_action,
        ]
        for action in self.actions:
            if action not in always_enabled_actions:
                action.setEnabled(enabled)

    # action callbacks --------------------------------------------------------

    def open_dlg_create_project(self, import_data=False):
        # check if there is a project already open
        if QgsProject.instance().fileName():
            QMessageBox.warning(
                self.iface.mainWindow(),
                self.tr("MzS Tools"),
                self.tr("Close the current project before creating a new one."),
            )
            return

        if import_data:
            QMessageBox.information(
                self.iface.mainWindow(),
                self.tr("MzS Tools"),
                self.tr(
                    "This tool allows to open an existing Seismic Microzonation project based on italian 'Standard MS' "
                    "by creating a new MzS Tools project for the provided municipality and then importing the data from the 'Standard MS' project.\n\n"
                    "The original project data format must be: \n\n"
                    "- Microsoft Access database, SQLite database or CSV files ('CdI_Tabelle')\n"
                    "- Shapefiles (vector layers such as 'Instab', 'Geotec', etc.)"
                ),
            )

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
                project_path = self.prj_manager.create_project(
                    comune_name, cod_istat, study_author, author_email, dir_out
                )
            except Exception as e:
                err_msg = self.tr("Error during project creation")
                self.log(f"{err_msg}: {e} ", log_level=2)
                self.log(traceback.format_exc(), log_level=2)
                QMessageBox.critical(None, self.tr("MzS Tools error"), f'{err_msg}:\n"{str(e)}"')
                # cleanup
                QgsProject.instance().clear()
                prj_path = Path(dir_out) / f"{cod_istat}_{self.prj_manager.sanitize_comune_name(comune_name)}"
                if prj_path.exists():
                    self.log(f"Removing incomplete project in {prj_path}")
                    shutil.rmtree(prj_path)
                return

            if import_data:
                self.open_dlg_import_data()

            elif project_path:
                msg = self.tr("Project created successfully in:")
                self.log(f"{msg} {project_path}", push=True, duration=0)

    def open_dlg_load_ogc_services(self):
        self.dlg_load_ogc_layers = DlgLoadOgcServices(self.iface.mainWindow())
        self.dlg_load_ogc_layers.exec()

    def open_dlg_fix_layers(self):
        if not self.prj_manager.is_mzs_project:
            self.log(self.tr("The tool must be used within an opened MS project!"), log_level=1)
            return

        self.dlg_fix_layers = DlgFixLayers(self.iface.mainWindow())
        self.dlg_fix_layers.exec()

    def check_project_issues(self):
        self.prj_manager.check_project_structure()
        if self.prj_manager.project_issues:
            self.report_project_issues()
        else:
            QMessageBox.information(
                None,
                self.tr("MzS Tools - Project Issues"),
                self.tr("No issues found in the current project."),
            )

    def on_load_default_print_layouts(self):
        button = QMessageBox.question(
            self.iface.mainWindow(),
            self.tr("MzS Tools - Load default print layouts"),
            self.tr(
                "Load the default MzS Tools print layouts. The existing layouts will be preserved.\n\nDo you want to proceed?"
            ),
        )
        if button == QMessageBox.StandardButton.Yes:
            self.prj_manager.backup_print_layouts(backup_label="backup", backup_timestamp=True)
            self.prj_manager.load_print_layouts()
            self.log(self.tr("Print layouts loaded."), log_level=3, push=True, duration=0)

    def open_dlg_import_data(self):
        if self.dlg_import_data is None:
            self.dlg_import_data = DlgImportData(self.iface.mainWindow())

        indagini_count = self.prj_manager.count_indagini_data()
        # self.log(f"Indagini data count: {indagini_count}", log_level=4)
        prj_contains_indagini_data = False
        sequences_gt_0 = False
        for tab, count in indagini_count.items():
            # count[0] is the table rows count, count[1] is the sequence for the primary key
            if count[0] > 0:
                prj_contains_indagini_data = True
            if count[1] > 0:
                sequences_gt_0 = True

        if prj_contains_indagini_data:
            title = self.tr("Warning!")
            message = self.tr(
                "The project already contains 'Indagini' data (siti, indagini, parametri, curve)."
                "\n\nThe imported data numeric IDs (and composite ID such as 'ID_SPU', 'ID_INDPU', etc.), will be different from the original data."
                "\n\nTo preserve the original IDs, use a new, empy project, or delete all punctual and linear sites before running the import tool."
            )
            QMessageBox.warning(self.iface.mainWindow(), title, message)
            self.dlg_import_data.reset_sequences = False
        else:
            self.dlg_import_data.reset_sequences = sequences_gt_0

        self.dlg_import_data.exec()

    def open_dlg_export_data(self):
        if self.dlg_export_data is None:
            self.dlg_export_data = DlgExportData(self.iface.mainWindow())

        self.dlg_export_data.exec()

    def on_backup_db_action(self):
        try:
            backup_path = self.prj_manager.backup_database()
        except Exception as e:
            err_msg = self.tr("Error during database backup:")
            self.log(f"{err_msg} {e}", log_level=2)
            self.log(traceback.format_exc(), log_level=2)
            QMessageBox.critical(None, self.tr("MzS Tools error"), f"{err_msg}\n{str(e)}")
            return

        if backup_path:
            msg = self.tr("Database backup created in:")
            self.log(f"{msg} {backup_path}", log_level=3, push=True, duration=10)

    def on_backup_project_action(self):
        backup_dir = QFileDialog.getExistingDirectory(
            self.iface.mainWindow(),
            self.tr("Select backup directory"),
            str(self.prj_manager.project_path.parent),
            QFileDialog.Option.ShowDirsOnly,
        )
        if not backup_dir:
            return

        msg = None
        if backup_dir == str(self.prj_manager.project_path):
            msg = self.tr(
                "The backup directory cannot be the same as the project directory. Select a different directory."
            )
            QMessageBox.warning(None, self.tr("Warning"), msg)
            return
        if (Path(backup_dir) / "db" / "indagini.sqlite").exists():
            msg = self.tr(
                "The selected directory seems to contain an MzS Tools project. Select a different directory."
            )
            QMessageBox.warning(None, self.tr("Warning"), msg)
            return

        try:
            backup_path = self.prj_manager.backup_project(Path(backup_dir))
        except Exception as e:
            err_msg = self.tr("Error during project backup:")
            self.log(f"{err_msg} {e}", log_level=2)
            self.log(traceback.format_exc(), log_level=2)
            QMessageBox.critical(None, self.tr("MzS Tools error"), f"{err_msg}\n{str(e)}")
            return

        if backup_path:
            msg = self.tr("Project backup created in:")
            self.log(f"{msg} {backup_path}", log_level=3, push=True, duration=10)

    def on_check_attachments_action(self):
        self.dlg_manage_attachments = DlgManageAttachments(self.iface.mainWindow())
        self.dlg_manage_attachments.exec()

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

    # end action callbacks ----------------------------------------------------

    def check_project(self):
        """
        Initialize the MzSProjectManager and return immediately if the project is not a MzSTools project.
        If the project is a MzSTools project:
        - check if the project is outdated and ask the user to start the update process
        - report any issues in the project structure
        - connect editing signals to automatically set cross-layer no-overlap rules
        """
        # initialize the project manager
        self.prj_manager.init_manager()

        self.enable_plugin_actions(self.prj_manager.is_mzs_project and not self.prj_manager.project_updateable)

        if not self.prj_manager.is_mzs_project:
            return

        if self.prj_manager.project_updateable:
            # Use QTimer to delay the display of the message box until the project is fully loaded
            QTimer.singleShot(2000, self.show_project_update_dialog)
            return

        self.report_project_issues()
        self.prj_manager.connect_editing_signals()

    def show_project_update_dialog(self):
        """Display the project update confirmation dialog after a delay to ensure project is fully loaded."""
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Question)
        msg_box.setWindowTitle(self.tr("MzS Tools - Project Update"))
        msg_upd1 = self.tr("The project will be updated from version")
        msg_upd2 = self.tr("to version")
        msg_box.setText(f"{msg_upd1} {self.prj_manager.project_version} {msg_upd2} {__version__}.")
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
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setDefaultButton(QMessageBox.StandardButton.Yes)

        response = msg_box.exec()
        if response == QMessageBox.StandardButton.Yes:
            self.update_current_project()
        else:
            msg = self.tr(
                "Project update cancelled! Most of the plugin functionality will be disabled until the project is updated. "
                "It is highly recommended to update the project to avoid possible issues."
            )
            self.log(
                msg,
                log_level=1,
                push=True,
                duration=0,
                button=True,
                button_text=self.tr("Update project"),
                button_connect=self.update_current_project,
            )

    def report_project_issues(self):
        if not self.prj_manager.project_issues:
            return
        formatted_issues = json.dumps(self.prj_manager.project_issues, indent=4)
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setWindowTitle(self.tr("MzS Tools - Project Issues"))
        msg_box.setText(
            self.tr(
                "Some issues have been found in the current MzS Tools project.\n\n"
                "It is suggested to use the 'Replace/repair layers' function in the MzS Tools toolbar to try to solve the issues."
            )
        )
        # msg_box.setInformativeText(self.tr("Do you want to proceed?"))
        msg_box.setDetailedText(formatted_issues)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.setDefaultButton(QMessageBox.StandardButton.Ok)
        msg_box.exec()

    def update_current_project(self):
        if not self.prj_manager.is_mzs_project or not self.prj_manager.project_updateable:
            return
        self.log("Starting project update process.", log_level=1)
        self.iface.messageBar().clearWidgets()

        backup_path = self.prj_manager.backup_project()
        try:
            self.prj_manager.update_db()
            self.prj_manager.update_project()
        except Exception as e:
            err_msg = self.tr("An error occurred during project update.")
            self.log(f"{err_msg} {e}", log_level=2)
            self.log(traceback.format_exc(), log_level=2)
            backup_msg = self.tr("You can can find a backup of the project in: ") + "\n\n" + str(backup_path)
            QMessageBox.critical(None, self.tr("MzS Tools error"), f"{err_msg}\n\n{str(e)}\n\n{backup_msg}")
            return

    def tr(self, message):
        return QCoreApplication.translate("MzSTools", message)
