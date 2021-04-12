# -*- coding: utf-8 -*-
# -------------------------------------------------------------------------------
# Name:		tb_aggiorna_progetto.py
# Author:	  Tarquini E.
# Created:	 24-09-2018
# -------------------------------------------------------------------------------

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
        if result == QDialog.Accepted:

            QgsProject.instance().clear()

            try:
                vers_data_1 = os.path.join(self.plugin_dir, "versione.txt")
                new_vers = open(vers_data_1, 'r').read()
                vers_data_2 = os.path.join(dir2, "progetto", "versione.txt")
                proj_vers = open(vers_data_2, 'r').read()
                pacchetto = os.path.join(
                    self.plugin_dir, "data", "progetto_MS.zip")

                if proj_vers < '0.8' and new_vers == '1.3':
                    name_output = nome + "_backup_v" + proj_vers + "_" + \
                        datetime.datetime.now().strftime("%Y_%m_%d_%H_%M")
                    shutil.copytree(dir2, os.path.join(
                        dir_output, name_output))

                    path_db = os.path.join(dir2, "db", "indagini.sqlite")
                    sql_script = ["query_v08.sql",
                                  "query_v09.sql", "query_v10_12.sql"]
                    for x in sql_script:
                        self.sql_command(path_db, x)

                    zip_ref = zipfile.ZipFile(pacchetto, 'r')
                    zip_ref.extractall(dir2)
                    zip_ref.close()

                    shutil.rmtree(os.path.join(dir2, "progetto", "maschere"))
                    shutil.copytree(os.path.join(dir2, "progetto_MS", "progetto", "maschere"), os.path.join(
                        dir2, "progetto", "maschere"))
                    shutil.rmtree(os.path.join(dir2, "progetto", "script"))
                    shutil.copytree(os.path.join(dir2, "progetto_MS", "progetto", "script"), os.path.join(
                        dir2, "progetto", "script"))
                    os.remove(os.path.join(dir2, "progetto", "versione.txt"))
                    shutil.copyfile(os.path.join(dir2, "progetto_MS", "progetto", "versione.txt"), os.path.join(
                        dir2, "progetto", "versione.txt"))
                    os.remove(os.path.join(dir2, "progetto_MS.qgs"))
                    shutil.copyfile(os.path.join(
                        dir2, "progetto_MS", "progetto_MS.qgs"), os.path.join(dir2, "progetto_MS.qgs"))
                    shutil.copyfile(os.path.join(dir2, "progetto_MS", "progetto", "loghi", "Legenda_valori_HVSR_rev01.svg"), os.path.join(
                        dir2, "progetto", "loghi", "Legenda_valori_HVSR_rev01.svg"))

                    self.load_new_qgs_file(dir2)

                    shutil.rmtree(os.path.join(dir2, "progetto_MS"))
                    QMessageBox.information(
                        None, 'INFORMATION!', "The project structure has been updated!\nSAVE the project, please!\nThe backup copy has been saved in the following directory: " + dir_output, name_output)

                elif proj_vers == '0.8' and new_vers == '1.3':
                    name_output = nome + "_backup_v" + proj_vers + "_" + \
                        datetime.datetime.now().strftime("%Y_%m_%d_%H_%M")
                    shutil.copytree(dir2, os.path.join(
                        dir_output, name_output))

                    path_db = os.path.join(dir2, "db", "indagini.sqlite")
                    sql_script = ["query_v09.sql", "query_v10_12.sql"]

                    for x in sql_script:
                        self.sql_command(path_db, x)

                    zip_ref = zipfile.ZipFile(pacchetto, 'r')
                    zip_ref.extractall(dir2)
                    zip_ref.close()

                    shutil.rmtree(os.path.join(dir2, "progetto", "maschere"))
                    shutil.copytree(os.path.join(dir2, "progetto_MS", "progetto", "maschere"), os.path.join(
                        dir2, "progetto", "maschere"))
                    shutil.rmtree(os.path.join(dir2, "progetto", "script"))
                    shutil.copytree(os.path.join(dir2, "progetto_MS", "progetto", "script"), os.path.join(
                        dir2, "progetto", "script"))
                    os.remove(os.path.join(dir2, "progetto", "versione.txt"))
                    shutil.copyfile(os.path.join(dir2, "progetto_MS", "progetto", "versione.txt"), os.path.join(
                        dir2, "progetto", "versione.txt"))
                    os.remove(os.path.join(dir2, "progetto_MS.qgs"))
                    shutil.copyfile(os.path.join(
                        dir2, "progetto_MS", "progetto_MS.qgs"), os.path.join(dir2, "progetto_MS.qgs"))

                    self.load_new_qgs_file(dir2)

                    shutil.rmtree(os.path.join(dir2, "progetto_MS"))
                    QMessageBox.information(
                        None, 'INFORMATION!', "The project structure has been updated!\nSAVE the project, please!\nThe backup copy has been saved in the following directory: " + dir_output, name_output)

                elif proj_vers >= '0.9' and proj_vers < '1.2' and new_vers == '1.3':
                    name_output = nome + "_backup_v" + proj_vers + "_" + \
                        datetime.datetime.now().strftime("%Y_%m_%d_%H_%M")
                    shutil.copytree(dir2, os.path.join(
                        dir_output, name_output))

                    path_db = os.path.join(dir2, "db", "indagini.sqlite")
                    sql_script = "query_v10_12.sql"
                    self.sql_command(path_db, sql_script)

                    zip_ref = zipfile.ZipFile(pacchetto, 'r')
                    zip_ref.extractall(dir2)
                    zip_ref.close()

                    shutil.rmtree(os.path.join(dir2, "progetto", "maschere"))
                    shutil.copytree(os.path.join(dir2, "progetto_MS", "progetto", "maschere"), os.path.join(
                        dir2, "progetto", "maschere"))
                    shutil.rmtree(os.path.join(dir2, "progetto", "script"))
                    shutil.copytree(os.path.join(dir2, "progetto_MS", "progetto", "script"), os.path.join(
                        dir2, "progetto", "script"))
                    os.remove(os.path.join(dir2, "progetto", "versione.txt"))
                    shutil.copyfile(os.path.join(dir2, "progetto_MS", "progetto", "versione.txt"), os.path.join(
                        dir2, "progetto", "versione.txt"))
                    os.remove(os.path.join(dir2, "progetto_MS.qgs"))
                    shutil.copyfile(os.path.join(
                        dir2, "progetto_MS", "progetto_MS.qgs"), os.path.join(dir2, "progetto_MS.qgs"))

                    self.load_new_qgs_file(dir2)

                    shutil.rmtree(os.path.join(dir2, "progetto_MS"))
                    QMessageBox.information(
                        None, 'INFORMATION!', "The project structure has been updated!\nSAVE the project, please!\nThe backup copy has been saved in the following directory: " + dir_output, name_output)

                elif proj_vers >= '1.2' and new_vers == '1.3':
                    name_output = nome + "_backup_v" + proj_vers + "_" + \
                        datetime.datetime.now().strftime("%Y_%m_%d_%H_%M")
                    shutil.copytree(dir2, os.path.join(
                        dir_output, name_output))

                    zip_ref = zipfile.ZipFile(pacchetto, 'r')
                    zip_ref.extractall(dir2)
                    zip_ref.close()

                    shutil.rmtree(os.path.join(dir2, "progetto", "maschere"))
                    shutil.copytree(os.path.join(dir2, "progetto_MS", "progetto", "maschere"), os.path.join(
                        dir2, "progetto", "maschere"))
                    shutil.rmtree(os.path.join(dir2, "progetto", "script"))
                    shutil.copytree(os.path.join(dir2, "progetto_MS", "progetto", "script"), os.path.join(
                        dir2, "progetto", "script"))
                    os.remove(os.path.join(dir2, "progetto", "versione.txt"))
                    shutil.copyfile(os.path.join(dir2, "progetto_MS", "progetto", "versione.txt"), os.path.join(
                        dir2, "progetto", "versione.txt"))
                    os.remove(os.path.join(dir2, "progetto_MS.qgs"))
                    shutil.copyfile(os.path.join(
                        dir2, "progetto_MS", "progetto_MS.qgs"), os.path.join(dir2, "progetto_MS.qgs"))

                    self.load_new_qgs_file(dir2)

                    shutil.rmtree(os.path.join(dir2, "progetto_MS"))
                    QMessageBox.information(
                        None, 'INFORMATION!', "The project structure has been updated!\nSAVE the project, please!\nThe backup copy has been saved in the following directory: " + dir_output, name_output)

            except Exception as z:
                QMessageBox.critical(
                    None, 'ERROR!', 'Error:\n"' + str(z) + '"')

    def sql_command(self, path_db, file_sql):
        conn = sqlite3.connect(path_db)
        cursor = conn.cursor()
        conn.text_factory = lambda x: str(x, 'utf-8', 'ignore')
        conn.enable_load_extension(True)
        f = open(self.plugin_dir, file_sql)
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

    def load_new_qgs_file(self, dir2):

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
            map_item.setExtent(canvas.extent())

        zLayer.removeSelection()
