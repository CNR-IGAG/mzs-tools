# -----------------------------------------------------------------------------
# Copyright (C) 2018-2026, CNR-IGAG LabGIS <labgis@igag.cnr.it>
# This file is part of MzS Tools.
#
# MzS Tools is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# MzS Tools is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with MzS Tools.  If not, see <https://www.gnu.org/licenses/>.
# -----------------------------------------------------------------------------

import shutil
import warnings
from unittest.mock import Mock

import pytest
from qgis.core import QgsProject

from mzs_tools.__about__ import DIR_PLUGIN_ROOT, __base_version__
from mzs_tools.gui.dlg_export_data import DlgExportData
from mzs_tools.tasks.export_project_files_task import ExportProjectFilesTask
from mzs_tools.tasks.export_siti_lineari_task import ExportSitiLineariTask
from mzs_tools.tasks.export_siti_puntuali_task import ExportSitiPuntualiTask


def test_export_data(
    plugin,
    qgis_app,
    qgis_iface,
    prj_manager,
    base_project_path_current_imported,
    mdb_deps_available,
    monkeypatch,
    qtbot,
    tmp_path,
):
    monkeypatch.setattr(qgis_iface, "messageBar", lambda: Mock(), raising=False)
    plugin_instance = plugin(qgis_iface)

    project_file = base_project_path_current_imported / "progetto_MS.qgz"

    # Create a new project
    project = QgsProject.instance()

    # open the project
    project.read(str(project_file))

    plugin_instance.check_project()

    assert prj_manager.is_mzs_project is True
    assert prj_manager.project_updateable is False

    dialog = DlgExportData()

    qtbot.addWidget(dialog)
    dialog.show()

    dialog.output_dir_widget.lineEdit().setText(str(tmp_path))

    # TODO: import/export from/to mdb using QGIS task manager causes threading issues in tests, with pytest hanging at the end:
    # QObject::killTimer: Timers cannot be stopped from another thread
    # QObject::~QObject: Timers cannot be stopped from another thread
    # if mdb_deps_available:
    #     # test MDB connection
    #     cdi_tabelle_path = DIR_PLUGIN_ROOT / "data" / dialog.cdi_tabelle_model_file
    #     mdb_connected = dialog.check_mdb_connection(cdi_tabelle_path)
    #     dialog.radio_button_mdb.setEnabled(mdb_connected)
    #     if mdb_connected:
    #         dialog.radio_button_mdb.setChecked(True)
    # else:
    #     dialog.radio_button_sqlite.setChecked(True)

    dialog.radio_button_sqlite.setChecked(True)

    assert dialog.ok_button.isEnabled() is True

    with qtbot.waitSignal(qgis_app.taskManager().allTasksFinished, timeout=10000) as blocker:
        # blocker.connect(app.worker.failed)  # Can add other signals to blocker
        # accept() will run start_import_tasks
        dialog.accept()
        # Test will block at this point until either the signal is emitted.
        # If 10 seconds passed without a signal, qtbot.TimeoutError will be raised.
        # The allTasksFinished signal is bugged or unreliable though, so we make sure
        # all tasks are really done by checking the active task count
        # warnings.warn(f"Total tasks: {qgis_app.taskManager().countActiveTasks()}", UserWarning)
        qtbot.wait(1000)
        while qgis_app.taskManager().countActiveTasks() > 0:
            qtbot.wait(1000)
    assert blocker.signal_triggered is True

    # TODO: verify exported data
    exported_project_dir = tmp_path / "057001_Accumoli_S42_Shapefile"
    assert exported_project_dir.exists()


def test_export_siti_puntuali_task_to_mdb(
    plugin,
    qgis_iface,
    prj_manager,
    base_project_path_current_imported,
    mdb_deps_available,
    tmp_path,
):
    # exit if mdb dependencies are not available
    if not mdb_deps_available:
        warnings.warn("MDB dependencies not available, skipping MDB import test", UserWarning)
        return

    plugin_instance = plugin(qgis_iface)

    project_file = base_project_path_current_imported / "progetto_MS.qgz"

    # Create a new project
    project = QgsProject.instance()

    # open the project
    project.read(str(project_file))

    plugin_instance.check_project()

    assert prj_manager.is_mzs_project is True
    assert prj_manager.project_updateable is False

    # get current project comune
    comune_data = prj_manager.get_project_comune_data()
    comune_name = prj_manager.sanitize_comune_name(comune_data.comune)
    exported_project_path = tmp_path / f"{comune_data.cod_istat}_{comune_name}_S42_Shapefile"
    mdb_path = exported_project_path / "Indagini"
    mdb_path.mkdir(parents=True)

    cdi_tabelle_path = DIR_PLUGIN_ROOT / "data" / "CdI_Tabelle_4.2.mdb"
    shutil.copy(cdi_tabelle_path, exported_project_path / "Indagini" / "CdI_Tabelle.mdb")

    task = ExportSitiPuntualiTask(exported_project_path, data_source="mdb")
    task.run()

    # TODO: verify exported mdb


def test_export_siti_puntuali_task_to_sqlite(
    plugin,
    qgis_iface,
    prj_manager,
    base_project_path_current_imported,
    tmp_path,
):
    plugin_instance = plugin(qgis_iface)

    project_file = base_project_path_current_imported / "progetto_MS.qgz"

    # Create a new project
    project = QgsProject.instance()

    # open the project
    project.read(str(project_file))

    plugin_instance.check_project()

    assert prj_manager.is_mzs_project is True
    assert prj_manager.project_updateable is False

    # get current project comune
    comune_data = prj_manager.get_project_comune_data()
    comune_name = prj_manager.sanitize_comune_name(comune_data.comune)
    exported_project_path = tmp_path / f"{comune_data.cod_istat}_{comune_name}_S42_Shapefile"
    db_path = exported_project_path / "Indagini"
    db_path.mkdir(parents=True)

    cdi_tabelle_path = DIR_PLUGIN_ROOT / "data" / "CdI_Tabelle.sqlite"
    shutil.copy(cdi_tabelle_path, exported_project_path / "Indagini" / "CdI_Tabelle.sqlite")

    task = ExportSitiPuntualiTask(exported_project_path, data_source="sqlite")
    task.run()

    # TODO: verify exported mdb


def test_export_siti_lineari_task_to_mdb(
    plugin,
    qgis_iface,
    prj_manager,
    base_project_path_current_imported,
    mdb_deps_available,
    tmp_path,
):
    # exit if mdb dependencies are not available
    if not mdb_deps_available:
        warnings.warn("MDB dependencies not available, skipping MDB import test", UserWarning)
        return

    plugin_instance = plugin(qgis_iface)

    project_file = base_project_path_current_imported / "progetto_MS.qgz"

    # Create a new project
    project = QgsProject.instance()

    # open the project
    project.read(str(project_file))

    plugin_instance.check_project()

    assert prj_manager.is_mzs_project is True
    assert prj_manager.project_updateable is False

    # get current project comune
    comune_data = prj_manager.get_project_comune_data()
    comune_name = prj_manager.sanitize_comune_name(comune_data.comune)
    exported_project_path = tmp_path / f"{comune_data.cod_istat}_{comune_name}_S42_Shapefile"
    mdb_path = exported_project_path / "Indagini"
    mdb_path.mkdir(parents=True)

    cdi_tabelle_path = DIR_PLUGIN_ROOT / "data" / "CdI_Tabelle_4.2.mdb"
    shutil.copy(cdi_tabelle_path, exported_project_path / "Indagini" / "CdI_Tabelle.mdb")

    task = ExportSitiLineariTask(exported_project_path, data_source="mdb")
    task.run()

    # TODO: verify exported mdb


def test_export_siti_lineari_task_to_sqlite(
    plugin,
    qgis_iface,
    prj_manager,
    base_project_path_current_imported,
    tmp_path,
):
    plugin_instance = plugin(qgis_iface)

    project_file = base_project_path_current_imported / "progetto_MS.qgz"

    # Create a new project
    project = QgsProject.instance()

    # open the project
    project.read(str(project_file))

    plugin_instance.check_project()

    assert prj_manager.is_mzs_project is True
    assert prj_manager.project_updateable is False

    # get current project comune
    comune_data = prj_manager.get_project_comune_data()
    comune_name = prj_manager.sanitize_comune_name(comune_data.comune)
    exported_project_path = tmp_path / f"{comune_data.cod_istat}_{comune_name}_S42_Shapefile"
    db_path = exported_project_path / "Indagini"
    db_path.mkdir(parents=True)

    cdi_tabelle_path = DIR_PLUGIN_ROOT / "data" / "CdI_Tabelle.sqlite"
    shutil.copy(cdi_tabelle_path, exported_project_path / "Indagini" / "CdI_Tabelle.sqlite")

    task = ExportSitiLineariTask(exported_project_path, data_source="sqlite")
    task.run()

    # TODO: verify exported mdb


def test_export_project_files_task(
    plugin,
    qgis_iface,
    prj_manager,
    base_project_path_current_imported,
    tmp_path,
):
    plugin_instance = plugin(qgis_iface)

    project_file = base_project_path_current_imported / "progetto_MS.qgz"

    # Create a new project
    project = QgsProject.instance()

    # open the project
    project.read(str(project_file))

    plugin_instance.check_project()

    assert prj_manager.is_mzs_project is True
    assert prj_manager.project_updateable is False

    # get current project comune
    comune_data = prj_manager.get_project_comune_data()
    comune_name = prj_manager.sanitize_comune_name(comune_data.comune)
    exported_project_path = tmp_path / f"{comune_data.cod_istat}_{comune_name}_S42_Shapefile"

    task = ExportProjectFilesTask(exported_project_path)
    task.run()

    indagini_docs_path = exported_project_path / "Indagini" / "Documenti"
    assert indagini_docs_path.exists()
    assert any(indagini_docs_path.iterdir())
    plot_path = exported_project_path / "Plot"
    assert plot_path.exists()
    spettri_path = exported_project_path / "MS23" / "Spettri"
    assert spettri_path.exists()
    assert any(spettri_path.iterdir())
