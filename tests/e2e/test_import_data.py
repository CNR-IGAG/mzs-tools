from qgis.core import QgsProject

from mzs_tools.__about__ import __base_version__
from mzs_tools.gui.dlg_import_data import DlgImportData, DlgMdbPassword


def test_import_data(
    plugin, qgis_app, qgis_iface, qgis_new_project, base_project_path, standard_project_path, tmp_path, monkeypatch
):
    plugin_instance = plugin(qgis_iface)

    project_file = base_project_path / "progetto_MS.qgz"

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

    # monkeypatch DlgMdbPassword.exec() to avoid blocking dialog
    monkeypatch.setattr(DlgMdbPassword, "exec", lambda self: None, raising=False)

    result = dialog.check_project_dir(str(standard_project_path))

    # standard project should be importable
    assert result is True

    project.clear()
