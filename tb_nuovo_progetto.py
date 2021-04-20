# -*- coding: utf-8 -*-
# -------------------------------------------------------------------------------
# Name:		tb_nuovo_progetto.py
# Author:	  Tarquini E.
# Created:	 21-02-2018
# -------------------------------------------------------------------------------

import csv
import datetime
import os
import shutil
import sqlite3
import sys
import webbrowser
import zipfile

from qgis.core import *
from qgis.gui import *
from qgis.PyQt import QtGui, uic
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtWidgets import *
from qgis.utils import *
from .utils import save_map_image

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'tb_nuovo_progetto.ui'))


class nuovo_progetto(QDialog, FORM_CLASS):

    def __init__(self, iface, parent=None):
        """Constructor."""
        self.iface = iface
        super().__init__(parent)
        self.setupUi(self)
        self.plugin_dir = os.path.dirname(__file__)

    def nuovo(self):
        self.help_button.clicked.connect(lambda: webbrowser.open(
            'https://www.youtube.com/watch?v=TcaljLE5TCk&t=57s&list=PLM5qQOkOkzgWH2VogqeQIDybylmE4P1TQ&index=2'))
        dir_svg_input = os.path.join(self.plugin_dir, "img", "svg")
        dir_svg_output = self.plugin_dir.split("python")[0] + "svg"
        tabella_controllo = os.path.join(self.plugin_dir, "comuni.csv")
        pacchetto = os.path.join(self.plugin_dir, "data", "progetto_MS.zip")

        dizio_comuni = {}
        dict_comuni = {}

        with open(tabella_controllo, 'r') as csvfile:
            csvreader = csv.reader(csvfile, delimiter=';')
            for row in csvreader:
                cod_istat = str(row[2])
                nome_com = row[3]
                cod_com = row[4]
                nome_comune = cod_istat + "_" + cod_com
                dict_comuni[cod_istat] = nome_comune
                dizio_comuni[nome_com] = cod_istat

        data_meta = datetime.datetime.now().strftime(r"%d/%m/%Y")
        data_dato = datetime.datetime.now().strftime(r"%d/%m/%Y")

        self.dir_output.clear()
        self.comune.clear()
        self.cod_istat.clear()
        self.professionista.clear()
        self.email_prof.clear()
        self.sito_prof.clear()
        self.ufficio.clear()
        self.propretario.clear()
        self.email_prop.clear()
        self.sito_prop.clear()
        self.contatto.clear()
        self.email_cont.clear()
        self.sito_cont.clear()
        self.scala_nom.clear()
        self.accuratezza.clear()
        self.lineage.clear()
        self.descriz.clear()

        self.button_box.setEnabled(False)
        self.comune.addItems(sorted(dizio_comuni.keys()))
        self.comune.model().item(0).setEnabled(False)
        self.comune.currentIndexChanged.connect(lambda: self.update_cod_istat(
            dizio_comuni, str(self.comune.currentText()), self.cod_istat))
        self.scala_nom.textEdited.connect(
            lambda: self.update_num(self.scala_nom, 0, 100000))
        self.comune.currentIndexChanged.connect(self.disableButton)
        self.professionista.textChanged.connect(self.disableButton)
        self.email_prof.textChanged.connect(self.disableButton)
        self.sito_prof.textChanged.connect(self.disableButton)
        self.ufficio.textChanged.connect(self.disableButton)
        self.propretario.textChanged.connect(self.disableButton)
        self.email_prop.textChanged.connect(self.disableButton)
        self.sito_prop.textChanged.connect(self.disableButton)
        self.contatto.textChanged.connect(self.disableButton)
        self.sito_cont.textChanged.connect(self.disableButton)
        self.email_cont.textChanged.connect(self.disableButton)
        self.scala_nom.textChanged.connect(self.disableButton)
        self.accuratezza.textChanged.connect(self.disableButton)
        self.lineage.textChanged.connect(self.disableButton)
        self.descriz.textChanged.connect(self.disableButton)
        self.dir_output.textChanged.connect(self.disableButton)

        # Sample data for testing purposes
        # TODO: disable
        if False:
            d = QTemporaryDir()
            d.setAutoRemove(False)
            self.dir_output.setText(d.path())
            self.comune.setCurrentText('Luserna San Giovanni')
            self.cod_istat.setText('001139')
            self.professionista.setText('itopen')
            self.email_prof.setText('some text')
            self.sito_prof.setText('some text')
            self.ufficio.setText('some text')
            self.propretario.setText('some text')
            self.email_prop.setText('some text')
            self.sito_prop.setText('some text')
            self.contatto.setText('some text')
            self.email_cont.setText('some text')
            self.sito_cont.setText('some text')
            self.scala_nom.setText('50000')
            self.accuratezza.setText('some text')
            self.lineage.setText('some text')
            self.descriz.setText('some text')

        self.show()
        self.adjustSize()
        result = self.exec_()

        if result:

            dir_out = self.dir_output.text()
            if os.path.isdir(dir_out):
                try:
                    comune = str(self.comune.currentText())
                    cod_istat = self.cod_istat.text()
                    professionista = self.professionista.text()
                    email_prof = self.email_prof.text()
                    sito_prof = self.sito_prof.text()
                    ufficio = self.ufficio.text()
                    propretario = self.propretario.text()
                    email_prop = self.email_prop.text()
                    sito_prop = self.sito_prop.text()
                    contatto = self.contatto.text()
                    email_cont = self.email_cont.text()
                    sito_cont = self.sito_cont.text()
                    scala_nom = self.scala_nom.text()
                    accuratezza = self.accuratezza.text()
                    lineage = self.lineage.toPlainText()
                    descriz = self.descriz.toPlainText()

                    if not os.path.exists(dir_svg_output):
                        shutil.copytree(dir_svg_input, dir_svg_output)
                    else:
                        src_files = os.listdir(dir_svg_input)
                        for file_name in src_files:
                            full_file_name = os.path.join(
                                dir_svg_input, file_name)
                            if os.path.isfile(full_file_name):
                                shutil.copy(full_file_name, dir_svg_output)

                    zip_ref = zipfile.ZipFile(pacchetto, 'r')
                    zip_ref.extractall(dir_out)
                    zip_ref.close()
                    for x, y in list(dict_comuni.items()):
                        if x == cod_istat:
                            comune_nome = (y[6:]).replace("_", " ")
                            path_comune = os.path.join(dir_out, y)
                            os.rename(os.path.join(
                                dir_out, "progetto_MS"), path_comune)

                    project = QgsProject.instance()
                    project.read(os.path.join(path_comune, "progetto_MS.qgs"))

                    layer_limiti_comunali = QgsProject.instance(
                    ).mapLayersByName("Limiti comunali")[0]
                    req = QgsFeatureRequest()
                    req.setFilterExpression('"cod_istat" = \'%s\'' % cod_istat)
                    selection = layer_limiti_comunali.getFeatures(req)
                    layer_limiti_comunali.selectByIds(
                        [k.id() for k in selection])

                    layer_comune_progetto = QgsProject.instance(
                    ).mapLayersByName("Comune del progetto")[0]
                    selected_features = layer_limiti_comunali.selectedFeatures()

                    features = []
                    for i in selected_features:
                        features.append(i)

                    layer_comune_progetto.startEditing()
                    data_provider = layer_comune_progetto.dataProvider()
                    data_provider.addFeatures(features)
                    layer_comune_progetto.commitChanges()

                    features = layer_comune_progetto.getFeatures()
                    for feat in features:
                        attrs = feat.attributes()
                        codice_regio = attrs[1]
                        codice_prov = attrs[2]
                        codice_com = attrs[3]
                        nome = attrs[4]
                        regione = attrs[7]
                        provincia = attrs[6]

                    layer_limiti_comunali.removeSelection()

                    layer_limiti_comunali.setSubsetString(
                        "cod_regio='" + codice_regio + "'")

                    logo_regio_in = os.path.join(
                        self.plugin_dir, "img", "logo_regio", codice_regio + ".png").replace('\\', '/')
                    logo_regio_out = os.path.join(
                        path_comune, "progetto", "loghi", "logo_regio.png").replace('\\', '/')
                    shutil.copyfile(logo_regio_in, logo_regio_out)

                    mainPath = QgsProject.instance().homePath()
                    canvas = self.iface.mapCanvas()

                    QgsMessageLog.logMessage(
                        'Canvas WKT %s' % canvas.extent().asWktPolygon())
                    QgsMessageLog.logMessage(
                        'layer_limiti_comunali WKT %s' % layer_limiti_comunali.extent().asWktPolygon())

                    imageFilename = os.path.join(
                        mainPath, "progetto", "loghi", "mappa_reg.png")
                    save_map_image(
                        imageFilename, layer_limiti_comunali, canvas)

                    extent = layer_comune_progetto.dataProvider().extent()
                    canvas.setExtent(extent)

                    QgsMessageLog.logMessage(
                        'Canvas WKT %s' % canvas.extent().asWktPolygon())
                    QgsMessageLog.logMessage(
                        'layer_comune_progetto data provider WKT %s' % extent.asWktPolygon())

                    layout_manager = QgsProject.instance().layoutManager()
                    layouts = layout_manager.printLayouts()

                    for layout in layouts:
                        map_item = layout.itemById('mappa_0')
                        map_item.setExtent(canvas.extent())
                        map_item_2 = layout.itemById(
                            'regio_title')
                        map_item_2.setText("Regione " + regione)
                        map_item_3 = layout.itemById(
                            'com_title')
                        map_item_3.setText("Comune di " + nome)
                        map_item_4 = layout.itemById('logo')
                        map_item_4.refreshPicture()
                        map_item_5 = layout.itemById('mappa_1')
                        map_item_5.refreshPicture()

                    self.indice_tab_execute(data_meta, regione, codice_regio, provincia,
                                            codice_prov, nome, codice_com, professionista, ufficio, propretario)
                    self.metadati_tab_execute(codice_prov, codice_com, professionista, email_prof, sito_prof, data_meta, ufficio, propretario,
                                              email_prop, sito_prop, data_dato, descriz, contatto, email_cont, sito_cont, scala_nom, extent, accuratezza, lineage)

                    # Save the project!
                    project.write(os.path.join(path_comune, "progetto_MS.qgs"))

                    QMessageBox.information(
                        None, 'INFORMATION!', "The project has been created successfully.")

                except Exception as z:
                    raise z
                    QMessageBox.critical(
                        None, 'ERROR!', 'Error:\n"' + str(z) + '"')
                    if os.path.exists(os.path.join(dir_out, "progetto_MS")):
                        shutil.rmtree(os.path.join(dir_out, "progetto_MS"))

            else:
                QMessageBox.warning(
                    self.iface.mainWindow(), 'WARNING!', "The selected directory does not exist!")

    def disableButton(self):
        check_campi = [self.professionista.text(), self.email_prof.text(), self.sito_prof.text(), self.propretario.text(), self.ufficio.text(), self.email_prop.text(), self.sito_prop.text(), self.contatto.text(
        ), self.email_cont.text(), self.sito_cont.text(), self.scala_nom.text(), self.dir_output.text(), self.accuratezza.text(), self.lineage.toPlainText(), self.descriz.toPlainText(), str(self.comune.currentText())]
        check_value = []

        for x in check_campi:
            if len(x) > 0:
                value_campi = 1
                check_value.append(value_campi)
            else:
                value_campi = 0
                check_value.append(value_campi)

        campi = sum(check_value)
        if campi > 15:
            self.button_box.setEnabled(True)
        else:
            self.button_box.setEnabled(False)

    def update_cod_istat(self, dizionario, nome_comune_sel, campo):
        for chiave, valore in list(dizionario.items()):
            if chiave == nome_comune_sel:
                campo.setText(valore)

    def update_num(self, value, n1, n2):
        try:
            valore = int(value.text())
            if valore not in list(range(n1, n2)):
                value.setText('')
        except:
            value.setText('')

    def indice_tab_execute(self, data_meta, regione, codice_regio, provincia, codice_prov, nome, codice_com, professionista, ufficio, propretario):
        orig_gdb = QgsProject.instance().readPath(
            os.path.join("db", "indagini.sqlite"))
        conn = sqlite3.connect(orig_gdb)
        sql = """ATTACH '""" + orig_gdb + """' AS A;"""
        conn.execute(sql)
        conn.execute("""INSERT INTO 'indice'(data_in,regione,cod_reg,provincia,cod_prov,comune,cod_com,soggetto,ufficio,responsabile,ID_MZS) VALUES ('""" + data_meta + """', '""" + regione + """', '""" + codice_regio + """',
			'""" + self.changeWord(provincia) + """', '""" + codice_prov + """', '""" + self.changeWord(nome) + """', '""" + codice_com + """', '""" + self.changeWord(professionista) + """', '""" + self.changeWord(ufficio) + """',
			'""" + self.changeWord(propretario) + """', '""" + codice_prov + codice_com + """');""")
        conn.commit()
        conn.close()

    def metadati_tab_execute(self, codice_prov, codice_com, professionista, email_prof, sito_prof, data_meta, ufficio, propretario, email_prop, sito_prop, data_dato, descriz, contatto, email_cont, sito_cont, scala_nom, extent, accuratezza, lineage):
        orig_gdb = QgsProject.instance().readPath(
            os.path.join("db", "indagini.sqlite"))
        conn = sqlite3.connect(orig_gdb)
        sql = """ATTACH '""" + orig_gdb + """' AS A;"""
        conn.execute(sql)
        conn.execute("""INSERT INTO 'metadati'("id_metadato", "liv_gerarchico", "resp_metadato_nome", "resp_metadato_email", "resp_metadato_sito", "data_metadato", "srs_dati", "proprieta_dato_nome", "proprieta_dato_email", "proprieta_dato_sito",
			"data_dato", "ruolo", "desc_dato", "formato", "tipo_dato", "contatto_dato_nome", "contatto_dato_email", "contatto_dato_sito", "keywords", "keywords_inspire", "limitazione", "vincoli_accesso", "vincoli_fruibilita", "vincoli_sicurezza",
			"scala", "categoria_iso", "estensione_ovest", "estensione_est", "estensione_sud", "estensione_nord", "precisione", "genealogia")
			VALUES ('""" + codice_prov + codice_com + """M1', 'series','""" + self.changeWord(professionista) + """', '""" + self.changeWord(email_prof) + """', '""" + self.changeWord(sito_prof) + """', '""" + self.changeWord(data_meta) + """',
			32633,'""" + self.changeWord(ufficio) + """ """ + self.changeWord(propretario) + """', '""" + self.changeWord(email_prop) + """', '""" + self.changeWord(sito_prop) + """', '""" + self.changeWord(data_dato) + """', 'owner',
			'""" + self.changeWord(descriz) + """', 'mapDigital','vector','""" + self.changeWord(contatto) + """', '""" + self.changeWord(email_cont) + """', '""" + self.changeWord(sito_cont) + """', '(Microzonazione Sismica, Pericolosita Sismica)',
			'(Zone a rischio naturale, Geologia)','nessuna limitazione','nessuno','nessuno','nessuno','""" + self.changeWord(scala_nom) + """', 'geoscientificInformation',  '""" + str(extent.xMinimum()) + """', '""" + str(extent.xMaximum()) + """',
            '""" + str(extent.yMinimum()) + """', '""" + str(extent.yMaximum()) + """', '""" + self.changeWord(accuratezza) + """', '""" + self.changeWord(lineage) + """');""")
        conn.commit()
        conn.close()

    def changeWord(self, word):
        for letter in word:
            if letter == "'":
                word = word.replace(letter, "''")
        return word
