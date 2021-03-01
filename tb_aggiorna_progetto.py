from builtins import str
# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# Name:		tb_aggiorna_progetto.py
# Author:	  Tarquini E.
# Created:	 24-09-2018
#-------------------------------------------------------------------------------

from qgis.PyQt import QtGui, uic
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtWidgets import *
from qgis.utils import *
from qgis.core import *
from qgis.gui import *
import os
import sys
import webbrowser
import shutil
import sqlite3
import zipfile
import datetime


FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'tb_aggiorna_progetto.ui'))


class aggiorna_progetto(QDialog, FORM_CLASS):

    def __init__(self, parent=None):
        """Constructor."""
        super(aggiorna_progetto, self).__init__(parent)
        self.setupUi(self)
        self.plugin_dir = os.path.dirname(__file__)

    def aggiorna(self, dir2, dir_output, nome):
        self.show()
        result = self.exec_()
        if result:
            QgsProject.instance().clear()
            for c in iface.activeComposers():
                iface.deleteComposer(c)
            try:
                vers_data_1 = self.plugin_dir + os.sep + "versione.txt"
                new_vers = open(vers_data_1, 'r').read()
                vers_data_2 = dir2 + os.sep + "progetto" + os.sep + "versione.txt"
                proj_vers = open(vers_data_2, 'r').read()
                pacchetto = self.plugin_dir + os.sep + "data" + os.sep + "progetto_MS.zip"

                if proj_vers < '0.8' and new_vers == '1.3':
                    name_output = nome + "_backup_v" + proj_vers + "_" + \
                        datetime.datetime.now().strftime("%Y_%m_%d_%H_%M")
                    shutil.copytree(dir2, dir_output + os.sep + name_output)

                    path_db = dir2 + os.sep + "db" + os.sep + "indagini.sqlite"
                    sql_script = ["query_v08.sql",
                                  "query_v09.sql", "query_v10_12.sql"]
                    for x in sql_script:
                        self.sql_command(path_db, x)

                    zip_ref = zipfile.ZipFile(pacchetto, 'r')
                    zip_ref.extractall(dir2)
                    zip_ref.close()

                    shutil.rmtree(dir2 + os.sep + "progetto" +
                                  os.sep + "maschere")
                    shutil.copytree(dir2 + os.sep + "progetto_MS" + os.sep + "progetto" +
                                    os.sep + "maschere", dir2 + os.sep + "progetto" + os.sep + "maschere")
                    shutil.rmtree(dir2 + os.sep + "progetto" +
                                  os.sep + "script")
                    shutil.copytree(dir2 + os.sep + "progetto_MS" + os.sep + "progetto" +
                                    os.sep + "script", dir2 + os.sep + "progetto" + os.sep + "script")
                    os.remove(dir2 + os.sep + "progetto" +
                              os.sep + "versione.txt")
                    shutil.copyfile(dir2 + os.sep + "progetto_MS" + os.sep + "progetto" + os.sep +
                                    "versione.txt", dir2 + os.sep + "progetto" + os.sep + "versione.txt")
                    os.remove(dir2 + os.sep + "progetto_MS.qgs")
                    shutil.copyfile(dir2 + os.sep + "progetto_MS" + os.sep +
                                    "progetto_MS.qgs", dir2 + os.sep + "progetto_MS.qgs")
                    shutil.copyfile(dir2 + os.sep + "progetto_MS" + os.sep + "progetto" + os.sep + "loghi" + os.sep +
                                    "Legenda_valori_HVSR_rev01.svg", dir2 + os.sep + "progetto" + os.sep + "loghi" + os.sep + "Legenda_valori_HVSR_rev01.svg")
                    self.new_qgs_file(dir2)

                    shutil.rmtree(dir2 + os.sep + "progetto_MS")
                    QMessageBox.information(
                        None, u'INFORMATION!', u"The project structure has been updated!\nSAVE the project, please!\nThe backup copy has been saved in the following directory: " + dir_output + os.sep + name_output)

                elif proj_vers == '0.8' and new_vers == '1.3':
                    name_output = nome + "_backup_v" + proj_vers + "_" + \
                        datetime.datetime.now().strftime("%Y_%m_%d_%H_%M")
                    shutil.copytree(dir2, dir_output + os.sep + name_output)

                    path_db = dir2 + os.sep + "db" + os.sep + "indagini.sqlite"
                    sql_script = ["query_v09.sql", "query_v10_12.sql"]
                    for x in sql_script:
                        self.sql_command(path_db, x)

                    zip_ref = zipfile.ZipFile(pacchetto, 'r')
                    zip_ref.extractall(dir2)
                    zip_ref.close()

                    shutil.rmtree(dir2 + os.sep + "progetto" +
                                  os.sep + "maschere")
                    shutil.copytree(dir2 + os.sep + "progetto_MS" + os.sep + "progetto" +
                                    os.sep + "maschere", dir2 + os.sep + "progetto" + os.sep + "maschere")
                    shutil.rmtree(dir2 + os.sep + "progetto" +
                                  os.sep + "script")
                    shutil.copytree(dir2 + os.sep + "progetto_MS" + os.sep + "progetto" +
                                    os.sep + "script", dir2 + os.sep + "progetto" + os.sep + "script")
                    os.remove(dir2 + os.sep + "progetto" +
                              os.sep + "versione.txt")
                    shutil.copyfile(dir2 + os.sep + "progetto_MS" + os.sep + "progetto" + os.sep +
                                    "versione.txt", dir2 + os.sep + "progetto" + os.sep + "versione.txt")
                    os.remove(dir2 + os.sep + "progetto_MS.qgs")
                    shutil.copyfile(dir2 + os.sep + "progetto_MS" + os.sep +
                                    "progetto_MS.qgs", dir2 + os.sep + "progetto_MS.qgs")
                    self.new_qgs_file(dir2)

                    shutil.rmtree(dir2 + os.sep + "progetto_MS")
                    QMessageBox.information(
                        None, u'INFORMATION!', u"The project structure has been updated!\nSAVE the project, please!\nThe backup copy has been saved in the following directory: " + dir_output + os.sep + name_output)

                elif proj_vers >= '0.9' and proj_vers < '1.2' and new_vers == '1.3':
                    name_output = nome + "_backup_v" + proj_vers + "_" + \
                        datetime.datetime.now().strftime("%Y_%m_%d_%H_%M")
                    shutil.copytree(dir2, dir_output + os.sep + name_output)

                    path_db = dir2 + os.sep + "db" + os.sep + "indagini.sqlite"
                    sql_script = "query_v10_12.sql"
                    self.sql_command(path_db, sql_script)

                    zip_ref = zipfile.ZipFile(pacchetto, 'r')
                    zip_ref.extractall(dir2)
                    zip_ref.close()

                    shutil.rmtree(dir2 + os.sep + "progetto" +
                                  os.sep + "maschere")
                    shutil.copytree(dir2 + os.sep + "progetto_MS" + os.sep + "progetto" +
                                    os.sep + "maschere", dir2 + os.sep + "progetto" + os.sep + "maschere")
                    shutil.rmtree(dir2 + os.sep + "progetto" +
                                  os.sep + "script")
                    shutil.copytree(dir2 + os.sep + "progetto_MS" + os.sep + "progetto" +
                                    os.sep + "script", dir2 + os.sep + "progetto" + os.sep + "script")
                    os.remove(dir2 + os.sep + "progetto" +
                              os.sep + "versione.txt")
                    shutil.copyfile(dir2 + os.sep + "progetto_MS" + os.sep + "progetto" + os.sep +
                                    "versione.txt", dir2 + os.sep + "progetto" + os.sep + "versione.txt")
                    os.remove(dir2 + os.sep + "progetto_MS.qgs")
                    shutil.copyfile(dir2 + os.sep + "progetto_MS" + os.sep +
                                    "progetto_MS.qgs", dir2 + os.sep + "progetto_MS.qgs")
                    self.new_qgs_file(dir2)

                    shutil.rmtree(dir2 + os.sep + "progetto_MS")
                    QMessageBox.information(
                        None, u'INFORMATION!', u"The project structure has been updated!\nSAVE the project, please!\nThe backup copy has been saved in the following directory: " + dir_output + os.sep + name_output)

                elif proj_vers >= '1.2' and new_vers == '1.3':
                    name_output = nome + "_backup_v" + proj_vers + "_" + \
                        datetime.datetime.now().strftime("%Y_%m_%d_%H_%M")
                    shutil.copytree(dir2, dir_output + os.sep + name_output)

                    zip_ref = zipfile.ZipFile(pacchetto, 'r')
                    zip_ref.extractall(dir2)
                    zip_ref.close()

                    shutil.rmtree(dir2 + os.sep + "progetto" +
                                  os.sep + "maschere")
                    shutil.copytree(dir2 + os.sep + "progetto_MS" + os.sep + "progetto" +
                                    os.sep + "maschere", dir2 + os.sep + "progetto" + os.sep + "maschere")
                    shutil.rmtree(dir2 + os.sep + "progetto" +
                                  os.sep + "script")
                    shutil.copytree(dir2 + os.sep + "progetto_MS" + os.sep + "progetto" +
                                    os.sep + "script", dir2 + os.sep + "progetto" + os.sep + "script")
                    os.remove(dir2 + os.sep + "progetto" +
                              os.sep + "versione.txt")
                    shutil.copyfile(dir2 + os.sep + "progetto_MS" + os.sep + "progetto" + os.sep +
                                    "versione.txt", dir2 + os.sep + "progetto" + os.sep + "versione.txt")
                    os.remove(dir2 + os.sep + "progetto_MS.qgs")
                    shutil.copyfile(dir2 + os.sep + "progetto_MS" + os.sep +
                                    "progetto_MS.qgs", dir2 + os.sep + "progetto_MS.qgs")
                    self.new_qgs_file(dir2)

                    shutil.rmtree(dir2 + os.sep + "progetto_MS")
                    QMessageBox.information(
                        None, u'INFORMATION!', u"The project structure has been updated!\nSAVE the project, please!\nThe backup copy has been saved in the following directory: " + dir_output + os.sep + name_output)

            except Exception as z:
                QMessageBox.critical(
                    None, u'ERROR!', u'Error:\n"' + str(z) + '"')

    def sql_command(self, path_db, file_sql):
        conn = sqlite3.connect(path_db)
        cursor = conn.cursor()
        conn.text_factory = lambda x: str(x, 'utf-8', 'ignore')
        conn.enable_load_extension(True)
        f = open(self.plugin_dir + os.sep + file_sql)
        full_sql = f.read()
        sql_commands = full_sql.replace('\n', '').split(';;')[:-1]
        try:
            conn.execute('SELECT load_extension("mod_spatialite")')
            for sql_command in sql_commands:
                cursor.execute(sql_command)
            cursor.close()
            conn.commit()
        finally:
            conn.close()

    def new_qgs_file(self, dir2):
        project = QgsProject.instance()
        project.read(os.path.join(dir2, "progetto_MS.qgs"))
        zLayer = QgsProject.instance().mapLayersByName(
            "Comune del progetto")[0]

        features = zLayer.getFeatures()
        for feat in features:
            attrs = feat.attributes()
            codice_regio = attrs[1]

        sourceLYR = QgsProject.instance().mapLayersByName("Limiti comunali")[0]
        sourceLYR.setSubsetString("cod_regio='" + codice_regio + "'")
        canvas = iface.mapCanvas()
        extent = zLayer.extent()
        canvas.setExtent(extent)

        composers = iface.activeComposers()
        for composer_view in composers:
            composition = composer_view.composition()
            map_item = composition.getComposerItemById('mappa_0')
            map_item.setMapCanvas(canvas)
            map_item.zoomToExtent(canvas.extent())

        zLayer.removeSelection()
