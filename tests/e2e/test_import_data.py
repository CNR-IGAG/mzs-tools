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

from pathlib import Path
from unittest.mock import Mock

import pytest
from qgis.core import Qgis, QgsProject

from mzs_tools.gui.dlg_import_data import DlgImportData
from mzs_tools.tasks.import_shapefile_task import ImportShapefileTask
from mzs_tools.tasks.import_siti_lineari_task import ImportSitiLineariTask
from mzs_tools.tasks.import_siti_puntuali_task import ImportSitiPuntualiTask


def _log_has(path: Path | None, text: str) -> bool:
    return path is not None and path.exists() and text in path.read_text(encoding="utf-8")


def test_import_data(
    plugin,
    qgis_iface,
    prj_manager,
    base_project_path_current,
    standard_project_path,
    mdb_deps_available,
    monkeypatch,
    wait_tasks_done,
):
    # Substitute MockMessageBar from pytest-qgis with a simple Mock as it seems to have
    # issues with our use of pushMessage: https://github.com/osgeosuomi/pytest-qgis/issues/26
    # https://github.com/GispoCoding/pytest-qgis/blob/main/src/pytest_qgis/mock_qgis_classes.py
    monkeypatch.setattr(qgis_iface, "messageBar", lambda: Mock(), raising=False)
    plugin_instance = plugin(qgis_iface)

    project_file = base_project_path_current / "progetto_MS.qgz"

    # Create a new project
    project = QgsProject.instance()

    # open the project
    project.read(str(project_file))

    plugin_instance.check_project()
    # plugin_instance.prj_manager.init_manager()

    assert prj_manager.is_mzs_project is True
    assert prj_manager.project_updateable is False

    # monkeypatch.setattr(DlgImportData, "on_tasks_completed", Mock(), raising=False)
    dialog = DlgImportData()

    # switch to passwordless MDB
    mdb_file = standard_project_path / "Indagini" / "CdI_Tabelle.mdb"
    mdb_file.rename(mdb_file.with_suffix(".mdb.bak"))
    (standard_project_path / "Indagini" / "CdI_Tabelle_no_pwd.mdb").rename(mdb_file)

    # mdb_connected = dialog.check_mdb_connection(standard_project_path / "Indagini" / "CdI_Tabelle.mdb")
    dialog.check_mdb_connection(standard_project_path / "Indagini" / "CdI_Tabelle.mdb")
    result = dialog.check_project_dir(str(standard_project_path))

    # standard project should be importable even when mdb access is not available
    assert result is True

    dialog.input_dir_widget.lineEdit().setText(str(standard_project_path))

    # TODO: import/export from/to mdb using QGIS task manager causes threading issues in tests, with pytest hanging at the end:
    # QObject::killTimer: Timers cannot be stopped from another thread
    # QObject::~QObject: Timers cannot be stopped from another thread
    # if mdb_deps_available and mdb_connected:
    #     dialog.radio_button_mdb.setChecked(True)
    # else:
    #     warnings.warn("MDB dependencies not available, skipping MDB import option test", UserWarning)

    # enable sqlite import option, siti puntuali and lineari checkboxes are automatically selected
    dialog.radio_button_sqlite.setChecked(True)

    # accept() will run start_import_tasks
    dialog.accept()
    log_path = dialog.import_data_task_manager.log_file_path
    wait_tasks_done(lambda: _log_has(log_path, "Data imported") or _log_has(log_path, "Data import completed"))

    log_text = log_path.read_text(encoding="utf-8")
    assert dialog.import_data_task_manager.tr("Data imported successfully") in log_text


@pytest.mark.parametrize("source", ["mdb", "csv", "sqlite"])
@pytest.mark.parametrize("kind", ["puntuali", "lineari"])
def test_import_siti_task(
    kind,
    source,
    plugin,
    qgis_iface,
    prj_manager,
    base_project_path_current,
    standard_project_path,
    mdb_deps_available,
):
    """Test ImportSitiPuntualiTask / ImportSitiLineariTask independently, for each data source.

    Tasks are executed via the QGIS task manager and coverage.py does not track code executed
    in separate threads, so we run the task directly here.
    """
    if source == "mdb" and not mdb_deps_available:
        pytest.skip("MDB dependencies (Java, JayDeBeApi) not available")

    plugin_instance = plugin(qgis_iface)

    project_file = base_project_path_current / "progetto_MS.qgz"
    project = QgsProject.instance()

    indagini_dir = standard_project_path / "Indagini"

    # remove the password protected MDB, and switch to the passwordless one for the mdb source
    mdb_file = indagini_dir / "CdI_Tabelle.mdb"
    mdb_file.rename(mdb_file.with_suffix(".mdb.bak"))
    if source == "mdb":
        (indagini_dir / "CdI_Tabelle_no_pwd.mdb").rename(mdb_file)

    # open the project
    project.read(str(project_file))
    plugin_instance.check_project()

    shapefile_name = "Ind_pu.shp" if kind == "puntuali" else "Ind_ln.shp"
    standard_proj_paths = {
        "CdI_Tabelle.mdb": {
            "parent": "Indagini",
            "path": indagini_dir / "CdI_Tabelle.mdb",
            "checkbox": None,
        },
        "CdI_Tabelle.sqlite": {
            "parent": "Indagini",
            "path": indagini_dir / "CdI_Tabelle.sqlite" if source == "sqlite" else None,
            "checkbox": None,
        },
        shapefile_name: {
            "parent": "Indagini",
            "path": indagini_dir / shapefile_name,
            "checkbox": None,
        },
        "Documenti": {
            "parent": "Indagini",
            "path": indagini_dir / "Documenti",
            "checkbox": None,
        },
    }

    csv_files = None
    if source == "csv":
        csv_dir = standard_project_path / "CSV"
        csv_files = {"puntuali": {}, "lineari": {}}
        csv_files["puntuali"]["sito_puntuale"] = csv_dir / "Sito_Puntuale.txt"
        csv_files["puntuali"]["indagini_puntuali"] = csv_dir / "Indagini_Puntuali.txt"
        csv_files["puntuali"]["parametri_puntuali"] = csv_dir / "Parametri_Puntuali.txt"
        csv_files["puntuali"]["curve"] = csv_dir / "Curve.txt"

        csv_files["lineari"]["sito_lineare"] = csv_dir / "Sito_Lineare.txt"
        csv_files["lineari"]["indagini_lineari"] = csv_dir / "Indagini_Lineari.txt"
        csv_files["lineari"]["parametri_lineari"] = csv_dir / "Parametri_Lineari.txt"

    task_class = ImportSitiPuntualiTask if kind == "puntuali" else ImportSitiLineariTask
    task = task_class(
        standard_proj_paths,
        data_source=source,
        mdb_password=None,
        csv_files=csv_files,
    )
    task.run()

    # verify imported features directly in the db
    if kind == "puntuali":
        tables = ["sito_puntuale", "indagini_puntuali", "parametri_puntuali"]
    else:
        tables = ["sito_lineare", "indagini_lineari", "parametri_lineari"]
    for table in tables:
        assert prj_manager.db_manager.get_row_count(table) > 0, f"no rows imported in {table}"

    if kind == "puntuali":
        curve_count = prj_manager.db_manager.get_row_count("curve")
        if source == "csv":
            # dummy curve data in csv
            assert curve_count > 0
        else:
            # no curve data in sample standard project
            assert curve_count == 0


def _load_project_and_check(plugin_instance, prj_manager, base_project_path):
    """Helper: open the sample project and verify it is a valid MzS project."""
    project = QgsProject.instance()
    project.read(str(base_project_path / "progetto_MS.qgz"))
    plugin_instance.check_project()
    assert prj_manager.is_mzs_project is True
    assert prj_manager.project_updateable is False


def test_import_siti_puntuali_task_from_mdb_cancelled_by_user(
    plugin,
    qgis_app,
    qgis_iface,
    prj_manager,
    base_project_path_current,
    standard_project_path,
    monkeypatch,
    qtbot,
):
    """cancel_tasks() stops the import and pushes a Warning to the message bar.

    All task run() methods are monkeypatched to return True immediately so the
    test is deterministic and avoids side-effects from the real import logic.
    """
    mock_bar = Mock()
    monkeypatch.setattr(qgis_iface, "messageBar", lambda: mock_bar, raising=False)
    # Patch all tasks so run() returns True instantly (no real import, no exceptions)
    monkeypatch.setattr(ImportSitiPuntualiTask, "run", lambda self: True)
    monkeypatch.setattr(ImportSitiLineariTask, "run", lambda self: True)
    monkeypatch.setattr(ImportShapefileTask, "run", lambda self: True)

    plugin_instance = plugin(qgis_iface)
    _load_project_and_check(plugin_instance, prj_manager, base_project_path_current)

    dialog = DlgImportData()
    qtbot.addWidget(dialog)
    # Switch to passwordless MDB to avoid a blocking password dialog during check_project_dir
    mdb_file = standard_project_path / "Indagini" / "CdI_Tabelle.mdb"
    mdb_file.rename(mdb_file.with_suffix(".mdb.bak"))
    (standard_project_path / "Indagini" / "CdI_Tabelle_no_pwd.mdb").rename(mdb_file)
    dialog.check_project_dir(str(standard_project_path))
    dialog.input_dir_widget.lineEdit().setText(str(standard_project_path))
    dialog.radio_button_sqlite.setChecked(True)

    with qtbot.waitSignal(qgis_app.taskManager().allTasksFinished, timeout=15000):
        dialog.accept()
        # Cancel immediately after accept() - import_data_task_manager is already set
        dialog.import_data_task_manager.cancel_tasks()
        while qgis_app.taskManager().countActiveTasks() > 0:
            qtbot.wait(500)

    assert dialog.import_data_task_manager is not None
    # cancel_tasks() always pushes a Warning regardless of task state
    call_levels = [c.kwargs.get("level") for c in mock_bar.pushMessage.call_args_list]
    assert Qgis.MessageLevel.Warning in call_levels


def test_import_siti_puntuali_task_from_mdb_failure(
    plugin,
    qgis_app,
    qgis_iface,
    prj_manager,
    base_project_path_current,
    standard_project_path,
    monkeypatch,
    qtbot,
):
    """When ImportSitiPuntualiTask.run returns False the manager records task_failed=True.

    Returning False without setting self.exception is the "cancelled" path: finished()
    logs a warning but does not re-raise, so no exception propagates into Qt's event
    loop and there is no risk of a SIGSEGV.
    Shapefile and siti-lineari tasks are patched to succeed so that the only failure
    is the one we deliberately inject.
    """
    monkeypatch.setattr(qgis_iface, "messageBar", lambda: Mock(), raising=False)
    # Patch shapefile and sln tasks so they do not fail on their own
    monkeypatch.setattr(ImportShapefileTask, "run", lambda self: True)
    monkeypatch.setattr(ImportSitiLineariTask, "run", lambda self: True)
    # Patch spu to fail (returns False, no exception → finished() path is safe)
    monkeypatch.setattr(ImportSitiPuntualiTask, "run", lambda self: False)

    plugin_instance = plugin(qgis_iface)
    _load_project_and_check(plugin_instance, prj_manager, base_project_path_current)

    dialog = DlgImportData()
    qtbot.addWidget(dialog)
    # Switch to passwordless MDB to avoid a blocking password dialog during check_project_dir
    mdb_file = standard_project_path / "Indagini" / "CdI_Tabelle.mdb"
    mdb_file.rename(mdb_file.with_suffix(".mdb.bak"))
    (standard_project_path / "Indagini" / "CdI_Tabelle_no_pwd.mdb").rename(mdb_file)
    dialog.check_project_dir(str(standard_project_path))
    dialog.input_dir_widget.lineEdit().setText(str(standard_project_path))
    dialog.radio_button_sqlite.setChecked(True)

    with qtbot.waitSignal(qgis_app.taskManager().allTasksFinished, timeout=15000):
        dialog.accept()
        qtbot.wait(500)
        while qgis_app.taskManager().countActiveTasks() > 0:
            qtbot.wait(500)

    assert dialog.import_data_task_manager is not None
    assert dialog.import_data_task_manager.task_failed is True


def test_import_shapefile_task(
    plugin,
    qgis_iface,
    prj_manager,
    base_project_path_current,
    standard_project_path,
):
    """Test ImportShapefileTask independently.
    Tasks are executed via the QGIS task manager and coverage.py does not track code executed
    in separate threads, so we run the task directly here.
    """
    # monkeypatch.setattr(QMessageBox, "exec", lambda: Mock(), raising=False)
    plugin_instance = plugin(qgis_iface)

    project_file = base_project_path_current / "progetto_MS.qgz"
    project = QgsProject.instance()

    # open the project
    project.read(str(project_file))
    plugin_instance.check_project()

    standard_proj_paths = {
        "Elineari.shp": {
            "parent": "GeoTec",
            "path": standard_project_path / "GeoTec" / "Elineari.shp",
            "checkbox": None,
            "table": "elineari",
        },
    }

    task = ImportShapefileTask(standard_proj_paths, "Elineari.shp")
    task.run()

    # verify that features were imported
    dest_layer_id = prj_manager.find_layer_by_table_name_role("elineari", "editing")
    dest_layer = prj_manager.current_project.mapLayer(dest_layer_id)
    assert dest_layer.featureCount() > 0
