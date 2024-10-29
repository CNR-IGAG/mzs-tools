import os
import sqlite3
import webbrowser
from datetime import datetime

from qgis.core import QgsProject
from qgis.gui import QgsDateTimeEdit
from qgis.PyQt import uic
from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtWidgets import QDialog, QLineEdit, QMessageBox, QTextEdit

from .utils import create_basic_sm_metadata, qgs_log

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "tb_edit_metadata.ui"))


class EditMetadataDialog(QDialog, FORM_CLASS):
    def __init__(self, iface, parent=None):
        """Constructor."""
        self.iface = iface
        super().__init__(parent)
        self.setupUi(self)

        self.help_button.clicked.connect(
            lambda: webbrowser.open(
                "https://mzs-tools.readthedocs.io/it/latest/plugin/altri_strumenti.html#inserimento-e-modifica-dei-metadati"
            )
        )

        self.required_fields = (
            self.id_metadato,
            self.liv_gerarchico,
            self.resp_metadato_nome,
            self.resp_metadato_email,
            self.data_metadato,
            self.srs_dati,
            self.proprieta_dato_nome,
            self.proprieta_dato_email,
            self.proprieta_dato_sito,
            self.data_dato,
            self.ruolo,
            self.desc_dato,
            self.precisione,
            self.genealogia,
            self.formato,
            self.tipo_dato,
            self.contatto_dato_nome,
            self.contatto_dato_email,
            self.contatto_dato_sito,
            self.keywords,
            self.keywords_inspire,
            self.limitazione,
            self.vincoli_accesso,
            self.vincoli_fruibilita,
            self.vincoli_sicurezza,
            self.scala,
            self.categoria_iso,
            self.estensione_ovest,
            self.estensione_est,
            self.estensione_sud,
            self.estensione_nord,
        )

        # connect all required fields to the validate_input method
        for field in self.required_fields:
            if isinstance(field, QLineEdit) and field.isEnabled():
                field.textChanged.connect(self.validate_input)
            if isinstance(field, QTextEdit):
                field.textChanged.connect(self.validate_input)
            if isinstance(field, QgsDateTimeEdit):
                field.valueChanged.connect(self.validate_input)

    def run_edit_metadata_dialog(self):
        """Run the metadata edit tool."""

        self.home_path = QgsProject.instance().homePath()
        self.db_path = os.path.join(self.home_path, "db", "indagini.sqlite")

        if not (os.path.exists(self.home_path) and os.path.exists(self.db_path)):
            self.show_error("This tool can only be used with MzSTools projects.")
            return

        # get comune_progetto data
        comune_record = self.get_comune_progetto()
        if not comune_record:
            self.show_error("There was a problem reading comune_progetto from database!")
            return
        comune = comune_record[4]
        cod_istat = comune_record[6]
        provincia = comune_record[7]
        regione = comune_record[8]

        expected_id = f"{cod_istat}M1"
        comune_info = f"{comune} ({provincia}, {regione})"

        # check if "metadati" table contains a single record with expected id
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM metadati WHERE id_metadato = ?", (expected_id,))
            count = cursor.fetchone()[0]

        if count == 0:
            qgs_log("Metadata record not found. Creating a new record...", level="warning")
            create_basic_sm_metadata(cod_istat)
        if count > 1:
            qgs_log("Multiple metadata records found.", level="error")
            self.show_error(
                "Multiple metadata records found. Please edit the 'metadati' table and remove all but one record."
            )
            return

        self.load_data(expected_id, comune_info)
        self.validate_input()

        self.show()
        self.adjustSize()

        result = self.exec_()

        if result:
            self.save_data()

    def parse_date(self, date_str):
        if date_str and date_str != "NULL":
            try:
                return datetime.strptime(date_str, "%d/%m/%Y")
            except ValueError:
                pass
        return None

    def load_data(self, record_id, comune_info):
        """Load data from the SQLite table and populate the form fields."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM metadati WHERE id_metadato = ?", (record_id,))
            record = cursor.fetchone()

        if record:
            data_metadato = self.parse_date(record[5])
            data_dato = self.parse_date(record[10])

            self.comune_info.setText(comune_info)
            self.id_metadato.setText(record[0])
            self.liv_gerarchico.setText(record[1] or "series")
            self.resp_metadato_nome.setText(record[2])
            self.resp_metadato_email.setText(record[3])
            self.resp_metadato_sito.setText(record[4])
            if data_metadato:
                self.data_metadato.setDateTime(data_metadato)
            else:
                self.data_metadato.setEmpty()
            self.srs_dati.setText(record[6] or "32633")
            self.proprieta_dato_nome.setText(record[7])
            self.proprieta_dato_email.setText(record[8])
            self.proprieta_dato_sito.setText(record[9])
            if data_dato:
                self.data_dato.setDateTime(data_dato)
            else:
                self.data_dato.setEmpty()
            self.ruolo.setText(record[11] or "owner")
            self.desc_dato.setText(record[12])
            self.formato.setText(record[13] or "mapDigital")
            self.tipo_dato.setText(record[14] or "vector")
            self.contatto_dato_nome.setText(record[15])
            self.contatto_dato_email.setText(record[16])
            self.contatto_dato_sito.setText(record[17])
            self.keywords.setText(record[18])
            self.keywords_inspire.setText(record[19])
            self.limitazione.setText(record[20] or "nessuna limitazione")
            self.vincoli_accesso.setText(record[21] or "nessuno")
            self.vincoli_fruibilita.setText(record[22] or "nessuno")
            self.vincoli_sicurezza.setText(record[23] or "nessuno")
            self.scala.setText(record[24])
            self.categoria_iso.setText(record[25] or "geoscientificInformation")
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

    def validate_input(self):
        """Enable the 'Save' button if all required fields are filled."""
        all_fields_filled = True
        css_style = "border: 1px solid red; border-radius: 3px;"
        for field in self.required_fields:
            if isinstance(field, QLineEdit) and field.isEnabled():
                if field.text() is None or field.text() == "":
                    field.setStyleSheet(css_style)
                    all_fields_filled = False
                else:
                    field.setStyleSheet("")
            if isinstance(field, QTextEdit):
                if not field.toPlainText():
                    field.setStyleSheet(css_style)
                    all_fields_filled = False
                else:
                    field.setStyleSheet("")
            if isinstance(field, QgsDateTimeEdit):
                if field.isNull() or not field.text():
                    field.setStyleSheet(css_style)
                    all_fields_filled = False
                else:
                    field.setStyleSheet("")
            self.button_box.setEnabled(all_fields_filled)

    def save_data(self):
        """Save the edited data back to the SQLite table."""
        qgs_log("Updating metadata record...", level="info")
        with sqlite3.connect(self.db_path) as conn:
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
                    self.data_metadato.text() if not self.data_metadato.isNull() else None,
                    self.srs_dati.text(),
                    self.proprieta_dato_nome.text(),
                    self.proprieta_dato_email.text(),
                    self.proprieta_dato_sito.text(),
                    self.data_dato.text() if not self.data_dato.isNull() else None,
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
        QMessageBox.information(self.iface.mainWindow(), self.tr("Success"), self.tr("Metadata updated successfully."))

    def get_comune_progetto(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM comune_progetto")
                record = cursor.fetchone()
        except sqlite3.Error as e:
            qgs_log(f"Error reading 'comune_progetto' table: {e}", level="error")
            return None
        return record

    def show_error(self, message):
        QMessageBox.critical(self.iface.mainWindow(), self.tr("Error"), self.tr(message))

    def tr(self, message):
        return QCoreApplication.translate("EditMetadataDialog", message)
