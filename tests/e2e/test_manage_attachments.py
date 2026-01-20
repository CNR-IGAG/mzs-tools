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

from unittest.mock import Mock

import pytest
from qgis.core import QgsProject

from mzs_tools.gui.dlg_manage_attachments import DlgManageAttachments
from mzs_tools.tasks.attachments_task import AttachmentsTask


@pytest.mark.display
def test_manage_attachments(
    plugin, qgis_app, qgis_iface, prj_manager, base_project_path_current_imported, monkeypatch, qtbot
):
    monkeypatch.setattr(qgis_iface, "messageBar", lambda: Mock(), raising=False)
    plugin_instance = plugin(qgis_iface)
    project_file = base_project_path_current_imported / "progetto_MS.qgz"

    # Open the project
    project = QgsProject.instance()
    project.read(str(project_file))
    plugin_instance.check_project()

    assert prj_manager.is_mzs_project is True
    assert prj_manager.project_updateable is False

    dialog = DlgManageAttachments()

    # Test without prepending IDs
    dialog.chk_prepend_ids.setChecked(False)

    with qtbot.waitSignal(qgis_app.taskManager().allTasksFinished, timeout=10000) as blocker:
        dialog.accept()
        # save task description for later checks
        task_description = dialog.manager.manage_attachments_task.description()
        # small delay to allow task to start
        qtbot.wait(100)
        while qgis_app.taskManager().countActiveTasks() > 0:
            qtbot.wait(100)

    assert dialog.manager.log_file_path.exists() is True
    log_text = dialog.manager.log_file_path.read_text(encoding="utf-8")

    assert f"Task {task_description} completed" in log_text

    # There are expected missing attachments in the test project
    assert "057001P238_057001P39.pdf for indagini_puntuali 057001P238DN287 does not exist!" in log_text
    assert "A2 for parametri_puntuali 057001P240HVSR289FR799 does not exist!" in log_text

    # Wait a second to ensure different timestamps for log files
    qtbot.wait(1000)

    # Run task again with prepending IDs option enabled
    dialog = DlgManageAttachments()
    dialog.chk_prepend_ids.setChecked(True)
    with qtbot.waitSignal(qgis_app.taskManager().allTasksFinished, timeout=10000) as blocker:
        dialog.accept()
        # save task description for later checks
        task_description = dialog.manager.manage_attachments_task.description()
        # small delay to allow task to start
        qtbot.wait(100)
        while qgis_app.taskManager().countActiveTasks() > 0:
            qtbot.wait(100)

    assert dialog.manager.log_file_path.exists() is True
    log_text = dialog.manager.log_file_path.read_text(encoding="utf-8")

    assert f"Task {task_description} completed" in log_text

    # There are cases of documents attached to multiple features in the test project;
    # to be able to prepend IDs, these files are copied for each feature
    assert "Attachment ./Allegati/Documenti/057001P81-P87.pdf copied to" in log_text
    assert (
        "Attachment path updated in the database to Allegati/Documenti/057001P82RGM129_057001P81-P87.pdf" in log_text
    )
    assert "Attachment ./Allegati/Documenti/057001P88-P90.pdf copied to" in log_text
    assert "Attachment path updated in the database to Allegati/Documenti/057001P89DS136_057001P88-P90.pdf" in log_text


def test_manage_attachments_task(plugin, qgis_iface, prj_manager, base_project_path_current_imported):
    """Test the task in isolation for coverage.
    Tasks are executed via the QGIS task manager and coverage.py does not track code executed
    in separate threads, so we run the task directly here.
    """
    plugin_instance = plugin(qgis_iface)
    project_file = base_project_path_current_imported / "progetto_MS.qgz"

    # Open the project
    project = QgsProject.instance()
    project.read(str(project_file))
    plugin_instance.check_project()

    task = AttachmentsTask(prepend_ids=False)
    task.run()

    # Without prepending IDs, the file should not exist
    assert (
        prj_manager.project_path / "Allegati" / "Documenti" / "057001P82RGM129_057001P81-P87.pdf"
    ).exists() is False

    # With prepending IDs, the file should be created
    task = AttachmentsTask(prepend_ids=True)
    task.run()

    assert (prj_manager.project_path / "Allegati" / "Documenti" / "057001P82RGM129_057001P81-P87.pdf").exists() is True
