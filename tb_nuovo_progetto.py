import datetime
import os
import tempfile
import shutil
import sqlite3
import webbrowser
import zipfile

from qgis.PyQt import uic
from qgis.core import QgsProject, QgsFeatureRequest
from qgis.PyQt.QtWidgets import QDialog, QMessageBox, QCompleter
from qgis.PyQt.QtCore import QCoreApplication
from .utils import save_map_image

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "tb_nuovo_progetto.ui"))


class NewProject(QDialog, FORM_CLASS):
    def __init__(self, iface, parent=None):
        """Constructor."""
        self.iface = iface
        super().__init__(parent)
        self.setupUi(self)

        self.plugin_dir = os.path.dirname(__file__)
        self.project_template_path = os.path.join(self.plugin_dir, "data", "progetto_MS.zip")
        self.connect_signals()

    def run_new_project_tool(self):
        # check if there is a project already open
        if QgsProject.instance().fileName():
            QMessageBox.warning(
                self.iface.mainWindow(),
                self.tr("WARNING!"),
                self.tr("Close the current project before creating a new one."),
            )
            return

        # Load comuni data for autocomplete
        self.load_comuni_data()

        # check and update QGIS svg symbols cache
        self.check_svg_cache()

        self.clear_fields()
        self.button_box.setEnabled(False)

        self.show()
        self.adjustSize()
        result = self.exec_()

        if result:
            dir_out = self.dir_output.text()
            if os.path.isdir(dir_out):
                try:
                    self.create_project(dir_out)
                except Exception as z:
                    QMessageBox.critical(None, "ERROR!", f'Error:\n"{str(z)}"')
                    if os.path.exists(os.path.join(dir_out, "progetto_MS")):
                        shutil.rmtree(os.path.join(dir_out, "progetto_MS"))
            else:
                QMessageBox.warning(
                    self.iface.mainWindow(), self.tr("WARNING!"), self.tr("The selected directory does not exist!")
                )

    def connect_signals(self):
        self.help_button.clicked.connect(
            lambda: webbrowser.open("https://mzs-tools.readthedocs.io/it/latest/plugin/nuovo_progetto.html")
        )
        self.comuneField.textChanged.connect(self.update_cod_istat)
        self.professionista.textChanged.connect(self.validate_input)
        self.email_prof.textChanged.connect(self.validate_input)
        self.dir_output.textChanged.connect(self.validate_input)

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

    def check_svg_cache(self):
        dir_svg_input = os.path.join(self.plugin_dir, "img", "svg")
        dir_svg_output = self.plugin_dir.split("python")[0] + "svg"

        if not os.path.exists(dir_svg_output):
            shutil.copytree(dir_svg_input, dir_svg_output)
        else:
            src_files = os.listdir(dir_svg_input)
            for file_name in src_files:
                full_file_name = os.path.join(dir_svg_input, file_name)
                if os.path.isfile(full_file_name):
                    shutil.copy(full_file_name, dir_svg_output)

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
        self.save_basic_metadata(cod_istat, professionista, email_prof)

        # Save the project
        project.write(os.path.join(new_project_path, "progetto_MS.qgs"))

        QMessageBox.information(None, self.tr("Notice"), self.tr("The project has been created successfully."))

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

        features = layer_comune_progetto.getFeatures()
        for feat in features:
            attrs = feat.attributes()
            codice_regio = attrs[1]
            nome = attrs[4]
            regione = attrs[7]

        layer_limiti_comunali.removeSelection()
        layer_limiti_comunali.setSubsetString(f"cod_regio='{codice_regio}'")

        logo_regio_in = os.path.join(self.plugin_dir, "img", "logo_regio", codice_regio + ".png").replace("\\", "/")
        logo_regio_out = os.path.join(new_project_path, "progetto", "loghi", "logo_regio.png").replace("\\", "/")
        shutil.copyfile(logo_regio_in, logo_regio_out)

        mainPath = QgsProject.instance().homePath()
        canvas = self.iface.mapCanvas()

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

    def save_basic_metadata(self, cod_istat, professionista, email_prof):
        """Save the basic metadata of the project."""
        orig_gdb = QgsProject.instance().readPath(os.path.join("db", "indagini.sqlite"))
        conn = sqlite3.connect(orig_gdb)

        date_now = datetime.datetime.now().strftime(r"%d/%m/%Y")

        extent = QgsProject.instance().mapLayersByName("Comune del progetto")[0].dataProvider().extent()

        values = {
            "id_metadato": f"{cod_istat}M1",
            "liv_gerarchico": "series",
            "resp_metadato_nome": professionista,
            "resp_metadato_email": email_prof,
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
