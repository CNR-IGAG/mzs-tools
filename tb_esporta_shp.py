import os
import time
import webbrowser

from qgis.core import QgsProject
from qgis.PyQt import uic
from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtWidgets import QDialog, QMessageBox
from qgis.utils import iface

from .setup_workers import setup_workers
from .utils import detect_mzs_tools_project
from .workers.export_worker import ExportWorker

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "tb_esporta_shp.ui"))


class esporta_shp(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super().__init__(parent)
        self.setupUi(self)
        self.plugin_dir = os.path.dirname(__file__)

    def esporta_prog(self):
        if not detect_mzs_tools_project():
            self.show_error(self.tr("The tool must be used within an opened MS project!"))
            return

        self.help_button.clicked.connect(
            lambda: webbrowser.open("https://mzs-tools.readthedocs.io/it/latest/plugin/esportazione.html")
        )
        self.dir_output.clear()
        # self.alert_text.hide()
        self.button_box.setEnabled(False)
        self.dir_output.textChanged.connect(self.disableButton)

        self.show()
        self.adjustSize()
        result = self.exec_()
        if result:
            try:
                in_dir = QgsProject.instance().readPath("./")
                out_dir = self.dir_output.text()
                if os.path.exists(out_dir):
                    # create export worker
                    worker = ExportWorker(in_dir, out_dir, self.plugin_dir)

                    # create export log file
                    logfile_path = os.path.join(
                        in_dir,
                        "Allegati",
                        "log",
                        str(time.strftime("%Y-%m-%d_%H-%M-%S", time.gmtime())) + "_export_log.txt",
                    )
                    log_file = open(logfile_path, "a")
                    log_file.write("EXPORT REPORT:" + "\n---------------\n\n")

                    # start export worker
                    setup_workers().start_worker(worker, iface, "Starting export task...", log_file, logfile_path)

                else:
                    QMessageBox.warning(None, self.tr("WARNING!"), self.tr("The selected directory does not exist!"))

            except Exception as z:
                self.show_error(f"{str(z)}")

    def disableButton(self):
        if self.dir_output.text() and os.path.exists(self.dir_output.text()):
            self.button_box.setEnabled(True)
        else:
            self.button_box.setEnabled(False)

    def show_error(self, message):
        QMessageBox.critical(iface.mainWindow(), self.tr("Error"), message)

    def tr(self, message):
        return QCoreApplication.translate("esporta_shp", message)
