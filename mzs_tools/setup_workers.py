import os
import shutil
import sys
from builtins import object

from qgis.core import *
from qgis.gui import *
from qgis.PyQt import QtGui, uic
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtWidgets import *
from qgis.utils import *


class setup_workers(object):
    def __init__(self, parent=None):
        """Constructor."""
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)

    def start_worker(self, worker, iface, message, log_file=None, logfile_path=None):
        ############################################
        # DEBUG ONLY
        # self.import_reset()
        ############################################

        # configure the QgsMessageBar
        message_bar_item = iface.messageBar().createMessage(message)
        progress_bar = QProgressBar()
        progress_bar.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        cancel_button = QPushButton()
        cancel_button.setText("Cancel")
        cancel_button.clicked.connect(worker.kill)
        message_bar_item.layout().addWidget(progress_bar)
        message_bar_item.layout().addWidget(cancel_button)
        iface.messageBar().pushWidget(message_bar_item, Qgis.Info)
        self.logfile_path = logfile_path

        # start the worker in a new thread
        thread = QThread(iface.mainWindow())
        worker.moveToThread(thread)

        worker.set_message.connect(lambda message: self.set_worker_message(message, message_bar_item))

        if log_file is not None:
            worker.set_log_message.connect(lambda message: self.set_worker_log_message(message, log_file))

        worker.toggle_show_progress.connect(lambda show: self.toggle_worker_progress(show, progress_bar))

        worker.toggle_show_cancel.connect(lambda show: self.toggle_worker_cancel(show, cancel_button))

        worker.finished.connect(
            lambda result: self.worker_finished(result, thread, worker, iface, message_bar_item, log_file)
        )

        worker.error.connect(lambda e, exception_str: self.worker_error(e, exception_str, iface, log_file))

        worker.progress.connect(progress_bar.setValue)

        thread.started.connect(worker.run)

        thread.start()
        return thread, message_bar_item

    def worker_finished(self, result, thread, worker, iface, message_bar_item, log_file=None):
        # remove widget from message bar
        iface.messageBar().popWidget(message_bar_item)
        if result is not None:
            # report the result
            if log_file is not None:
                log_file.write("\n\n" + result)
            iface.messageBar().pushMessage("Process finished: %s." % result)
            worker.successfully_finished.emit(result)
        else:
            if log_file is not None:
                log_file.write("\n\nProcess interrupted!")
            iface.messageBar().pushMessage("Process cancelled.", level=Qgis.Warning, duration=3)

        # clean up the worker and thread
        worker.deleteLater()
        thread.quit()
        thread.wait()
        thread.deleteLater()

        iface.mapCanvas().refreshAllLayers()

        if log_file is not None:
            log_file.close()

        if result is not None:
            QMessageBox.information(
                iface.mainWindow(),
                "INFORMATION!",
                "Process completed.\n\nReport was saved in the project folder: %s" % self.logfile_path,
            )
        else:
            QMessageBox.critical(
                iface.mainWindow(),
                "ERROR!",
                "Process interrupted! Read the report saved in the project folder: %s" % self.logfile_path,
            )

    def worker_error(self, e, exception_string, iface, log_file=None):
        # notify the user that something went wrong
        iface.messageBar().pushMessage(
            "Something went wrong! See the message log for more information.", level=Qgis.Critical, duration=3
        )
        QgsMessageLog.logMessage(
            "Worker thread raised an exception: %s" % exception_string, "Worker", level=Qgis.Critical
        )

        log_file.write("\n\n!!! Worker thread raised an exception:\n\n" + exception_string)

    def set_worker_message(self, message, message_bar_item):
        message_bar_item.setText(message)

    def set_worker_log_message(self, message, log_file):
        QgsMessageLog.logMessage(message, "MzSTools", level=Qgis.Info)
        log_file.write(message)

    def toggle_worker_progress(self, show_progress, progress_bar):
        progress_bar.setMinimum(0)
        if show_progress:
            progress_bar.setMaximum(100)
        else:
            # show an undefined progress
            progress_bar.setMaximum(0)

    def toggle_worker_cancel(self, show_cancel, cancel_button):
        cancel_button.setVisible(show_cancel)

    ############################################
    # DEBUG ONLY
    def import_reset(self):
        # nome = ['Altro', 'Documenti', 'Plot', 'Spettri']
        lista_layer = [
            "Siti puntuali",
            "Indagini puntuali",
            "Parametri puntuali",
            "Curve di riferimento",
            "Siti lineari",
            "Indagini lineari",
            "Parametri lineari",
            "Elementi geologici e idrogeologici puntuali",
            "Elementi puntuali",
            "Elementi lineari",
            "Forme",
            "Unita' geologico-tecniche",
            "Instabilita' di versante",
            "Isobate liv 1",
            "Zone stabili liv 1",
            "Zone instabili liv 1",
            "Isobate liv 2",
            "Zone stabili liv 2",
            "Zone instabili liv 2",
            "Isobate liv 3",
            "Zone stabili liv 3",
            "Zone instabili liv 3",
        ]

        for layer in iface.mapCanvas().layers():
            if layer.name() in lista_layer:
                with edit(layer):
                    listOfIds = [feat.id() for feat in layer.getFeatures()]
                    layer.deleteFeatures(listOfIds)

    ############################################
