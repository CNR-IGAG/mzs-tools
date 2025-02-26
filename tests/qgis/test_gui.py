import os
from unittest.mock import MagicMock, patch

from qgis.PyQt.QtCore import Qt, QTimer
from qgis.PyQt.QtWidgets import QCompleter, QDialog

from ..__about__ import __version__
from ..gui.dlg_info import PluginInfo
from ..gui.dlg_create_project import DlgCreateProject


def test_tb_info(qgis_app):
    """Test PluginInfo dialog."""
    dialog = PluginInfo()
    assert dialog is not None
    assert dialog.markdown_available is not None
    assert dialog.label_info is not None
    assert dialog.label_license is not None
    assert dialog.label_credits is not None
    assert dialog.label_changelog is not None
    assert dialog.button_manual is not None
    assert dialog.button_github is not None
    assert dialog.buttonBox is not None

    if dialog.markdown_available:
        assert dialog.label_credits.textFormat() == 3
        assert dialog.label_changelog.textFormat() == 3

    dialog.show()

    assert dialog.label_version.text() == f"Version {__version__}"

    QTimer.singleShot(2000, qgis_app.closeAllWindows)
    qgis_app.exec_()


def test_tb_nuovo_progetto_gui(qgis_app):
    dialog = DlgCreateProject()
    assert dialog is not None

    dialog.show()

    # Get completer from comuneField
    completer = dialog.comuneField.completer()
    completer.setCompletionPrefix("rom")

    # Manually show completion popup
    completer.complete()

    # Get completion model
    model = completer.completionModel()
    assert model.rowCount() > 0

    # Verify "Roma" is in completions
    found = False
    for i in range(model.rowCount()):
        if "Roma" in model.data(model.index(i, 0)):
            found = True
            # Simulate selection of completion
            completer.activated.emit(model.data(model.index(i, 0)))
            break
    assert found

    # simulate selection from completer
    dialog.comuneField.setText("Roma (Roma - Lazio)")
    dialog.update_cod_istat()
    cod_istat = dialog.cod_istat.text()
    assert cod_istat == "058091"

    dialog.professionista.setText("Mario Rossi")
    dialog.email_prof.setText("asdf@qwer.com")
    dialog.output_dir_widget.lineEdit().setText("/tmp")

    # ok button should be enabled when all fields are filled
    assert dialog.ok_button.isEnabled() is True

    # all fields are required
    dialog.email_prof.setText("")
    assert dialog.ok_button.isEnabled() is False

    QTimer.singleShot(2000, dialog.reject)

    qgis_app.exec_()

    qgis_app.closeAllWindows()


def test_tb_nuovo_progetto_comune_completer():
    dialog = DlgCreateProject()

    # Test completer setup
    completer = dialog.comuneField.completer()
    assert isinstance(completer, QCompleter)
    assert completer.caseSensitivity() == Qt.CaseInsensitive

    # Test completion model
    model = completer.model()
    assert model.rowCount() > 0

    # Test completion matching
    dialog.comuneField.setText("rom")
    completer.setCompletionPrefix("rom")
    completion_model = completer.completionModel()
    assert completion_model.rowCount() > 0
    assert "Roma (Roma - Lazio)" in [
        completion_model.data(completion_model.index(i, 0)) for i in range(completion_model.rowCount())
    ]
    assert "Monopoli (Bari - Puglia)" not in [
        completion_model.data(completion_model.index(i, 0)) for i in range(completion_model.rowCount())
    ]

    dialog.comuneField.setText("monopoli")
    completer.setCompletionPrefix("monopoli")
    completion_model = completer.completionModel()
    assert completion_model.rowCount() == 1
    assert "Monopoli (Bari - Puglia)" in [
        completion_model.data(completion_model.index(i, 0)) for i in range(completion_model.rowCount())
    ]
    assert completer.currentCompletion() == "Monopoli (Bari - Puglia)"

    dialog.close()


def test_tb_nuovo_progetto_dialog_reject():
    dialog = DlgCreateProject()

    # Mock create_project method
    dialog.create_project = MagicMock()

    # Test dialog rejection
    with patch.object(QDialog, "exec_", return_value=False):
        dialog.run_new_project_tool(False)
        dialog.create_project.assert_not_called()
    dialog.close()


def test_create_project():
    dialog = DlgCreateProject()

    # Setup test data
    test_dir = "/tmp/test_project"
    comune = "Test Comune (TE - Test)"
    cod_istat = "123456"
    professionista = "Test Prof"
    email = "test@email.com"

    # Set dialog fields
    dialog.comuneField.setText(comune)
    dialog.cod_istat.setText(cod_istat)
    dialog.professionista.setText(professionista)
    dialog.email_prof.setText(email)

    # Mock dependencies
    project_mock = MagicMock()
    layout_mock = MagicMock()
    layout_manager_mock = MagicMock()
    layout_manager_mock.printLayouts.return_value = [layout_mock]
    project_mock.layoutManager.return_value = layout_manager_mock

    with (
        patch("qgis.core.QgsProject.instance", return_value=project_mock),
        # patch.object(dialog, "extract_project_template"),
        patch.object(dialog, "customize_project"),
        patch("mzs_tools.gui.dlg_create_project.create_basic_sm_metadata"),
        patch("qgis.PyQt.QtWidgets.QMessageBox.information"),
        patch("os.rename"),
        patch("os.path.join", side_effect=os.path.join),
    ):
        # Execute
        result = dialog.create_project(test_dir)

        # Verify
        expected_path = os.path.join(test_dir, f"{cod_istat}_Test_Comune", "progetto_MS.qgs")
        assert result == expected_path

        # Verify method calls
        # dialog.extract_project_template.assert_called_once_with(test_dir)
        dialog.customize_project.assert_called_once()
        project_mock.read.assert_called_once()
        project_mock.write.assert_called_once()
        layout_mock.refresh.assert_called_once()

    dialog.close()


def test_sanitize_comune_name():
    """Test comune name sanitization"""
    dialog = DlgCreateProject()
    assert dialog.sanitize_comune_name("Roma (RM - Lazio)") == "Roma"
    assert dialog.sanitize_comune_name("Sant'Angelo (LE)") == "Sant_Angelo"
    assert dialog.sanitize_comune_name("Città Sant'Angelo") == "Città_Sant_Angelo"


# @pytest.fixture
# def new_project_dialog():
#     dialog = NewProject()
#     dialog.comuneField.setText("Test Comune (TE - Test)")
#     dialog.cod_istat.setText("123456")
#     dialog.professionista.setText("Test Prof")
#     dialog.email_prof.setText("test@email.com")
#     dialog.dir_output.setText("/tmp/test_project")
#     return dialog


# def test_extract_project_template(new_project_dialog):
#     """Test project template extraction"""
#     with patch("zipfile.ZipFile") as mock_zip:
#         new_project_dialog.extract_project_template("/tmp/test")
#         mock_zip.assert_called_once()
#         mock_zip().__enter__().extractall.assert_called_once_with("/tmp/test")


# def test_customize_project(new_project_dialog, tmp_path):
#     """Test project customization"""
#     project_mock = MagicMock()
#     layer_mock = MagicMock()
#     feature_mock = MagicMock()
#     comune_layer_mock = MagicMock()
#     canvas_mock = MagicMock()
#     provider_mock = MagicMock()
#     extent = QgsRectangle(0, 0, 100, 100)

#     # Mock feature attributes
#     attrs = ["id", "12345", "code", "other", "TestComune", "data", "TE", "Test"]
#     feature_mock.attributes.return_value = attrs

#     # Mock layer operations
#     layer_mock.getFeatures.return_value = [feature_mock]
#     layer_mock.selectedFeatures.return_value = [feature_mock]
#     comune_layer_mock.getFeatures.return_value = [feature_mock]

#     # Mock provider and extent operations
#     provider_mock.extent.return_value = extent
#     provider_mock.addFeatures.return_value = (True, [feature_mock])
#     comune_layer_mock.dataProvider.return_value = provider_mock
#     canvas_mock.extent.return_value = extent

#     # Mock layout operations
#     layout_manager_mock = MagicMock()
#     layout_mock = MagicMock()
#     map_item_mock = MagicMock()
#     layout_mock.itemById.side_effect = lambda x: map_item_mock
#     layout_manager_mock.printLayouts.return_value = [layout_mock]
#     project_mock.layoutManager.return_value = layout_manager_mock
#     project_mock.homePath.return_value = str(tmp_path)

#     # Setup project layers
#     project_mock.mapLayersByName.side_effect = [[layer_mock], [comune_layer_mock]]

#     with (
#         patch("qgis.utils.iface") as mock_iface,
#         patch("os.path.exists", return_value=True),
#         patch("shutil.copyfile") as mock_copyfile,
#         patch("mzs_tools.tb_nuovo_progetto.save_map_image") as mock_save_image,
#     ):
#         # Setup iface mock with canvas
#         mock_iface.mapCanvas.return_value = canvas_mock

#         test_dir = tmp_path / "test_project"
#         test_dir.mkdir()
#         (test_dir / "progetto" / "loghi").mkdir(parents=True)

#         new_project_dialog.customize_project(project_mock, "12345", str(test_dir))

#         # Verify extent operations sequence
#         provider_mock.extent.assert_called_once()
#         # canvas_mock.setExtent.assert_called_once_with(extent)
#         # canvas_mock.refresh.assert_called()
#         # map_item_mock.zoomToExtent.assert_called_with(extent)
