import datetime
import os
import shutil
import traceback
import zipfile
from dataclasses import dataclass
from pathlib import Path
from sqlite3 import Connection
from typing import Optional

from qgis.core import QgsFeature, QgsField, QgsFields, QgsGeometry, QgsProject
from qgis.PyQt.QtCore import QCoreApplication, QVariant
from qgis.utils import iface, spatialite_connect

from mzs_tools.__about__ import DIR_PLUGIN_ROOT, __version__
from mzs_tools.plugin_utils.logging import MzSToolsLogger

from ..plugin_utils.misc import save_map_image


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
        self.current_project: QgsProject = None

        self.project_path = None
        self.project_version = None
        self.project_updateable = False
        self.db_path = None
        self.db_connection: Optional[Connection] = None

        self.comune_data: ComuneData = None
        self.project_metadata = None

        # TODO: build a simple map of table names and corresponding layer names
        # find the editable layers that are linked to tables in the db
        self.table_layer_map = {}

        self.project_issues = {}

        self.is_mzs_project: bool = False

    def init_manager(self):
        """Detect if the current project is a MzS Tools project and setup the manager."""
        self.current_project = QgsProject.instance()
        project_file_name = self.current_project.baseName()
        project_path = Path(self.current_project.absolutePath())
        db_path = project_path / "db" / "indagini.sqlite"
        version_file_path = project_path / "progetto" / "versione.txt"

        if project_file_name != "progetto_MS" or not db_path.exists() or not version_file_path.exists():
            self.log("No MzS Tools project detected", log_level=4)
            self.is_mzs_project = False
            return False

        self.project_path = project_path
        self.db_path = db_path

        # setup db connection and save it to the manager
        connected = self.setup_db_connection()
        if not connected:
            return False

        # cleanup db connection on project close
        self.current_project.cleared.connect(self.cleanup_db_connection)

        # check project version
        try:
            with version_file_path.open("r") as f:
                self.project_version = f.read().strip()
        except Exception as e:
            self.log(f"Error reading project version: {e}", log_level=2)
            self.project_issues["version"] = "Error reading project version"

        if self.project_version and self.project_version < __version__:
            self.log(
                f"MzS Project is version {self.project_version} and should be updated to version {__version__}",
                log_level=1,
            )
            self.project_updateable = True

        # get comune data from db
        self.comune_data = self.get_project_comune_data()
        if not self.comune_data:
            self.log("Error reading comune data from project db", log_level=2)
            self.project_issues["comune"] = "Error reading comune data from project db"

        # TODO: load metadata from db if exists
        # self.sm_project_metadata = self.get_sm_project_metadata()

        self.is_mzs_project = True
        self.log(f"MzS Tools project version {self.project_version} detected. Manager initialized.")

        return True

    def setup_db_connection(self):
        # setup db connection
        if not self.db_connection:
            self.log(f"Creating db connection to {self.db_path}...", log_level=4)
            # database cannot be an empty 0-byte file
            if self.db_path.stat().st_size == 0:
                err_msg = self.tr(f"The database file is empty! {self.db_path}")
                self.log(err_msg, log_level=2, push=True, duration=0)
                self.project_issues["db"] = "Empty database file"
                self.cleanup_db_connection()
                return False

            try:
                self.db_connection = spatialite_connect(str(self.db_path))
                # validate connection
                cursor = self.db_connection.cursor()
                # TODO: quick check for db version and integrity
                # cursor.execute("PRAGMA integrity_check")
                cursor.execute("PRAGMA quick_check")
                # cursor.execute("SELECT * FROM sito_puntuale LIMIT 1")
                cursor.close()
            except Exception as e:
                err_msg = self.tr(f"Error connecting to db! {self.db_path}")
                self.log(f"{err_msg}: {e}", log_level=2, push=True, duration=0)
                self.log(traceback.format_exc(), log_level=2)
                self.cleanup_db_connection()
                return False

        return True

    def cleanup_db_connection(self):
        if self.db_connection:
            self.log(f"Closing db connection to {self.db_path}...", log_level=4)
            self.db_connection.close()
            self.db_connection = None

    def get_project_comune_data(self) -> Optional[ComuneData]:
        data = None
        with self.db_connection as conn:
            cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM comune_progetto LIMIT 1")
            row = cursor.fetchone()
            if row:
                data = ComuneData(
                    cod_regio=row[1],
                    cod_prov=row[2],
                    cod_com=row[3],
                    comune=row[4],
                    provincia=row[7],
                    regione=row[8],
                    cod_istat=row[6],
                )
        finally:
            cursor.close()
        return data

    def get_comune_record(self, cod_istat):
        # extract comune feature from db
        record = None
        with self.db_connection as conn:
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
        # TODO: DeprecationWarning: QgsField constructor is deprecated
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

    def create_project_from_template(self, comune_name, cod_istat, study_author, author_email, dir_out):
        # extract project template in the output directory
        self.extract_project_template(dir_out)

        comune_name = self.sanitize_comune_name(comune_name)
        new_project_path = os.path.join(dir_out, f"{cod_istat}_{comune_name}")
        os.rename(os.path.join(dir_out, "progetto_MS"), new_project_path)

        self.current_project.read(os.path.join(new_project_path, "progetto_MS.qgs"))

        # init new project info
        self.current_project = QgsProject.instance()
        self.project_path = Path(self.current_project.absolutePath())
        self.db_path = self.project_path / "db" / "indagini.sqlite"

        self.setup_db_connection()

        self.customize_project_template(cod_istat)

        self.create_basic_project_metadata(cod_istat, study_author, author_email)

        # Refresh layouts
        self.refresh_project_layouts()

        # write the version file
        with open(os.path.join(self.project_path, "progetto", "versione.txt"), "w") as f:
            f.write(__version__)

        # Save the project
        self.current_project.write(os.path.join(new_project_path, "progetto_MS.qgs"))

        # completely reload the project
        iface.addProject(os.path.join(new_project_path, "progetto_MS.qgs"))

        return new_project_path

    def update_project_from_template(self):
        if not self.project_updateable:
            self.log("Requested project update for non-updateable project!", log_level=1)
            return

        # backup the current project
        self.backup_project()

        # extract project template in the current project directory (will be in "progetto_MS" subdir)
        self.extract_project_template(self.project_path)

        # remove old project files (maschere, script, loghi, progetto_MS.qgs)
        shutil.rmtree(os.path.join(self.project_path, "progetto", "maschere"))
        shutil.copytree(
            os.path.join(self.project_path, "progetto_MS", "progetto", "maschere"),
            os.path.join(self.project_path, "progetto", "maschere"),
        )

        shutil.rmtree(os.path.join(self.project_path, "progetto", "script"))
        shutil.copytree(
            os.path.join(self.project_path, "progetto_MS", "progetto", "script"),
            os.path.join(self.project_path, "progetto", "script"),
        )

        shutil.rmtree(os.path.join(self.project_path, "progetto", "loghi"))
        shutil.copytree(
            os.path.join(self.project_path, "progetto_MS", "progetto", "loghi"),
            os.path.join(self.project_path, "progetto", "loghi"),
        )

        # write the new version to the version file
        with open(os.path.join(self.project_path, "progetto", "versione.txt"), "w") as f:
            f.write(__version__)

        os.remove(os.path.join(self.project_path, "progetto_MS.qgs"))
        shutil.copyfile(
            os.path.join(self.project_path, "progetto_MS", "progetto_MS.qgs"),
            os.path.join(self.project_path, "progetto_MS.qgs"),
        )

        # read the new project file inside the loaded (old) project
        self.current_project.read(os.path.join(self.project_path, "progetto_MS.qgs"))

        self.setup_db_connection()

        # apply project customizations without creating comune feature
        self.customize_project_template(self.comune_data.cod_istat, insert_comune_progetto=False)

        # cleanup the extracted project template
        shutil.rmtree(os.path.join(self.project_path, "progetto_MS"))

        # Refresh layouts
        self.refresh_project_layouts()

        # Save the project
        self.current_project.write(os.path.join(self.project_path, "progetto_MS.qgs"))

        # completely reload the project
        iface.addProject(os.path.join(self.project_path, "progetto_MS.qgs"))

        return self.project_path

    def customize_project_template(self, cod_istat, insert_comune_progetto=True):
        """Customize the project with the selected comune data."""

        comune_record = self.get_comune_record(cod_istat)
        feature = self.create_comune_feature(comune_record)
        # TODO: get layer from self.table_layer_map
        layer_comune_progetto = self.current_project.mapLayersByName("Comune del progetto")[0]
        if insert_comune_progetto:
            # TODO: save comune progetto data to db directly?
            layer_comune_progetto.startEditing()
            data_provider = layer_comune_progetto.dataProvider()
            data_provider.addFeatures([feature])
            layer_comune_progetto.commitChanges()
            layer_comune_progetto.updateExtents()

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

    def refresh_project_layouts(self):
        layout_manager = self.current_project.layoutManager()
        layouts = layout_manager.printLayouts()
        for layout in layouts:
            layout.refresh()

    def update_db(self):
        sql_scripts = []
        if self.project_version < "0.8":
            sql_scripts.append("query_v08.sql")
        if self.project_version < "0.9":
            sql_scripts.append("query_v09.sql")
        if self.project_version < "1.2":
            sql_scripts.append("query_v10_12.sql")
        if self.project_version < "1.9":
            sql_scripts.append("query_v19.sql")
        if self.project_version < "1.9.2":
            sql_scripts.append("query_v192.sql")
        if self.project_version < "1.9.3":
            sql_scripts.append("query_v193.sql")
        if self.project_version < "1.9.5":
            sql_scripts.append("query_v195.sql")

        for upgrade_script in sql_scripts:
            self.log(f"Executing: {upgrade_script}", log_level=1)
            self.exec_db_upgrade_sql(upgrade_script)

        self.log("Sql upgrades ok")

    def exec_db_upgrade_sql(self, script_name):
        with self.db_connection as conn:
            cursor = conn.cursor()
            script_path = DIR_PLUGIN_ROOT / "data" / "sql_scripts" / script_name
            with script_path.open("r") as f:
                cursor.executescript(f.read())
            cursor.close()

    def create_basic_project_metadata(self, cod_istat, study_author=None, author_email=None):
        """Create a basic metadata record for an MzS Tools project."""
        # orig_gdb = self.current_project.readPath(os.path.join("db", "indagini.sqlite"))
        date_now = datetime.datetime.now().strftime(r"%d/%m/%Y")
        # TODO: get layer from self.table_layer_map
        extent = self.current_project.mapLayersByName("Comune del progetto")[0].dataProvider().extent()
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

        with self.db_connection as conn:
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

    def backup_project(self, out_dir=None):
        if not out_dir:
            out_dir = self.project_path.parent

        project_folder_name = Path(self.project_path).name
        backup_dir_name = f"{project_folder_name}_backup_v{self.project_version}_{datetime.datetime.now().strftime('%Y_%m_%d_%H_%M')}"
        backup_path = out_dir / backup_dir_name

        self.log(f"Backing up project in {backup_path}...")
        shutil.copytree(self.project_path, backup_path)

        return backup_path

    @staticmethod
    def extract_project_template(dir_out):
        project_template_path = DIR_PLUGIN_ROOT / "data" / "progetto_MS.zip"
        with zipfile.ZipFile(str(project_template_path), "r") as zip_ref:
            zip_ref.extractall(dir_out)

    @staticmethod
    def sanitize_comune_name(comune_name):
        return comune_name.split(" (")[0].replace(" ", "_").replace("'", "_")

    def tr(self, message: str) -> str:
        return QCoreApplication.translate(self.__class__.__name__, message)
