# -*- coding: utf-8 -*-

import traceback

from qgis.PyQt import QtCore

class AbstractWorker(QtCore.QObject):
    """Based on https://github.com/mbernasocchi/pyqtExperiments/blob/master/qgis_thread_example.py"""

    # available signals to be used in the concrete worker
    finished = QtCore.pyqtSignal(object)
    error = QtCore.pyqtSignal(Exception, str)
    progress = QtCore.pyqtSignal(float)
    toggle_show_progress = QtCore.pyqtSignal(bool)
    set_message = QtCore.pyqtSignal(str)
    set_log_message = QtCore.pyqtSignal(str)
    toggle_show_cancel = QtCore.pyqtSignal(bool)
    
    # private signal, don't use in concrete workers this is automatically
    # emitted if the result is not None
    successfully_finished = QtCore.pyqtSignal(object)

    def __init__(self):
        QtCore.QObject.__init__(self)
        self.killed = False

    def run(self):
        try:
            result = self.work()
            self.finished.emit(result)
        except UserAbortedNotification:
            self.finished.emit(None)
        except Exception as e:
            # forward the exception upstream
            self.error.emit(e, traceback.format_exc())
            self.finished.emit(None)

    def work(self):
        """ Reimplement this putting your calculation here
            available are:
                self.progress.emit(0-100)
                self.killed
            :returns a python object - use None if killed is true
        """

        raise NotImplementedError

    def kill(self):
        self.killed = True
        self.set_message.emit('Aborting...')
        self.toggle_show_progress.emit(False)


class UserAbortedNotification(Exception):
    pass
