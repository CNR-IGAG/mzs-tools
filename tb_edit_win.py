import os
import webbrowser

from qgis.core import *
from qgis.gui import *
from qgis.PyQt import QtGui, uic
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtWidgets import *
from qgis.utils import *


FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'tb_edit_win.ui'))


class edit_win(QDialog, FORM_CLASS):

    def __init__(self, parent=None):
        """Constructor."""
        super().__init__(parent)
        self.setupUi(self)
        self.plugin_dir = os.path.dirname(__file__)

    def edita(self):

        if len(QgsProject.instance().mapLayersByName("Siti puntuali")) == 0:
            QMessageBox.warning(
                None, self.tr('WARNING!'), self.tr("The tool must be used within an opened MS project!"))
            return

        self.help_button.clicked.connect(lambda: webbrowser.open(
            'https://www.youtube.com/watch?v=4jQ9OacJ71w&t=4s'))
        
        codici_mod_identcoord = []
        lista_mod_identcoord = []
        codici_modo_quota = []
        lista_modo_quota = []
        
        self.coord_x.clear()
        self.coord_y.clear()
        self.indirizzo.clear()
        self.mod_identcoord.clear()
        self.desc_modcoord.clear()
        self.quota_slm.clear()
        self.modo_quota.clear()
        self.note_sito.clear()

        # set calendar locale
        self.data_sito.clear()
        qgis_qlocale = QLocale(QSettings().value("locale/userLocale"))
        self.data_sito.setLocale(qgis_qlocale)
        today = QDate.currentDate()
        self.data_sito.setDate(today)

        self.alert_text.hide()
        self.button_box.setEnabled(False)

        self.coord_x.setValidator(QDoubleValidator(-170000, 801000, 2))
        self.coord_x.setMaxLength(9)

        self.coord_y.setValidator(QDoubleValidator(0, 5220000, 2))
        self.coord_y.setMaxLength(9)

        self.quota_slm.setValidator(QDoubleValidator(0, 4900, 0))
        self.quota_slm.setMaxLength(4)

        self.coord_x.textChanged.connect(self.disableButton)
        self.coord_y.textChanged.connect(self.disableButton)

        try:
            self.define_mod(codici_mod_identcoord,
                            "vw_mod_identcoord", lista_mod_identcoord)
            self.update_mod_box(self.mod_identcoord, codici_mod_identcoord)
            self.define_mod(codici_modo_quota,
                            "vw_modo_quota", lista_modo_quota)
            self.update_mod_box(self.modo_quota, codici_modo_quota)

        except IndexError:
            pass

        proj = QgsProject.instance()
        proj.writeEntry('Digitizing', 'SnappingMode', 'all_layers')
        proj.writeEntryDouble(
            'Digitizing', 'DefaultSnapTolerance', 20.0)

        self.show()
        self.adjustSize()
        result = self.exec_()
        if result:

            vectorLyr = QgsProject.instance().mapLayersByName("Siti puntuali")[0]
            it = vectorLyr.getFeatures()
            vpr = vectorLyr.dataProvider()

            idx1 = vpr.fields().lookupField("indirizzo")
            idx2 = vpr.fields().lookupField("desc_modcoord")
            idx3 = vpr.fields().lookupField("quota_slm")
            idx4 = vpr.fields().lookupField("data_sito")
            idx5 = vpr.fields().lookupField("note_sito")
            idx6 = vpr.fields().lookupField("mod_identcoord")
            idx7 = vpr.fields().lookupField("modo_quota")
            idx8 = vpr.fields().lookupField("ubicazione_prov")
            idx9 = vpr.fields().lookupField("ubicazione_com")
            idx10 = vpr.fields().lookupField("id_spu")

            attr = [None] * len(vpr.fields())

            attr[idx1] = self.indirizzo.text()
            attr[idx2] = self.desc_modcoord.text()
            attr[idx3] = self.quota_slm.text()
            attr[idx4] = self.data_sito.text()
            attr[idx5] = self.note_sito.toPlainText()
            attr[idx6] = self.mod_identcoord.currentText().strip().split(" - ")[0]
            attr[idx7] = self.modo_quota.currentText().strip().split(" - ")[0]
            attr[idx8] = self.ubicazione_prov.text()
            attr[idx9] = self.ubicazione_com.text()
            attr[idx10] = self.id_spu.text()

            pnt = QgsGeometry.fromPointXY(
                QgsPointXY(float(self.coord_x.text()), float(self.coord_y.text())))
            f = QgsFeature()
            f.setGeometry(pnt)
            f.setAttributes(attr)
            vpr.addFeatures([f])
            vectorLyr.updateExtents()

    def update_num(self, value, n1, n2):
        try:
            valore = int(value.text())
            if valore not in list(range(n1, n2)):
                value.setText('')
        except:
            value.setText('')

    def disableButton(self):
        if self.coord_x.hasAcceptableInput() and self.coord_y.hasAcceptableInput():
            self.alert_text.hide()
            self.button_box.setEnabled(True)
        else:
            self.alert_text.show()
            self.button_box.setEnabled(False)

    def define_mod(self, codici_mod, nome, lista):
        codici_mod_layer = QgsProject.instance().mapLayersByName(nome)[
            0]

        for classe in codici_mod_layer.getFeatures(QgsFeatureRequest().setFlags(QgsFeatureRequest.NoGeometry)):
            lista = [classe.attributes()[1], classe.attributes()[2]]
            codici_mod.append(lista)
        return codici_mod

    def update_mod_box(self, mod_box, codici_mod):
        mod_box.clear()
        mod_box.addItem("")
        mod_box.model().item(0).setEnabled(False)
        for row in codici_mod:
            mod_box.addItem(row[1])

    def tr(self, message):
        return QCoreApplication.translate('edit_win', message)
