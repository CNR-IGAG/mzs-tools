import zipfile
from pathlib import Path

from qgis.core import QgsProject

from mzs_tools.__about__ import __base_version__
from mzs_tools.gui.dlg_import_data import DlgImportData, DlgMdbPassword


def test_import_data_check_project_dir(
    plugin, qgis_app, qgis_iface, qgis_new_project, prj_manager, tmp_path, monkeypatch
):
    plugin_instance = plugin(qgis_iface)

    # Extract the project from zip archive in tests/data directory
    project_archive = Path(__file__).parent.parent / "data" / "mzs_projects" / "057001_Accumoli_v2.0.5_new.zip"
    with zipfile.ZipFile(project_archive, "r") as zip_ref:
        zip_ref.extractall(tmp_path)

    project_file = tmp_path / "057001_Accumoli" / "progetto_MS.qgz"

    # Create a new project
    project = QgsProject.instance()

    # simulate already updated project by changing versione.txt
    versione_file = project_file.parent / "progetto" / "versione.txt"
    versione_file.write_text(__base_version__)

    # open the project
    project.read(str(project_file))

    plugin_instance.check_project()

    assert plugin_instance.prj_manager.is_mzs_project is True
    assert plugin_instance.prj_manager.project_updateable is False

    dialog = DlgImportData()

    # extract the standard project
    project_archive = Path(__file__).parent.parent / "data" / "standard_projects" / "Accumoli.zip"
    with zipfile.ZipFile(project_archive, "r") as zip_ref:
        zip_ref.extractall(tmp_path)

    # monkeypatch DlgMdbPassword.exec() to avoid blocking dialog
    monkeypatch.setattr(DlgMdbPassword, "exec", lambda self: None, raising=False)

    result = dialog.check_project_dir(str(tmp_path / "Accumoli"))

    # standard project should be importable
    assert result is True

    project.clear()
