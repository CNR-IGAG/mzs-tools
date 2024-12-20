import os
import shutil
import sqlite3
import tempfile
import webbrowser
import zipfile

from qgis.core import QgsFeatureRequest, QgsProject
from qgis.PyQt import uic
from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtWidgets import QCompleter, QDialog, QFileDialog, QMessageBox
from qgis.utils import iface

from .utils import create_basic_sm_metadata, save_map_image

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "tb_nuovo_progetto.ui"))


class NewProject(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super().__init__(parent)
        self.setupUi(self)

        self.plugin_dir = os.path.dirname(__file__)
        self.project_template_path = os.path.join(self.plugin_dir, "data", "progetto_MS.zip")

        # Load comuni data for autocomplete
        self.load_comuni_data()

        self.connect_signals()

    def connect_signals(self):
        self.help_button.clicked.connect(
            lambda: webbrowser.open("https://mzs-tools.readthedocs.io/it/latest/plugin/nuovo_progetto.html")
        )
        self.comuneField.textChanged.connect(self.update_cod_istat)
        self.professionista.textChanged.connect(self.validate_input)
        self.email_prof.textChanged.connect(self.validate_input)
        self.dir_output.textChanged.connect(self.validate_input)
        self.pushButton_out.clicked.connect(self.update_output_field)

    def showEvent(self, e):
        self.clear_fields()
        self.button_box.setEnabled(False)

    def update_output_field(self):
        out_dir = QFileDialog.getExistingDirectory(self, "", "", QFileDialog.ShowDirsOnly)
        self.dir_output.setText(out_dir)

    def load_comuni_data(self):
        # Load comuni data from the project template
        with tempfile.TemporaryDirectory() as temp_dir:
            with zipfile.ZipFile(self.project_template_path, "r") as zip_ref:
                temp_db_path = zip_ref.extract("progetto_MS/db/indagini.sqlite", temp_dir)

            # Load comuni data from temp db
            conn = sqlite3.connect(temp_db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT comune, cod_istat, provincia, regione FROM comuni")
            self.comuni = cursor.fetchall()
            conn.close()

        # Create a list of comuni names for the completer
        self.comuni_names = [f"{comune[0]} ({comune[2]} - {comune[3]})" for comune in self.comuni]

        # Set up the completer
        completer = QCompleter(self.comuni_names, self)
        completer.setCaseSensitivity(False)
        self.comuneField.setCompleter(completer)

    def run_new_project_tool(self):
        # check if there is a project already open
        if QgsProject.instance().fileName():
            QMessageBox.warning(
                iface.mainWindow(),
                self.tr("WARNING!"),
                self.tr("Close the current project before creating a new one."),
            )
            return

        # self.show()
        # self.adjustSize()
        result = self.exec_()

        if result:
            dir_out = self.dir_output.text()
            if os.path.isdir(dir_out):
                try:
                    new_project = self.create_project(dir_out)
                    # reload the project
                    iface.addProject(new_project)
                except Exception as z:
                    QMessageBox.critical(None, "ERROR!", f'Error:\n"{str(z)}"')
                    if os.path.exists(os.path.join(dir_out, "progetto_MS")):
                        shutil.rmtree(os.path.join(dir_out, "progetto_MS"))
            else:
                QMessageBox.warning(
                    iface.mainWindow(), self.tr("WARNING!"), self.tr("The selected directory does not exist!")
                )

    def create_project(self, dir_out):
        comune_name = self.comuneField.text()
        cod_istat = self.cod_istat.text()
        professionista = self.professionista.text()
        email_prof = self.email_prof.text()

        self.extract_project_template(dir_out)

        comune_name = self.sanitize_comune_name(comune_name)
        new_project_path = os.path.join(dir_out, f"{cod_istat}_{comune_name}")
        os.rename(os.path.join(dir_out, "progetto_MS"), new_project_path)

        project = QgsProject.instance()
        project.read(os.path.join(new_project_path, "progetto_MS.qgs"))

        self.customize_project(project, cod_istat, new_project_path)
        create_basic_sm_metadata(cod_istat, professionista, email_prof)

        # Refresh layouts
        layout_manager = QgsProject.instance().layoutManager()
        layouts = layout_manager.printLayouts()
        for layout in layouts:
            layout.refresh()

        # Save the project
        project.write(os.path.join(new_project_path, "progetto_MS.qgs"))

        QMessageBox.information(None, self.tr("Notice"), self.tr("The project has been created successfully."))

        return os.path.join(new_project_path, "progetto_MS.qgs")

    def extract_project_template(self, dir_out):
        with zipfile.ZipFile(self.project_template_path, "r") as zip_ref:
            zip_ref.extractall(dir_out)

    def sanitize_comune_name(self, comune_name):
        return comune_name.split(" (")[0].replace(" ", "_").replace("'", "_")

    def customize_project(self, project, cod_istat, new_project_path):
        """Customize the project with the selected comune data."""
        layer_limiti_comunali = project.mapLayersByName("Limiti comunali")[0]
        req = QgsFeatureRequest()
        req.setFilterExpression(f"\"cod_istat\" = '{cod_istat}'")
        selection = layer_limiti_comunali.getFeatures(req)
        layer_limiti_comunali.selectByIds([k.id() for k in selection])

        layer_comune_progetto = project.mapLayersByName("Comune del progetto")[0]
        selected_features = layer_limiti_comunali.selectedFeatures()

        features = [i for i in selected_features]

        layer_comune_progetto.startEditing()
        data_provider = layer_comune_progetto.dataProvider()
        data_provider.addFeatures(features)
        layer_comune_progetto.commitChanges()
        layer_comune_progetto.updateExtents()

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
        logo_regio_out = os.path.join(new_project_path, "progetto", "loghi", "logo_regio.png").replace("\\", "/")
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

    def clear_fields(self):
        self.comuneField.clear()
        self.dir_output.clear()
        self.cod_istat.clear()
        self.professionista.clear()
        self.email_prof.clear()

    def validate_input(self):
        if (
            self.cod_istat
            and self.professionista.text()
            and self.email_prof.text()
            and self.dir_output.text()
            and os.path.isdir(self.dir_output.text())
        ):
            self.button_box.setEnabled(True)
        else:
            self.button_box.setEnabled(False)

    def update_cod_istat(self):
        comune_name = self.comuneField.text()

        if comune_name not in self.comuni_names:
            self.cod_istat.clear()
            self.button_box.setEnabled(False)
        else:
            comune_record = next((comune for comune in self.comuni if comune[0] == comune_name.split(" (")[0]), None)
            if comune_record:
                self.cod_istat.setText(comune_record[1])
                self.validate_input()

    def tr(self, message):
        return QCoreApplication.translate("NewProject", message)
