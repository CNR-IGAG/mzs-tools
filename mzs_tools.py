import os
import shutil

from qgis.core import (
    Qgis,
    QgsMessageLog,
    QgsProject,
    QgsSettings,
    QgsSnappingConfig,
    QgsTolerance,
)
from qgis.PyQt.QtCore import QCoreApplication, QSettings, QTranslator
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QFileDialog, qApp

from .tb_aggiorna_progetto import aggiorna_progetto
from .tb_copia_ms import copia_ms
from .tb_edit_win import edit_win
from .tb_esporta_shp import esporta_shp
from .tb_importa_shp import importa_shp
from .tb_info import info
from .tb_nuovo_progetto import nuovo_progetto

# from .tb_wait import wait


class MzSTools:
    def __init__(self, iface):

        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)

        # initialize locale
        try:
            locale = QSettings().value("locale/userLocale", "en", type=str)[0:2]
        except Exception:
            locale = "en"
        locale_path = os.path.join(
            self.plugin_dir, "i18n", "MzSTools_{}.qm".format(locale)
        )
        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # self.wait_dlg = wait()
        self.project_update_dlg = aggiorna_progetto()
        self.new_project_dlg = nuovo_progetto(self.iface)
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

        self.iface.projectRead.connect(self.check_project)

    def tr(self, message):
        return QCoreApplication.translate("MzSTools", message)

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
        icon_path8 = os.path.join(self.plugin_dir, "img", "ico_edita.png")
        icon_path9 = os.path.join(self.plugin_dir, "img", "ico_salva_edita.png")
        icon_path10 = os.path.join(self.plugin_dir, "img", "ico_xypoint.png")

        self.add_action(
            icon_path2,
            text=self.tr("New project"),
            callback=self.new_project,
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

        self.add_action(
            icon_path8,
            text=self.tr("Add feature or record"),
            callback=self.add_feature_or_record,
            parent=self.iface.mainWindow(),
        )

        self.add_action(
            icon_path9,
            text=self.tr("Save"),
            callback=self.save,
            parent=self.iface.mainWindow(),
        )

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
        out_dir = QFileDialog.getExistingDirectory(
            self.new_project_dlg, "", "", QFileDialog.ShowDirsOnly
        )
        self.new_project_dlg.dir_output.setText(out_dir)

    def select_input_fld_4(self):
        in_dir = QFileDialog.getExistingDirectory(
            self.import_shp_dlg, "", "", QFileDialog.ShowDirsOnly
        )
        self.import_shp_dlg.dir_input.setText(in_dir)

    def select_tab_fld_4(self):
        tab_dir = QFileDialog.getExistingDirectory(
            self.import_shp_dlg, "", "", QFileDialog.ShowDirsOnly
        )
        self.import_shp_dlg.tab_input.setText(tab_dir)

    def select_input_fld_5(self):
        in_dir = QFileDialog.getExistingDirectory(
            self.export_shp_dlg, "", "", QFileDialog.ShowDirsOnly
        )
        self.export_shp_dlg.dir_input.setText(in_dir)

    def select_output_fld_5(self):
        out_dir = QFileDialog.getExistingDirectory(
            self.export_shp_dlg, "", "", QFileDialog.ShowDirsOnly
        )
        self.export_shp_dlg.dir_output.setText(out_dir)

    def check_project(self):
        percorso = QgsProject.instance().homePath()
        dir_output = "/".join(percorso.split("/")[:-1])
        nome = percorso.split("/")[-1]

        # detect MzSTools project
        if os.path.exists(os.path.join(percorso, "progetto")) and os.path.exists(
            os.path.join(percorso, "progetto", "versione.txt")
        ):
            QgsMessageLog.logMessage("MzSTools project detected", "MzSTools", Qgis.Info)
            QgsMessageLog.logMessage("Checking svg symbols...", "MzSTools", Qgis.Info)

            dir_svg_input = os.path.join(self.plugin_dir, "img", "svg")
            dir_svg_output = self.plugin_dir.split("python")[0] + "svg"

            if not os.path.exists(dir_svg_output):
                QgsMessageLog.logMessage(
                    f"Copying svg symbols in {dir_svg_output}", "MzSTools", Qgis.Info
                )
                shutil.copytree(dir_svg_input, dir_svg_output)
            else:
                QgsMessageLog.logMessage(
                    f"Updating svg symbols in {dir_svg_output}", "MzSTools", Qgis.Info
                )
                src_files = os.listdir(dir_svg_input)
                for file_name in src_files:
                    full_file_name = os.path.join(dir_svg_input, file_name)
                    if os.path.isfile(full_file_name):
                        shutil.copy(full_file_name, dir_svg_output)

            QgsMessageLog.logMessage(
                "Comparing project and plugin versions", "MzSTools", Qgis.Info
            )
            vers_data = os.path.join(
                os.path.dirname(QgsProject.instance().fileName()),
                "progetto",
                "versione.txt",
            )

            try:
                with open(vers_data, "r") as f:
                    proj_vers = f.read()
                    with open(
                        os.path.join(os.path.dirname(__file__), "versione.txt")
                    ) as nf:
                        new_proj_vers = nf.read()
                        if proj_vers < new_proj_vers:
                            QgsMessageLog.logMessage(
                                "Project needs updating!", "MzSTools", Qgis.Info
                            )
                            qApp.processEvents()
                            self.project_update_dlg.aggiorna(
                                percorso, dir_output, nome, proj_vers, new_proj_vers
                            )

            except Exception as ex:
                QgsMessageLog.logMessage(f"Error: {ex}", "MzSTools", Qgis.Critical)

    def new_project(self):
        self.new_project_dlg.nuovo()

    def help(self):
        self.info_dlg.help()

    def import_project(self):

        self.import_shp_dlg.importa_prog()

    def export_project(self):

        self.export_shp_dlg.esporta_prog()

    def copy_stab(self):

        self.ms_copy_dlg.copia()

    def add_feature_or_record(self):

        proj = QgsProject.instance()

        snapping_config = proj.instance().snappingConfig()
        snapping_config.clearIndividualLayerSettings()

        snapping_config.setTolerance(20.0)
        snapping_config.setMode(QgsSnappingConfig.AllLayers)

        DIZIO_LAYER = {
            "Zone stabili liv 1": "Zone instabili liv 1",
            "Zone instabili liv 1": "Zone stabili liv 1",
            "Zone stabili liv 2": "Zone instabili liv 2",
            "Zone instabili liv 2": "Zone stabili liv 2",
            "Zone stabili liv 3": "Zone instabili liv 3",
            "Zone instabili liv 3": "Zone stabili liv 3",
        }
        POLY_LYR = [
            "Unita' geologico-tecniche",
            "Instabilita' di versante",
            "Zone stabili liv 1",
            "Zone instabili liv 1",
            "Zone stabili liv 2",
            "Zone instabili liv 2",
            "Zone stabili liv 3",
            "Zone instabili liv 3",
        ]

        layer = self.iface.activeLayer()

        # Configure snapping
        if layer is not None:

            if layer.name() in POLY_LYR:

                # self.wait_dlg.show()
                for fc in proj.mapLayers().values():
                    if fc.name() in POLY_LYR:
                        layer_settings = QgsSnappingConfig.IndividualLayerSettings(
                            True,
                            QgsSnappingConfig.VertexFlag,
                            20,
                            QgsTolerance.ProjectUnits,
                        )

                        snapping_config.setIndividualLayerSettings(fc, layer_settings)
                        snapping_config.setIntersectionSnapping(False)

                for chiave, valore in list(DIZIO_LAYER.items()):
                    if layer.name() == chiave:
                        other_layer = proj.mapLayersByName(valore)[0]

                        layer_settings = QgsSnappingConfig.IndividualLayerSettings(
                            True,
                            QgsSnappingConfig.VertexFlag,
                            20,
                            QgsTolerance.ProjectUnits,
                        )
                        snapping_config.setIndividualLayerSettings(
                            layer, layer_settings
                        )
                        snapping_config.setIndividualLayerSettings(
                            other_layer, layer_settings
                        )

                        snapping_config.setIntersectionSnapping(True)

                    elif layer.name() == "Unita' geologico-tecniche":

                        layer_settings = QgsSnappingConfig.IndividualLayerSettings(
                            True,
                            QgsSnappingConfig.VertexFlag,
                            20,
                            QgsTolerance.ProjectUnits,
                        )
                        snapping_config.setIndividualLayerSettings(
                            layer, layer_settings
                        )
                        snapping_config.setIntersectionSnapping(True)

                    elif layer.name() == "Instabilita' di versante":

                        layer_settings = QgsSnappingConfig.IndividualLayerSettings(
                            True,
                            QgsSnappingConfig.VertexFlag,
                            20,
                            QgsTolerance.ProjectUnits,
                        )
                        snapping_config.setIndividualLayerSettings(
                            layer, layer_settings
                        )
                        snapping_config.setIntersectionSnapping(True)

                layer.startEditing()
                self.iface.actionAddFeature().trigger()
                # self.wait_dlg.hide()

            else:
                layer.startEditing()
                self.iface.actionAddFeature().trigger()

    def save(self):

        proj = QgsProject.instance()

        snapping_config = proj.snappingConfig()
        snapping_config.clearIndividualLayerSettings()

        snapping_config.setTolerance(20.0)
        snapping_config.setMode(QgsSnappingConfig.AllLayers)

        POLYGON_LYR = [
            "Unita' geologico-tecniche",
            "Instabilita' di versante",
            "Zone stabili liv 1",
            "Zone instabili liv 1",
            "Zone stabili liv 2",
            "Zone instabili liv 2",
            "Zone stabili liv 3",
            "Zone instabili liv 3",
        ]

        layer = self.iface.activeLayer()
        if layer is not None:
            if layer.name() in POLYGON_LYR:

                # self.wait_dlg.show()
                layers = proj.mapLayers().values()
                snapping_config = proj.snappingConfig()
                snapping_config.clearIndividualLayerSettings()
                snapping_config.setIntersectionSnapping(False)

                for fc in layers:
                    if fc.name() in POLYGON_LYR:

                        layer_settings = QgsSnappingConfig.IndividualLayerSettings(
                            True,
                            QgsSnappingConfig.VertexFlag,
                            20,
                            QgsTolerance.ProjectUnits,
                        )
                        snapping_config.setIndividualLayerSettings(fc, layer_settings)

                layer.commitChanges()
                # self.wait_dlg.hide()

            else:
                layer.commitChanges()

    def add_site(self):
        self.edit_win_dlg.edita()
