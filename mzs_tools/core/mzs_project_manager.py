import os
import shutil
import sqlite3
import zipfile
from pathlib import Path

from qgis.core import QgsFeature, QgsFeatureRequest, QgsField, QgsFields, QgsGeometry, QgsPointXY, QgsProject
from qgis.PyQt.QtCore import QCoreApplication, QVariant
from qgis.utils import iface

from mzs_tools.__about__ import DIR_PLUGIN_ROOT

from ..utils import create_basic_sm_metadata, save_map_image


class MzSProjectManager:
    def __init__(self):
        self.current_project = QgsProject.instance()

        self.is_mzs_project = self.detect_mzs_project()

        self.project_path = None
        self.db_path = None
        self.mzs_project_version = None

        self.cod_regio = None
        self.cod_prov = None
        self.cod_com = None
        self.comune = None
        self.provincia = None
        self.regione = None
        self.cod_istat = None

        self.sm_project_metadata = None

        # TODO: build a simple map of table names and corresponding layer names
        # find the editable layers that are linked to tables in the db
        self.table_layer_map = {}

    def detect_mzs_project(self):
        """Detect if the current project is a MzSTools project."""

        project_file_name = self.current_project.baseName()
        project_path = Path(self.current_project.absolutePath())
        db_path = project_path / "db" / "indagini.sqlite"
        version_file_path = project_path / "progetto" / "versione.txt"

        if project_file_name != "progetto_MS" or not db_path.exists() or not version_file_path.exists():
            return False

        self.project_path = project_path
        self.db_path = db_path
        with version_file_path.open("r") as f:
            self.mzs_project_version = f.read().strip()

        # TODO: quick check for db integrity and get version

        # get comune data from db
        comune_record = self.get_project_comune_record()
        if comune_record:
            self.cod_regio = comune_record[1]
            self.cod_prov = comune_record[2]
            self.cod_com = comune_record[3]
            self.comune = comune_record[4]
            self.provincia = comune_record[7]
            self.regione = comune_record[8]
            self.cod_istat = comune_record[6]

        # TODO: load metadata from db if exists
        # self.sm_project_metadata = self.get_sm_project_metadata()

        return True

    def get_project_comune_record(self):
        record = None
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM comune_progetto LIMIT 1")
            record = cursor.fetchone()
            cursor.close()
        return record

    def get_comune_record(self, cod_istat):
        # extract comune feature from db
        record = None
        with sqlite3.connect(self.db_path) as conn:
            conn.enable_load_extension(True)
            conn.execute('SELECT load_extension("mod_spatialite")')
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT ogc_fid, cod_regio, cod_prov, cod_com, comune, cod_istat, provincia, regione, st_astext(GEOMETRY) FROM comuni WHERE cod_istat = '{cod_istat}'"
            )
            record = cursor.fetchone()
            cursor.close()

        return record

    def create_comune_feature(self, comune_record):
        # create comune feature
        fields = QgsFields()
        fields.append(QgsField("pkuid", QVariant.Int))
        fields.append(QgsField("cod_regio", QVariant.String))
        fields.append(QgsField("cod_prov", QVariant.String))
        fields.append(QgsField("cod_com", QVariant.String))
        fields.append(QgsField("comune", QVariant.String))
        fields.append(QgsField("cod_istat", QVariant.String))
        fields.append(QgsField("provincia", QVariant.String))
        fields.append(QgsField("regione", QVariant.String))

        feature = QgsFeature(fields)
        feature.setAttributes(list(comune_record[:8]))
        feature.setGeometry(QgsGeometry.fromWkt(comune_record[8]))

        return feature

    def create_project(self, comune_name, cod_istat, dir_out):
        # comune_name = self.comuneField.text()
        # cod_istat = self.cod_istat.text()
        # professionista = self.professionista.text()
        # email_prof = self.email_prof.text()

        self.extract_project_template(dir_out)

        comune_name = self.sanitize_comune_name(comune_name)
        new_project_path = os.path.join(dir_out, f"{cod_istat}_{comune_name}")
        os.rename(os.path.join(dir_out, "progetto_MS"), new_project_path)

        # project = QgsProject.instance()
        self.current_project.read(os.path.join(new_project_path, "progetto_MS.qgs"))

        self.customize_project(self.current_project, cod_istat, new_project_path)
        # create_basic_sm_metadata(cod_istat, professionista, email_prof)

        # Refresh layouts
        layout_manager = self.current_project.layoutManager()
        layouts = layout_manager.printLayouts()
        for layout in layouts:
            layout.refresh()

        # Save the project
        self.current_project.write(os.path.join(new_project_path, "progetto_MS.qgs"))

        # QMessageBox.information(None, self.tr("Notice"), self.tr("The project has been created successfully."))

        # return os.path.join(new_project_path, "progetto_MS.qgs")

        # completely reload the project
        iface.addProject(os.path.join(new_project_path, "progetto_MS.qgs"))

    def customize_project(self, cod_istat):
        """Customize the project with the selected comune data."""

        # TODO: get comune data from db directly
        # layer_limiti_comunali = self.current_project.mapLayersByName("Limiti comunali")[0]
        # req = QgsFeatureRequest()
        # req.setFilterExpression(f"\"cod_istat\" = '{cod_istat}'")
        # selection = layer_limiti_comunali.getFeatures(req)
        # layer_limiti_comunali.selectByIds([k.id() for k in selection])

        # layer_comune_progetto = self.current_project.mapLayersByName("Comune del progetto")[0]
        # selected_features = layer_limiti_comunali.selectedFeatures()

        # features = [i for i in selected_features]

        comune_record = self.get_comune_record(cod_istat)
        feature = self.create_comune_feature(comune_record)

        # TODO: save comune progetto data to db directly?
        layer_comune_progetto = self.current_project.mapLayersByName("Comune del progetto")[0]
        layer_comune_progetto.startEditing()
        data_provider = layer_comune_progetto.dataProvider()
        data_provider.addFeatures([feature])
        layer_comune_progetto.commitChanges()
        layer_comune_progetto.updateExtents()

        # features = layer_comune_progetto.getFeatures()
        # for feat in features:
        #     attrs = feat.attributes()
        #     codice_regio = attrs[1]
        #     nome = attrs[4]
        #     provincia = attrs[6]
        #     regione = attrs[7]

        attribute_map = feature.attributeMap()
        codice_regio = attribute_map["cod_regio"]
        comune = attribute_map["comune"]
        provincia = attribute_map["provincia"]
        regione = attribute_map["regione"]

        layer_limiti_comunali = self.current_project.mapLayersByName("Limiti comunali")[0]
        layer_limiti_comunali.removeSelection()
        layer_limiti_comunali.setSubsetString(f"cod_regio='{codice_regio}'")

        logo_regio_in = os.path.join(DIR_PLUGIN_ROOT, "img", "logo_regio", codice_regio + ".png")
        logo_regio_out = os.path.join(self.project_path, "progetto", "loghi", "logo_regio.png")
        shutil.copyfile(logo_regio_in, logo_regio_out)

        mainPath = QgsProject.instance().homePath()
        canvas = iface.mapCanvas()

        imageFilename = os.path.join(mainPath, "progetto", "loghi", "mappa_reg.png")
        # TODO: this assumes comune_progetto and comuni layers are the only layers currently active
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
            map_item_3.setText("Comune di " + comune)
            map_item_4 = layout.itemById("logo")
            map_item_4.refreshPicture()
            map_item_5 = layout.itemById("mappa_1")
            map_item_5.refreshPicture()

        # set project title
        project_title = f"MzS Tools - Comune di {comune} ({provincia}, {regione}) - Studio di Microzonazione Sismica"
        self.current_project.setTitle(project_title)

    def update_project(self):
        pass

    @staticmethod
    def extract_project_template(dir_out):
        project_template_path = DIR_PLUGIN_ROOT / "data" / "progetto_MS.zip"
        with zipfile.ZipFile(str(project_template_path), "r") as zip_ref:
            zip_ref.extractall(dir_out)

    @staticmethod
    def sanitize_comune_name(comune_name):
        return comune_name.split(" (")[0].replace(" ", "_").replace("'", "_")
