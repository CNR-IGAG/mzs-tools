import datetime
import os
import shutil
import sqlite3
import zipfile
from pathlib import Path

from qgis.core import Qgis, QgsMessageLog, QgsProject
from qgis.PyQt import uic
from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtWidgets import QDialog, QMessageBox
from qgis.utils import iface

from .utils import save_map_image

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "tb_aggiorna_progetto.ui"))


class aggiorna_progetto(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super().__init__(parent)
        self.setupUi(self)
        self.plugin_dir = os.path.dirname(__file__)
        self.sql_scripts_dir = os.path.join(self.plugin_dir, "data", "sql_scripts")

    def aggiorna(self, proj_path, proj_vers):
        self.show()
        self.adjustSize()
        result = self.exec_()
        if result == QDialog.Accepted:
            pacchetto = os.path.join(self.plugin_dir, "data", "progetto_MS.zip")

            output_path = Path(proj_path).parent
            project_folder_name = Path(proj_path).name

            name_output = (
                f"{project_folder_name}_backup_v{proj_vers}_{datetime.datetime.now().strftime('%Y_%m_%d_%H_%M')}"
            )

            sql_scripts = []
            if proj_vers < "0.8":
                sql_scripts.append("query_v08.sql")
            if proj_vers < "0.9":
                sql_scripts.append("query_v09.sql")
            if proj_vers < "1.2":
                sql_scripts.append("query_v10_12.sql")
            if proj_vers < "1.9":
                sql_scripts.append("query_v19.sql")
            if proj_vers < "1.9.2":
                sql_scripts.append("query_v192.sql")
            if proj_vers < "1.9.3":
                sql_scripts.append("query_v193.sql")

            try:
                shutil.copytree(proj_path, os.path.join(str(output_path), name_output))

                path_db = os.path.join(proj_path, "db", "indagini.sqlite")

                for upgrade_script in sql_scripts:
                    QgsMessageLog.logMessage(f"Executing: {upgrade_script}", "MzSTools", level=Qgis.Info)
                    self.exec_db_upgrade_sql(path_db, upgrade_script)

                QgsMessageLog.logMessage("Sql upgrades ok", "MzSTools", level=Qgis.Info)
                zip_ref = zipfile.ZipFile(pacchetto, "r")
                zip_ref.extractall(proj_path)
                zip_ref.close()

                shutil.rmtree(os.path.join(proj_path, "progetto", "maschere"))
                shutil.copytree(
                    os.path.join(proj_path, "progetto_MS", "progetto", "maschere"),
                    os.path.join(proj_path, "progetto", "maschere"),
                )
                shutil.rmtree(os.path.join(proj_path, "progetto", "script"))
                shutil.copytree(
                    os.path.join(proj_path, "progetto_MS", "progetto", "script"),
                    os.path.join(proj_path, "progetto", "script"),
                )
                shutil.copyfile(
                    os.path.join(os.path.dirname(__file__), "versione.txt"),
                    os.path.join(proj_path, "progetto", "versione.txt"),
                )
                shutil.rmtree(os.path.join(proj_path, "progetto", "loghi"))
                shutil.copytree(
                    os.path.join(proj_path, "progetto_MS", "progetto", "loghi"),
                    os.path.join(proj_path, "progetto", "loghi"),
                )

                # remove the old project file and copy the new one
                os.remove(os.path.join(proj_path, "progetto_MS.qgs"))
                shutil.copyfile(
                    os.path.join(proj_path, "progetto_MS", "progetto_MS.qgs"),
                    os.path.join(proj_path, "progetto_MS.qgs"),
                )

                self.load_new_qgs_file(proj_path)

                shutil.rmtree(os.path.join(proj_path, "progetto_MS"))

                QMessageBox.information(
                    None,
                    self.tr("INFORMATION!"),
                    self.tr(
                        "The project structure has been updated!\nThe backup copy has been saved in the following directory: "
                    )
                    + name_output,
                )

                # reload the project
                iface.addProject(os.path.join(proj_path, "progetto_MS.qgs"))

            except Exception as z:
                QMessageBox.critical(None, "ERROR!", 'Error:\n"' + str(z) + '"')

    def exec_db_upgrade_sql(self, path_db, upgrade_script):
        conn = sqlite3.connect(path_db)
        cursor = conn.cursor()
        conn.text_factory = lambda x: str(x, "utf-8", "ignore")
        conn.enable_load_extension(True)

        with open(os.path.join(self.sql_scripts_dir, upgrade_script), "r") as f:
            full_sql = f.read()
            sql_commands = full_sql.split(";;")
            try:
                conn.execute('SELECT load_extension("mod_spatialite")')
                for sql_command in sql_commands:
                    sql_command = sql_command.strip()
                    if sql_command:
                        cursor.execute(sql_command)
                cursor.close()
                conn.commit()
            finally:
                conn.close()

    def load_new_qgs_file(self, proj_path):
        QgsMessageLog.logMessage("Loading new project", "MzSTools", level=Qgis.Info)

        project = QgsProject.instance()

        # read the new project file inside the loaded (old) project
        project.read(os.path.join(proj_path, "progetto_MS.qgs"))

        layer_limiti_comunali = project.mapLayersByName("Limiti comunali")[0]

        layer_comune_progetto = project.mapLayersByName("Comune del progetto")[0]

        features = layer_comune_progetto.getFeatures()
        for feat in features:
            attrs = feat.attributes()
            codice_regio = attrs[1]
            nome = attrs[4]
            provincia = attrs[6]
            regione = attrs[7]

        layer_limiti_comunali.removeSelection()
        layer_limiti_comunali.setSubsetString(f"cod_regio='{codice_regio}'")

        logo_regio_in = os.path.join(self.plugin_dir, "img", "logo_regio", codice_regio + ".png").replace("\\", "/")
        logo_regio_out = os.path.join(proj_path, "progetto", "loghi", "logo_regio.png").replace("\\", "/")
        shutil.copyfile(logo_regio_in, logo_regio_out)

        mainPath = QgsProject.instance().homePath()
        canvas = iface.mapCanvas()

        imageFilename = os.path.join(mainPath, "progetto", "loghi", "mappa_reg.png")
        save_map_image(imageFilename, layer_limiti_comunali, canvas)

        extent = layer_comune_progetto.dataProvider().extent()
        canvas.setExtent(extent)

        layout_manager = QgsProject.instance().layoutManager()
        layouts = layout_manager.printLayouts()

        for layout in layouts:
            map_item = layout.itemById("mappa_0")
            map_item.zoomToExtent(canvas.extent())
            map_item_2 = layout.itemById("regio_title")
            map_item_2.setText("Regione " + regione)
            map_item_3 = layout.itemById("com_title")
            map_item_3.setText("Comune di " + nome)
            map_item_4 = layout.itemById("logo")
            map_item_4.refreshPicture()
            map_item_5 = layout.itemById("mappa_1")
            map_item_5.refreshPicture()

        # set project title
        project_title = f"MzS Tools - Comune di {nome} ({provincia}, {regione}) - Studio di Microzonazione Sismica"
        project.setTitle(project_title)

        # # Save the project
        project.write(os.path.join(QgsProject.instance().absolutePath(), "progetto_MS.qgs"))

        # Refresh layouts
        layout_manager = QgsProject.instance().layoutManager()
        layouts = layout_manager.printLayouts()
        for layout in layouts:
            layout.refresh()

    def tr(self, message):
        return QCoreApplication.translate("aggiorna_progetto", message)
