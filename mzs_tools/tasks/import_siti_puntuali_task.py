import random
from pathlib import Path
from time import sleep

from qgis.core import QgsTask, Qgis, QgsMessageLog, QgsVectorLayer
from qgis.gui import QgisInterface
from qgis.utils import iface

from mzs_tools.core.mzs_project_manager import MzSProjectManager
from mzs_tools.plugin_utils.logging import MzSToolsLogger

iface: QgisInterface


class ImportSitiPuntualiTask(QgsTask):
    def __init__(self, input_path: Path):
        super().__init__("Import siti puntuali task", QgsTask.CanCancel)
        # self.duration = duration
        # self.total = 0
        self.iterations = 0
        self.exception = None

        self.log = MzSToolsLogger().log

        self.input_path = input_path
        self.prj_manager = MzSProjectManager.instance()

        siti_puntuali_shapefile_path = input_path / "Indagini" / "Ind_pu.shp"

        self.siti_puntuali_shapefile = QgsVectorLayer(str(siti_puntuali_shapefile_path), "Ind_pu", "ogr")
        # feature_counter = self.siti_puntuali_shapefile.countSymbolFeatures()
        # feature_counter.symbolsCounted.connect(lambda: self.)
        # feature_counter.waitForFinished()
        # self.siti_num = feature_counter.featureCount()
        self.num_siti = self.siti_puntuali_shapefile.featureCount()

    def run(self):
        self.log("Running import siti puntuali task")

        # self.total = 100
        self.iterations = 0

        self.log(f"Input path: {self.input_path}")
        # self.log(f"Output path: {self.output_path}")

        # self.prj_manager.import_data(self.input_path, self.output_path)

        features = self.siti_puntuali_shapefile.getFeatures()

        for feature in features:
            self.iterations += 1
            sleep(0.2)
            # use setProgress to report progress
            self.log(f"{self.iterations} / {self.num_siti}")
            self.setProgress(self.iterations * 100 / self.num_siti)
            self.log(f"ID_SPU: {feature['ID_SPU']} - {self.progress()}")

            # check isCanceled() to handle cancellation
            if self.isCanceled():
                return False

        return True

    def finished(self, result):
        if result:
            self.log(f"Task {self.description()} completed with {self.iterations} iterations")
        else:
            if self.exception is None:
                self.log(f"Task {self.description()} was canceled", log_level=1)
            else:
                self.log(f"Task {self.description()} failed: {self.exception}", log_level=2)

                raise self.exception

    def cancel(self):
        self.log(f"Task {self.description()} was canceled", log_level=1)

        super().cancel()
