from pathlib import Path

from qgis.PyQt import uic
from qgis.PyQt.QtCore import QCoreApplication, Qt
from qgis.PyQt.QtWidgets import QDialog, QDialogButtonBox
from qgis.utils import iface

from ..core.mzs_project_manager import MzSProjectManager
from ..plugin_utils.logging import MzSToolsLogger

FORM_CLASS, _ = uic.loadUiType(Path(__file__).parent / f"{Path(__file__).stem}.ui")


class DlgLoadOgcServices(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setupUi(self)
        self.iface = iface

        self.log = MzSToolsLogger.log
        self.prj_manager = MzSProjectManager.instance()

        self.cancel_button = self.button_box.button(QDialogButtonBox.Cancel)
        self.ok_button = self.button_box.button(QDialogButtonBox.Ok)

        self.ok_button.setEnabled(False)

        self.chk_regional_wms.stateChanged.connect(self.validate_input)
        self.chk_webms_wms.stateChanged.connect(self.validate_input)
        self.chk_webms_wfs.stateChanged.connect(self.validate_input)
        self.chk_geo_ispra.stateChanged.connect(self.validate_input)

        self.accepted.connect(self.load_services)

    def validate_input(self):
        if (
            self.chk_regional_wms.isChecked()
            or self.chk_webms_wms.isChecked()
            or self.chk_webms_wfs.isChecked()
            or self.chk_geo_ispra.isChecked()
        ):
            self.ok_button.setEnabled(True)
        else:
            self.ok_button.setEnabled(False)

    def load_services(self):
        regional_wms = self.chk_regional_wms.isChecked()
        webms_wms = self.chk_webms_wms.isChecked()
        webms_wfs = self.chk_webms_wfs.isChecked()
        geo_ispra = self.chk_geo_ispra.isChecked()

        self.log(
            f"Request to load OGC services: Regional WMS: {regional_wms}, WebMS WMS: {webms_wms}, WebMS WFS: {webms_wfs}, GeoISpra: {geo_ispra}",
            log_level=4,
        )

        root_layer_group = self.prj_manager.load_ogc_services(
            regional_wms=regional_wms, webms_wms=webms_wms, webms_wfs=webms_wfs, geo_ispra=geo_ispra
        )

        self.log(f"OGC services added to '{root_layer_group}' group", log_level=3, push=True)

    def tr(self, message: str) -> str:
        return QCoreApplication.translate(self.__class__.__name__, message)
