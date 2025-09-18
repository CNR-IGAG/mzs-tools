import os
import sqlite3
import tempfile
import webbrowser
import zipfile
from contextlib import closing
from pathlib import Path

from qgis.PyQt import uic
from qgis.PyQt.QtCore import QCoreApplication, Qt
from qgis.PyQt.QtWidgets import QCompleter, QDialog, QDialogButtonBox, QFileDialog, QMessageBox

from ..__about__ import DIR_PLUGIN_ROOT

FORM_CLASS, _ = uic.loadUiType(Path(__file__).parent / f"{Path(__file__).stem}.ui")


class DlgCreateProject(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super().__init__(parent)
        self.setupUi(self)

        self.database_template_path = DIR_PLUGIN_ROOT / "data" / "indagini.sqlite.zip"

        self.output_dir_widget.setOptions(QFileDialog.Option.ShowDirsOnly)

        self.help_button = self.button_box.button(QDialogButtonBox.StandardButton.Help)
        self.cancel_button = self.button_box.button(QDialogButtonBox.StandardButton.Cancel)
        self.ok_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)

        # Load comuni data for autocomplete
        self.load_comuni_data()

        self.connect_signals()

    def connect_signals(self):
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        self.help_button.clicked.connect(
            lambda: webbrowser.open("https://mzs-tools.readthedocs.io/it/latest/plugin/nuovo_progetto.html")
        )
        self.comune_line_edit.textChanged.connect(self.update_cod_istat)
        self.study_author_line_edit.textChanged.connect(self.validate_input)
        self.author_email_line_edit.textChanged.connect(self.validate_input)
        self.output_dir_widget.lineEdit().textChanged.connect(self.validate_input)

    def showEvent(self, e):
        self.clear_fields()
        self.ok_button.setEnabled(False)

    def load_comuni_data(self):
        # Load comuni data from the project template
        with tempfile.TemporaryDirectory() as temp_dir:
            with zipfile.ZipFile(str(self.database_template_path), "r") as zip_ref:
                temp_db_path = zip_ref.extract("indagini.sqlite", temp_dir)

            # Load comuni data from temp db
            with closing(sqlite3.connect(temp_db_path)) as conn:
                with closing(conn.cursor()) as cursor:
                    cursor.execute("SELECT comune, cod_istat, provincia, regione FROM comuni")
                    self.comuni = cursor.fetchall()

        # Create a list of comuni names for the completer
        self.comuni_names = [f"{comune[0]} ({comune[2]} - {comune[3]})" for comune in self.comuni]

        # Set up the completer
        completer = QCompleter(self.comuni_names, self)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.comune_line_edit.setCompleter(completer)

    def clear_fields(self):
        self.comune_line_edit.clear()
        self.output_dir_widget.lineEdit().clear()
        self.cod_istat_line_edit.clear()
        self.study_author_line_edit.clear()
        self.author_email_line_edit.clear()

    def validate_input(self):
        if (
            self.cod_istat_line_edit.text()
            and self.study_author_line_edit.text()
            and self.author_email_line_edit.text()
            and self.output_dir_widget.lineEdit().text()
            and os.path.isdir(self.output_dir_widget.lineEdit().text())
        ):
            if (Path(self.output_dir_widget.lineEdit().text()) / "db" / "indagini.sqlite").exists():
                msg = self.tr(
                    "The selected directory seems to contain an MzS Tools project. Select a different directory."
                )
                QMessageBox.warning(None, self.tr("Warning"), msg)
                self.output_dir_widget.lineEdit().clear()
                return
            self.ok_button.setEnabled(True)
        else:
            self.ok_button.setEnabled(False)

    def update_cod_istat(self):
        comune_name = self.comune_line_edit.text()

        if comune_name not in self.comuni_names:
            self.cod_istat_line_edit.clear()
            self.ok_button.setEnabled(False)
        else:
            comune_record = next((comune for comune in self.comuni if comune[0] == comune_name.split(" (")[0]), None)
            if comune_record:
                self.cod_istat_line_edit.setText(comune_record[1])
                self.validate_input()

    def tr(self, message):
        return QCoreApplication.translate("NewProject", message)
