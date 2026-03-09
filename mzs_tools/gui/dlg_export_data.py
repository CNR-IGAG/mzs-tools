# -----------------------------------------------------------------------------
# Copyright (C) 2018-2026, CNR-IGAG LabGIS <labgis@igag.cnr.it>
# This file is part of MzS Tools.
#
# MzS Tools is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# MzS Tools is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with MzS Tools.  If not, see <https://www.gnu.org/licenses/>.
# -----------------------------------------------------------------------------

from functools import partial
from pathlib import Path
from typing import cast

from qgis.gui import QgisInterface
from qgis.PyQt import uic
from qgis.PyQt.QtCore import QCoreApplication, QUrl
from qgis.PyQt.QtGui import QDesktopServices
from qgis.PyQt.QtWidgets import (
    QDialog,
    QDialogButtonBox,
)
from qgis.utils import iface

from ..__about__ import DIR_PLUGIN_ROOT
from ..core.mzs_project_manager import MzSProjectManager
from ..plugin_utils.logging import MzSToolsLogger
from ..tasks.access_db_connection import AccessDbConnection, JVMError
from ..tasks.export_data_task_manager import ExportDataTaskManager

FORM_CLASS, _ = uic.loadUiType(Path(__file__).parent / f"{Path(__file__).stem}.ui")


class DlgExportData(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setupUi(self)
        self.iface: QgisInterface = cast(QgisInterface, iface)
        self.log = MzSToolsLogger.log

        self.prj_manager = MzSProjectManager.instance()

        self.help_button = self.button_box.button(QDialogButtonBox.StandardButton.Help)
        self.cancel_button = self.button_box.button(QDialogButtonBox.StandardButton.Cancel)
        self.ok_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)

        self.ok_button.setText(self.tr("Start export"))
        self.ok_button.setEnabled(False)
        self.radio_button_mdb.setEnabled(False)
        self.radio_button_sqlite.setEnabled(True)

        self.output_dir_widget.lineEdit().textChanged.connect(self.validate_input)
        self.radio_button_mdb.toggled.connect(self.validate_input)
        self.radio_button_sqlite.toggled.connect(self.validate_input)

        self.label_mdb_msg.setText("")
        self.label_mdb_msg.setVisible(True)

        self.help_button.pressed.connect(
            partial(QDesktopServices.openUrl, QUrl("https://cnr-igag.github.io/mzs-tools/plugin/esportazione.html"))
        )

        self.output_path = None

        self.accepted.connect(self.start_export_tasks)

        self.mdb_checked = False

        self.export_data_task_manager: ExportDataTaskManager | None = None

        # Exported project standard version, used to select CdI_Tabelle.mdb model and for naming the output folder
        # TODO: should be centralized and could be selectable by the user
        self.standard_version_string = "S42"
        # TODO: the file(s) should be renamed to f"CdI_Tabelle_{self.standard_version_string}.mdb"
        self.cdi_tabelle_model_file = "CdI_Tabelle_4.2.mdb"

    def showEvent(self, e):
        super().showEvent(e)
        self.output_dir_widget.lineEdit().setText("")

        if not self.mdb_checked:
            # test mdb connection
            cdi_tabelle_path = DIR_PLUGIN_ROOT / "data" / self.cdi_tabelle_model_file
            connected = self.check_mdb_connection(cdi_tabelle_path)
            self.radio_button_mdb.setEnabled(connected)
            self.mdb_checked = connected

    def validate_input(self):
        """Validate user input and enable/disable the OK button accordingly."""
        # Check output directory
        if not self.validate_output_dir():
            self.log("Output path is not valid", log_level=1)
            self.ok_button.setEnabled(False)
            return False

        # Check if a data source is selected
        if not (self.radio_button_mdb.isChecked() or self.radio_button_sqlite.isChecked()):
            self.log("No data source selected", log_level=1)
            self.ok_button.setEnabled(False)
            return False

        # All validations passed
        self.ok_button.setEnabled(True)
        return True

    def validate_output_dir(self):
        """Validate that the output directory exists."""
        output_dir = self.output_dir_widget.lineEdit().text()

        is_valid = output_dir and Path(output_dir).exists()
        if is_valid:
            self.output_path = Path(output_dir)

        return is_valid

    def check_mdb_connection(self, mdb_path):
        """Test connection to an Access database."""
        connected = False
        mdb_conn = None

        try:
            mdb_conn = AccessDbConnection(mdb_path)
            connected = mdb_conn.open()
            if connected:
                self.label_mdb_msg.setText(self.tr("[Connection established]"))
                self.radio_button_mdb.setToolTip("")

        except ImportError as e:
            error_msg = self.tr("Use the dependency check tool or 'qpip' QGIS plugin to install dependencies.")
            self.log(f"{e}. {error_msg}", log_level=1)
            self.label_mdb_msg.setText(f"[{e}]")
            self.radio_button_mdb.setToolTip(error_msg)
        except JVMError as e:
            self.log(f"{e}", log_level=1)
            self.label_mdb_msg.setText(f"[{e} - check your Java JVM installation]")
        except Exception as e:
            self.log(f"{e}", log_level=2)
            self.label_mdb_msg.setText(self.tr("[Connection failed]"))
        finally:
            if mdb_conn and connected:
                mdb_conn.close()

        return connected

    def start_export_tasks(self):
        """Start export tasks based on user selections."""
        if not self.prj_manager.project_path or not self.output_path:
            self.log("Project path or output path not set", log_level=2)
            return

        if self.radio_button_mdb.isChecked():
            indagini_output_format = "mdb"
        elif self.radio_button_sqlite.isChecked():
            indagini_output_format = "sqlite"
        else:
            self.log("No output format selected", log_level=1)
            return

        self.export_data_task_manager = ExportDataTaskManager(
            output_path=self.output_path,
            indagini_output_format=indagini_output_format,
            standard_version_string=self.standard_version_string,
            cdi_tabelle_model_file=self.cdi_tabelle_model_file,
            debug_mode=self.chk_debug_logging.isChecked(),
        )
        self.export_data_task_manager.start_export_tasks()

    def tr(self, message: str) -> str:
        return QCoreApplication.translate(self.__class__.__name__, message)
