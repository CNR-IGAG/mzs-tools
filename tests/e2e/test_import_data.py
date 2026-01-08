import warnings
from unittest.mock import Mock

import pytest
from qgis.core import QgsProject

from mzs_tools.__about__ import __base_version__
from mzs_tools.gui.dlg_import_data import DlgImportData
from mzs_tools.tasks.import_shapefile_task import ImportShapefileTask
from mzs_tools.tasks.import_siti_lineari_task import ImportSitiLineariTask
from mzs_tools.tasks.import_siti_puntuali_task import ImportSitiPuntualiTask


def test_import_data(
    plugin,
    qgis_app,
    qgis_iface,
    qgis_new_project,
    base_project_path_2_0_5,
    standard_project_path,
    mdb_deps_available,
    monkeypatch,
    qtbot,
):
    # Substitute MockMessageBar from pytest-qgis with a simple Mock as it seems to have
    # issues with our use of pushMessage
    # https://github.com/GispoCoding/pytest-qgis/blob/main/src/pytest_qgis/mock_qgis_classes.py
    monkeypatch.setattr(qgis_iface, "messageBar", lambda: Mock(), raising=False)
    plugin_instance = plugin(qgis_iface)

    project_file = base_project_path_2_0_5 / "progetto_MS.qgz"

    # Create a new project
    project = QgsProject.instance()

    # simulate already updated project by changing versione.txt
    versione_file = project_file.parent / "progetto" / "versione.txt"
    versione_file.write_text(__base_version__)

    # open the project
    project.read(str(project_file))

    plugin_instance.check_project()
    # plugin_instance.prj_manager.init_manager()

    assert plugin_instance.prj_manager.is_mzs_project is True
    assert plugin_instance.prj_manager.project_updateable is False

    # monkeypatch.setattr(DlgImportData, "on_tasks_completed", Mock(), raising=False)
    dialog = DlgImportData()

    # switch to passwordless MDB
    mdb_file = standard_project_path / "Indagini" / "CdI_Tabelle.mdb"
    mdb_file.rename(mdb_file.with_suffix(".mdb.bak"))
    (standard_project_path / "Indagini" / "CdI_Tabelle_no_pwd.mdb").rename(mdb_file)

    mdb_connected = dialog.check_mdb_connection(standard_project_path / "Indagini" / "CdI_Tabelle.mdb")
    result = dialog.check_project_dir(str(standard_project_path))

    # standard project should be importable even when mdb access is not available
    assert result is True

    dialog.input_dir_widget.lineEdit().setText(str(standard_project_path))

    # TODO: enabling MDB import tasks option seems to cause threading issues, with pytest hanging at the end:
    # QObject::killTimer: Timers cannot be stopped from another thread
    # QObject::~QObject: Timers cannot be stopped from another thread
    # if mdb_deps_available and mdb_connected:
    #     dialog.radio_button_mdb.setChecked(True)
    # else:
    #     warnings.warn("MDB dependencies not available, skipping MDB import option test", UserWarning)

    # https://pytest-qt.readthedocs.io/en/latest/signals.html
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

    # dialog.accept()
    # while qgis_app.taskManager().countActiveTasks() > 0:
    #     # qtbot.wait(1000)
    #     time.sleep(1)

    # dialog.task_manager.threadPool().waitForDone(100000)
    # qgis_app.taskManager().threadPool().clear()

    # # Poll until all tasks are complete (allTasksFinished signal is unreliable)
    # # Use qtbot.waitUntil which handles Qt event processing safely
    # qtbot.waitUntil(lambda: qgis_app.taskManager().countActiveTasks() == 0, timeout=100000)
    # warnings.warn(f"tasks: {qgis_app.taskManager().tasks()[0].status()}", UserWarning)
    # while qgis_app.taskManager().tasks()[0].status() != QgsTask.TaskStatus.Complete:
    #     # qtbot.wait(1000)
    #     time.sleep(1)
    # warnings.warn(f"tasks: {qgis_app.taskManager().tasks()[0].status()}", UserWarning)
    # qtbot.waitUntil(
    #     lambda: len(qgis_app.taskManager().tasks()) > 0
    #     and qgis_app.taskManager().tasks()[0].status() == QgsTask.TaskStatus.Complete,
    #     timeout=10000,
    # )

    log_text = dialog.log_file_path.read_text(encoding="utf-8")
    # Check for TESTING_MODE in log to ensure that the pytest-env environment variable was read
    assert "TESTING_MODE" in log_text
    assert dialog.tr("Data imported successfully") in log_text

    project.clear()


def test_import_siti_puntuali_task_from_mdb(
    plugin,
    qgis_iface,
    qgis_new_project,
    base_project_path_2_0_5,
    standard_project_path,
    mdb_deps_available,
):
    """Test ImportSitiPuntualiTask independently using mdb file as source.
    Tasks are executed via the QGIS task manager and coverage.py does not track code executed
    in separate threads, so we run the task directly here.
    """
    # exit if mdb dependencies are not available
    if not mdb_deps_available:
        warnings.warn("MDB dependencies not available, skipping MDB import test", UserWarning)
        return

    plugin_instance = plugin(qgis_iface)

    project_file = base_project_path_2_0_5 / "progetto_MS.qgz"
    project = QgsProject.instance()

    # simulate already updated project by changing versione.txt
    versione_file = project_file.parent / "progetto" / "versione.txt"
    versione_file.write_text(__base_version__)

    # switch to passwordless MDB
    mdb_file = standard_project_path / "Indagini" / "CdI_Tabelle.mdb"
    mdb_file.rename(mdb_file.with_suffix(".mdb.bak"))
    (standard_project_path / "Indagini" / "CdI_Tabelle_no_pwd.mdb").rename(mdb_file)

    # open the project
    project.read(str(project_file))
    plugin_instance.check_project()

    standard_proj_paths = {
        "CdI_Tabelle.mdb": {
            "parent": "Indagini",
            "path": standard_project_path / "Indagini" / "CdI_Tabelle.mdb",
            "checkbox": None,
        },
        "CdI_Tabelle.sqlite": {"parent": "Indagini", "path": None, "checkbox": None},
        "Ind_pu.shp": {
            "parent": "Indagini",
            "path": standard_project_path / "Indagini" / "Ind_pu.shp",
            "checkbox": None,
        },
        "Documenti": {
            "parent": "Indagini",
            "path": standard_project_path / "Indagini" / "Documenti",
            "checkbox": None,
        },
    }

    task = ImportSitiPuntualiTask(
        standard_proj_paths,
        data_source="mdb",
        mdb_password=None,
        csv_files=None,
    )
    task.run()

    # verify that features were imported - for some reason this won't work here...
    # dest_layer_id = plugin_instance.prj_manager.find_layer_by_table_name_role("sito_puntuale", "editing")
    # dest_layer = plugin_instance.prj_manager.current_project.mapLayer(dest_layer_id)
    # refresh layer to ensure feature count is updated
    # dest_layer.dataProvider().reloadData()
    # assert dest_layer.featureCount() > 0

    # verify imported features directly in the db
    result = plugin_instance.prj_manager.db_manager.get_row_count("sito_puntuale")
    assert result > 0

    result = plugin_instance.prj_manager.db_manager.get_row_count("indagini_puntuali")
    assert result > 0

    result = plugin_instance.prj_manager.db_manager.get_row_count("parametri_puntuali")
    assert result > 0

    result = plugin_instance.prj_manager.db_manager.get_row_count("curve")
    # no curve data in sample standard project
    assert result == 0

    project.clear()


def test_import_siti_puntuali_task_from_csv(
    plugin,
    qgis_iface,
    qgis_new_project,
    base_project_path_2_0_5,
    standard_project_path,
):
    """Test ImportSitiPuntualiTask independently using CSV files as source.
    Tasks are executed via the QGIS task manager and coverage.py does not track code executed
    in separate threads, so we run the task directly here.
    """
    plugin_instance = plugin(qgis_iface)

    project_file = base_project_path_2_0_5 / "progetto_MS.qgz"
    project = QgsProject.instance()

    # simulate already updated project by changing versione.txt
    versione_file = project_file.parent / "progetto" / "versione.txt"
    versione_file.write_text(__base_version__)

    # remove MDB
    mdb_file = standard_project_path / "Indagini" / "CdI_Tabelle.mdb"
    mdb_file.rename(mdb_file.with_suffix(".mdb.bak"))

    # open the project
    project.read(str(project_file))
    plugin_instance.check_project()

    standard_proj_paths = {
        "CdI_Tabelle.mdb": {
            "parent": "Indagini",
            "path": standard_project_path / "Indagini" / "CdI_Tabelle.mdb",
            "checkbox": None,
        },
        "CdI_Tabelle.sqlite": {"parent": "Indagini", "path": None, "checkbox": None},
        "Ind_pu.shp": {
            "parent": "Indagini",
            "path": standard_project_path / "Indagini" / "Ind_pu.shp",
            "checkbox": None,
        },
        "Documenti": {
            "parent": "Indagini",
            "path": standard_project_path / "Indagini" / "Documenti",
            "checkbox": None,
        },
    }

    found_files = {"puntuali": {}, "lineari": {}}
    found_files["puntuali"]["sito_puntuale"] = standard_project_path / "CSV" / "Sito_Puntuale.txt"
    found_files["puntuali"]["indagini_puntuali"] = standard_project_path / "CSV" / "Indagini_Puntuali.txt"
    found_files["puntuali"]["parametri_puntuali"] = standard_project_path / "CSV" / "Parametri_Puntuali.txt"
    found_files["puntuali"]["curve"] = standard_project_path / "CSV" / "Curve.txt"

    found_files["lineari"]["sito_lineare"] = standard_project_path / "CSV" / "Sito_Lineare.txt"
    found_files["lineari"]["indagini_lineari"] = standard_project_path / "CSV" / "Indagini_Lineari.txt"
    found_files["lineari"]["parametri_lineari"] = standard_project_path / "CSV" / "Parametri_Lineari.txt"

    task = ImportSitiPuntualiTask(
        standard_proj_paths,
        data_source="csv",
        mdb_password=None,
        csv_files=found_files,
    )
    task.run()

    # verify imported features directly in the db
    result = plugin_instance.prj_manager.db_manager.get_row_count("sito_puntuale")
    assert result > 0

    result = plugin_instance.prj_manager.db_manager.get_row_count("indagini_puntuali")
    assert result > 0

    result = plugin_instance.prj_manager.db_manager.get_row_count("parametri_puntuali")
    assert result > 0

    result = plugin_instance.prj_manager.db_manager.get_row_count("curve")
    # dummy curve data in csv
    assert result > 0

    project.clear()


def test_import_siti_puntuali_task_from_sqlite(
    plugin,
    qgis_iface,
    qgis_new_project,
    base_project_path_2_0_5,
    standard_project_path,
):
    """Test ImportSitiPuntualiTask independently using sqlite db as source.
    Tasks are executed via the QGIS task manager and coverage.py does not track code executed
    in separate threads, so we run the task directly here.
    """
    plugin_instance = plugin(qgis_iface)

    project_file = base_project_path_2_0_5 / "progetto_MS.qgz"
    project = QgsProject.instance()

    # simulate already updated project by changing versione.txt
    versione_file = project_file.parent / "progetto" / "versione.txt"
    versione_file.write_text(__base_version__)

    # remove MDB
    mdb_file = standard_project_path / "Indagini" / "CdI_Tabelle.mdb"
    mdb_file.rename(mdb_file.with_suffix(".mdb.bak"))

    # open the project
    project.read(str(project_file))
    plugin_instance.check_project()

    standard_proj_paths = {
        "CdI_Tabelle.mdb": {
            "parent": "Indagini",
            "path": standard_project_path / "Indagini" / "CdI_Tabelle.mdb",
            "checkbox": None,
        },
        "CdI_Tabelle.sqlite": {
            "parent": "Indagini",
            "path": standard_project_path / "Indagini" / "CdI_Tabelle.sqlite",
            "checkbox": None,
        },
        "Ind_pu.shp": {
            "parent": "Indagini",
            "path": standard_project_path / "Indagini" / "Ind_pu.shp",
            "checkbox": None,
        },
        "Documenti": {
            "parent": "Indagini",
            "path": standard_project_path / "Indagini" / "Documenti",
            "checkbox": None,
        },
    }

    task = ImportSitiPuntualiTask(
        standard_proj_paths,
        data_source="sqlite",
        mdb_password=None,
        csv_files=None,
    )
    task.run()

    # verify that features were imported - for some reason this won't work here...
    # dest_layer_id = plugin_instance.prj_manager.find_layer_by_table_name_role("sito_puntuale", "editing")
    # dest_layer = plugin_instance.prj_manager.current_project.mapLayer(dest_layer_id)
    # refresh layer to ensure feature count is updated
    # dest_layer.dataProvider().reloadData()
    # assert dest_layer.featureCount() > 0

    # verify imported features directly in the db
    result = plugin_instance.prj_manager.db_manager.get_row_count("sito_puntuale")
    assert result > 0

    result = plugin_instance.prj_manager.db_manager.get_row_count("indagini_puntuali")
    assert result > 0

    result = plugin_instance.prj_manager.db_manager.get_row_count("parametri_puntuali")
    assert result > 0

    result = plugin_instance.prj_manager.db_manager.get_row_count("curve")
    # no curve data in sample standard project
    assert result == 0

    project.clear()


def test_import_siti_lineari_task_from_mdb(
    plugin,
    qgis_iface,
    qgis_new_project,
    base_project_path_2_0_5,
    standard_project_path,
    mdb_deps_available,
):
    """Test ImportSitiLineariTask independently using mdb file as source.
    Tasks are executed via the QGIS task manager and coverage.py does not track code executed
    in separate threads, so we run the task directly here.
    """
    # exit if mdb dependencies are not available
    if not mdb_deps_available:
        warnings.warn("MDB dependencies not available, skipping MDB import test", UserWarning)
        return

    plugin_instance = plugin(qgis_iface)

    project_file = base_project_path_2_0_5 / "progetto_MS.qgz"
    project = QgsProject.instance()

    # simulate already updated project by changing versione.txt
    versione_file = project_file.parent / "progetto" / "versione.txt"
    versione_file.write_text(__base_version__)

    # switch to passwordless MDB
    mdb_file = standard_project_path / "Indagini" / "CdI_Tabelle.mdb"
    mdb_file.rename(mdb_file.with_suffix(".mdb.bak"))
    (standard_project_path / "Indagini" / "CdI_Tabelle_no_pwd.mdb").rename(mdb_file)

    # open the project
    project.read(str(project_file))
    plugin_instance.check_project()

    standard_proj_paths = {
        "CdI_Tabelle.mdb": {
            "parent": "Indagini",
            "path": standard_project_path / "Indagini" / "CdI_Tabelle.mdb",
            "checkbox": None,
        },
        "CdI_Tabelle.sqlite": {"parent": "Indagini", "path": None, "checkbox": None},
        "Ind_ln.shp": {
            "parent": "Indagini",
            "path": standard_project_path / "Indagini" / "Ind_ln.shp",
            "checkbox": None,
        },
        "Documenti": {
            "parent": "Indagini",
            "path": standard_project_path / "Indagini" / "Documenti",
            "checkbox": None,
        },
    }

    # task = ImportShapefileTask(standard_proj_paths, "Ind_pu.shp")
    # task.run()

    task = ImportSitiLineariTask(
        standard_proj_paths,
        data_source="mdb",
        mdb_password=None,
        csv_files=None,
    )
    task.run()

    # verify that features were imported - for some reason this won't work here...
    # dest_layer_id = plugin_instance.prj_manager.find_layer_by_table_name_role("sito_puntuale", "editing")
    # dest_layer = plugin_instance.prj_manager.current_project.mapLayer(dest_layer_id)
    # refresh layer to ensure feature count is updated
    # dest_layer.dataProvider().reloadData()
    # assert dest_layer.featureCount() > 0

    # verify imported features directly in the db
    result = plugin_instance.prj_manager.db_manager.get_row_count("sito_lineare")
    assert result > 0

    result = plugin_instance.prj_manager.db_manager.get_row_count("indagini_lineari")
    assert result > 0

    result = plugin_instance.prj_manager.db_manager.get_row_count("parametri_lineari")
    assert result > 0

    project.clear()


def test_import_siti_lineari_task_from_csv(
    plugin,
    qgis_iface,
    qgis_new_project,
    base_project_path_2_0_5,
    standard_project_path,
):
    """Test ImportSitiLineariTask independently using CSV files as source.
    Tasks are executed via the QGIS task manager and coverage.py does not track code executed
    in separate threads, so we run the task directly here.
    """
    plugin_instance = plugin(qgis_iface)

    project_file = base_project_path_2_0_5 / "progetto_MS.qgz"
    project = QgsProject.instance()

    # simulate already updated project by changing versione.txt
    versione_file = project_file.parent / "progetto" / "versione.txt"
    versione_file.write_text(__base_version__)

    # remove MDB
    mdb_file = standard_project_path / "Indagini" / "CdI_Tabelle.mdb"
    mdb_file.rename(mdb_file.with_suffix(".mdb.bak"))

    # open the project
    project.read(str(project_file))
    plugin_instance.check_project()

    standard_proj_paths = {
        "CdI_Tabelle.mdb": {
            "parent": "Indagini",
            "path": standard_project_path / "Indagini" / "CdI_Tabelle.mdb",
            "checkbox": None,
        },
        "CdI_Tabelle.sqlite": {"parent": "Indagini", "path": None, "checkbox": None},
        "Ind_ln.shp": {
            "parent": "Indagini",
            "path": standard_project_path / "Indagini" / "Ind_ln.shp",
            "checkbox": None,
        },
        "Documenti": {
            "parent": "Indagini",
            "path": standard_project_path / "Indagini" / "Documenti",
            "checkbox": None,
        },
    }

    found_files = {"puntuali": {}, "lineari": {}}
    found_files["puntuali"]["sito_puntuale"] = standard_project_path / "CSV" / "Sito_Puntuale.txt"
    found_files["puntuali"]["indagini_puntuali"] = standard_project_path / "CSV" / "Indagini_Puntuali.txt"
    found_files["puntuali"]["parametri_puntuali"] = standard_project_path / "CSV" / "Parametri_Puntuali.txt"
    found_files["puntuali"]["curve"] = standard_project_path / "CSV" / "Curve.txt"

    found_files["lineari"]["sito_lineare"] = standard_project_path / "CSV" / "Sito_Lineare.txt"
    found_files["lineari"]["indagini_lineari"] = standard_project_path / "CSV" / "Indagini_Lineari.txt"
    found_files["lineari"]["parametri_lineari"] = standard_project_path / "CSV" / "Parametri_Lineari.txt"

    task = ImportSitiLineariTask(
        standard_proj_paths,
        data_source="csv",
        mdb_password=None,
        csv_files=found_files,
    )
    task.run()

    # verify imported features directly in the db
    result = plugin_instance.prj_manager.db_manager.get_row_count("sito_lineare")
    assert result > 0

    result = plugin_instance.prj_manager.db_manager.get_row_count("indagini_lineari")
    assert result > 0

    result = plugin_instance.prj_manager.db_manager.get_row_count("parametri_lineari")
    assert result > 0

    project.clear()


def test_import_siti_lineari_task_from_sqlite(
    plugin,
    qgis_iface,
    qgis_new_project,
    base_project_path_2_0_5,
    standard_project_path,
):
    """Test ImportSitiLineariTask independently using sqlite db as source.
    Tasks are executed via the QGIS task manager and coverage.py does not track code executed
    in separate threads, so we run the task directly here.
    """
    plugin_instance = plugin(qgis_iface)

    project_file = base_project_path_2_0_5 / "progetto_MS.qgz"
    project = QgsProject.instance()

    # simulate already updated project by changing versione.txt
    versione_file = project_file.parent / "progetto" / "versione.txt"
    versione_file.write_text(__base_version__)

    # remove MDB
    mdb_file = standard_project_path / "Indagini" / "CdI_Tabelle.mdb"
    mdb_file.rename(mdb_file.with_suffix(".mdb.bak"))

    # open the project
    project.read(str(project_file))
    plugin_instance.check_project()

    standard_proj_paths = {
        "CdI_Tabelle.mdb": {
            "parent": "Indagini",
            "path": standard_project_path / "Indagini" / "CdI_Tabelle.mdb",
            "checkbox": None,
        },
        "CdI_Tabelle.sqlite": {
            "parent": "Indagini",
            "path": standard_project_path / "Indagini" / "CdI_Tabelle.sqlite",
            "checkbox": None,
        },
        "Ind_ln.shp": {
            "parent": "Indagini",
            "path": standard_project_path / "Indagini" / "Ind_ln.shp",
            "checkbox": None,
        },
        "Documenti": {
            "parent": "Indagini",
            "path": standard_project_path / "Indagini" / "Documenti",
            "checkbox": None,
        },
    }

    task = ImportSitiLineariTask(
        standard_proj_paths,
        data_source="sqlite",
        mdb_password=None,
        csv_files=None,
    )
    task.run()

    # verify that features were imported - for some reason this won't work here...
    # dest_layer_id = plugin_instance.prj_manager.find_layer_by_table_name_role("sito_puntuale", "editing")
    # dest_layer = plugin_instance.prj_manager.current_project.mapLayer(dest_layer_id)
    # refresh layer to ensure feature count is updated
    # dest_layer.dataProvider().reloadData()
    # assert dest_layer.featureCount() > 0

    # verify imported features directly in the db
    result = plugin_instance.prj_manager.db_manager.get_row_count("sito_lineare")
    assert result > 0

    result = plugin_instance.prj_manager.db_manager.get_row_count("indagini_lineari")
    assert result > 0

    result = plugin_instance.prj_manager.db_manager.get_row_count("parametri_lineari")
    assert result > 0

    project.clear()


@pytest.mark.skip("Not implemented yet")
def test_import_siti_puntuali_task_from_mdb_adapt_counters(
    plugin,
    qgis_iface,
    qgis_new_project,
    base_project_path_2_0_5,
    standard_project_path,
    mdb_deps_available,
):
    # insert a dummy site first and verify that counters are adapted
    pass


@pytest.mark.skip("Not implemented yet")
def test_import_siti_puntuali_task_from_mdb_cancelled_by_user(
    plugin,
    qgis_iface,
    qgis_new_project,
    base_project_path_2_0_5,
    standard_project_path,
    mdb_deps_available,
):
    # simulate user cancelling the task
    pass


@pytest.mark.skip("Not implemented yet")
def test_import_siti_puntuali_task_from_mdb_failure(
    plugin,
    qgis_iface,
    qgis_new_project,
    base_project_path_2_0_5,
    standard_project_path,
    mdb_deps_available,
):
    # simulate a failure during import
    pass


def test_import_shapefile_task(
    plugin,
    qgis_iface,
    qgis_new_project,
    base_project_path_2_0_5,
    standard_project_path,
):
    """Test ImportShapefileTask independently.
    Tasks are executed via the QGIS task manager and coverage.py does not track code executed
    in separate threads, so we run the task directly here.
    """
    # monkeypatch.setattr(QMessageBox, "exec", lambda: Mock(), raising=False)
    plugin_instance = plugin(qgis_iface)

    project_file = base_project_path_2_0_5 / "progetto_MS.qgz"
    project = QgsProject.instance()

    # simulate already updated project by changing versione.txt
    versione_file = project_file.parent / "progetto" / "versione.txt"
    versione_file.write_text(__base_version__)

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
    dest_layer_id = plugin_instance.prj_manager.find_layer_by_table_name_role("elineari", "editing")
    dest_layer = plugin_instance.prj_manager.current_project.mapLayer(dest_layer_id)
    assert dest_layer.featureCount() > 0

    project.clear()
