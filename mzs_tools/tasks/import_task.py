import random
from pathlib import Path
from time import sleep

from qgis.core import QgsTask, Qgis, QgsMessageLog
from qgis.gui import QgisInterface
from qgis.utils import iface

from mzs_tools.core.mzs_project_manager import MzSProjectManager
from mzs_tools.plugin_utils.logging import MzSToolsLogger

iface: QgisInterface


class ImportTask(QgsTask):
    def __init__(self, input_path: Path, output_path: Path):
        super().__init__("Import data task", QgsTask.CanCancel)
        # self.duration = duration
        self.total = 0
        self.iterations = 0
        self.exception = None

        self.log = MzSToolsLogger().log

        self.input_path = input_path
        self.output_path = output_path
        self.prj_manager = MzSProjectManager.instance()

    def run(self):
        self.log("Running import task")
        self.total = 100
        self.iterations = 0

        self.log(f"Input path: {self.input_path}")
        self.log(f"Output path: {self.output_path}")

        # self.prj_manager.import_data(self.input_path, self.output_path)

        for i in range(100):
            sleep(0.1)
            # use setProgress to report progress
            self.setProgress(i)
            arandominteger = random.randint(0, 500)
            self.log(f"Random integer: {arandominteger}")
            self.total += arandominteger
            self.iterations += 1
            # check isCanceled() to handle cancellation
            if self.isCanceled():
                return False
            # simulate exceptions to show how to abort task
            if arandominteger == 42:
                # DO NOT raise Exception('bad value!')
                # this would crash QGIS
                self.exception = Exception("bad value!")
                return False
        return True

    def finished(self, result):
        if result:
            self.log(f"Task {self.description()} completed with {self.iterations} iterations - total: {self.total}")
        else:
            if self.exception is None:
                self.log(f"Task {self.description()} was canceled", log_level=1)
            else:
                self.log(f"Task {self.description()} failed: {self.exception}", log_level=2)

                raise self.exception

    def cancel(self):
        self.log(f"Task {self.description()} was canceled", log_level=1)

        super().cancel()
