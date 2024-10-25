import os
import sqlite3
import webbrowser
from qgis.PyQt import uic
from qgis.core import QgsProject, QgsMessageLog, Qgis
from qgis.PyQt.QtWidgets import QDialog, QMessageBox
from qgis.PyQt.QtCore import QCoreApplication

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "tb_edit_metadata.ui"))


class EditMetadataDialog(QDialog, FORM_CLASS):
    def __init__(self, iface, parent=None):
        """Constructor."""
        self.iface = iface
        super().__init__(parent)
        self.setupUi(self)

        self.home_path = QgsProject.instance().homePath()
        self.db_path = QgsProject.instance().readPath("./") + "/db/indagini.sqlite"

        self.help_button.clicked.connect(
            lambda: webbrowser.open("https://mzs-tools.readthedocs.io/it/latest/plugin/nuovo_progetto.html")
        )

    def run_edit_metadata_dialog(self):
        """Run the metadata edit tool."""

        # detect MzSTools project
        if not QgsProject.instance().fileName() or not (
            os.path.exists(os.path.join(self.home_path, "progetto"))
            and os.path.exists(os.path.join(self.home_path, "progetto", "versione.txt"))
        ):
            QMessageBox.critical(
                self.iface.mainWindow(),
                self.tr("Error"),
                self.tr("This tool can only be used with MzSTools projects."),
            )
            return

        # get comune cod_istat
        layer_comune_progetto = QgsProject.instance().mapLayersByName("Comune del progetto")[0]
        features = layer_comune_progetto.getFeatures()
        for feat in features:
            attrs = feat.attributes()
            cod_istat = attrs[5]

        expected_id = f"{cod_istat}M1"
        QgsMessageLog.logMessage(f"expected_id: {expected_id}", "MzSTools", level=Qgis.Info)

        # check if "metadati" table contains a single record with expected id
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM metadati WHERE id_metadato = ?", (expected_id,))
        count = cursor.fetchone()[0]
        conn.close()

        if count == 0:
            QMessageBox.critical(self.iface.mainWindow(), self.tr("Error"), self.tr("Record not found."))
            # TODO: create a new record?
            return
        if count > 1:
            QMessageBox.critical(
                self.iface.mainWindow(),
                self.tr("Error"),
                self.tr("Multiple records found. Please edit the metadata table and remove all but one record."),
            )
            return

        self.load_data(expected_id)

        # self.button_box.setEnabled(False)

        self.show()
        self.adjustSize()
        result = self.exec_()

        if result:
            self.save_data()

    def load_data(self, record_id):
        """Load data from the SQLite table and populate the form fields."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM metadati WHERE id_metadato = ?", (record_id,))
        record = cursor.fetchone()
        conn.close()

        if record:
            self.id_metadato.setText(record[0])
            self.liv_gerarchico.setText(record[1])
            self.resp_metadato_nome.setText(record[2])
            self.resp_metadato_email.setText(record[3])
            self.resp_metadato_sito.setText(record[4])
            # self.data_metadato.setText(record[5])
            self.srs_dati.setText(record[6])
            self.proprieta_dato_nome.setText(record[7])
            self.proprieta_dato_email.setText(record[8])
            self.proprieta_dato_sito.setText(record[9])
            # self.data_dato.setText(record[10])
            self.ruolo.setText(record[11])
            self.desc_dato.setText(record[12])
            self.formato.setText(record[13])
            self.tipo_dato.setText(record[14])
            self.contatto_dato_nome.setText(record[15])
            self.contatto_dato_email.setText(record[16])
            self.contatto_dato_sito.setText(record[17])
            self.keywords.setText(record[18])
            self.keywords_inspire.setText(record[19])
            self.limitazione.setText(record[20])
            self.vincoli_accesso.setText(record[21])
            self.vincoli_fruibilita.setText(record[22])
            self.vincoli_sicurezza.setText(record[23])
            self.scala.setText(record[24])
            self.categoria_iso.setText(record[25])
            self.estensione_ovest.setText(record[26])
            self.estensione_est.setText(record[27])
            self.estensione_sud.setText(record[28])
            self.estensione_nord.setText(record[29])
            self.formato_dati.setText(record[30])
            self.distributore_dato_nome.setText(record[31])
            self.distributore_dato_telefono.setText(record[32])
            self.distributore_dato_email.setText(record[33])
            self.distributore_dato_sito.setText(record[34])
            self.url_accesso_dato.setText(record[35])
            self.funzione_accesso_dato.setText(record[36])
            self.precisione.setText(record[37])
            self.genealogia.setText(record[38])

    def save_data(self):
        """Save the edited data back to the SQLite table."""
        QgsMessageLog.logMessage("Saving data...", "MzSTools", level=Qgis.Info)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE metadati SET
                liv_gerarchico = ?, resp_metadato_nome = ?, resp_metadato_email = ?, resp_metadato_sito = ?, data_metadato = ?, 
                srs_dati = ?, proprieta_dato_nome = ?, proprieta_dato_email = ?, proprieta_dato_sito = ?, data_dato = ?, 
                ruolo = ?, desc_dato = ?, formato = ?, tipo_dato = ?, contatto_dato_nome = ?, contatto_dato_email = ?, 
                contatto_dato_sito = ?, keywords = ?, keywords_inspire = ?, limitazione = ?, vincoli_accesso = ?, 
                vincoli_fruibilita = ?, vincoli_sicurezza = ?, scala = ?, categoria_iso = ?, estensione_ovest = ?, 
                estensione_est = ?, estensione_sud = ?, estensione_nord = ?, formato_dati = ?, distributore_dato_nome = ?, 
                distributore_dato_telefono = ?, distributore_dato_email = ?, distributore_dato_sito = ?, url_accesso_dato = ?, 
                funzione_accesso_dato = ?, precisione = ?, genealogia = ?
            WHERE id_metadato = ?
        """,
            (
                self.liv_gerarchico.text(),
                self.resp_metadato_nome.text(),
                self.resp_metadato_email.text(),
                self.resp_metadato_sito.text(),
                self.data_metadato.text(),
                self.srs_dati.text(),
                self.proprieta_dato_nome.text(),
                self.proprieta_dato_email.text(),
                self.proprieta_dato_sito.text(),
                self.data_dato.text(),
                self.ruolo.text(),
                self.desc_dato.toPlainText(),
                self.formato.text(),
                self.tipo_dato.text(),
                self.contatto_dato_nome.text(),
                self.contatto_dato_email.text(),
                self.contatto_dato_sito.text(),
                self.keywords.text(),
                self.keywords_inspire.text(),
                self.limitazione.text(),
                self.vincoli_accesso.text(),
                self.vincoli_fruibilita.text(),
                self.vincoli_sicurezza.text(),
                self.scala.text(),
                self.categoria_iso.text(),
                self.estensione_ovest.text(),
                self.estensione_est.text(),
                self.estensione_sud.text(),
                self.estensione_nord.text(),
                self.formato_dati.text(),
                self.distributore_dato_nome.text(),
                self.distributore_dato_telefono.text(),
                self.distributore_dato_email.text(),
                self.distributore_dato_sito.text(),
                self.url_accesso_dato.text(),
                self.funzione_accesso_dato.text(),
                self.precisione.text(),
                self.genealogia.toPlainText(),
                self.id_metadato.text(),
            ),
        )
        conn.commit()
        conn.close()
        QMessageBox.information(self, "Success", "Record updated successfully.")
        # self.accept()

    def tr(self, message):
        return QCoreApplication.translate("EditMetadataDialog", message)
