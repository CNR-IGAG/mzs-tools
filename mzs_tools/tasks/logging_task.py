import logging

from qgis.PyQt import QtCore


class LoggingTask:
    log_msg = QtCore.pyqtSignal(str, int)

    def task_log(self, message: str = "", level=logging.INFO):
        self.log_msg.emit(message, level)
