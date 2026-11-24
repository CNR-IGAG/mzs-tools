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

from qgis.core import QgsApplication, QgsProcessingProvider
from qgis.PyQt.QtGui import QIcon

from ..__about__ import DIR_PLUGIN_ROOT
from .algorithms import (
    ExportProjectsInFolderToStandardAlgorithm,
    ExportProjectToStandardAlgorithm,
    ImportStandardProjectAlgorithm,
    ImportStandardProjectsInFolderAlgorithm,
    UpdateProjectAlgorithm,
    UpdateProjectsInFolderAlgorithm,
)


class MzSToolsProvider(QgsProcessingProvider):
    def id(self):
        return "mzs_tools"

    def name(self):
        return "MzS Tools"

    def icon(self):
        return QIcon(str(DIR_PLUGIN_ROOT / "icon.png"))

    def loadAlgorithms(self):
        self.addAlgorithm(UpdateProjectAlgorithm())
        self.addAlgorithm(UpdateProjectsInFolderAlgorithm())
        self.addAlgorithm(ImportStandardProjectAlgorithm())
        self.addAlgorithm(ImportStandardProjectsInFolderAlgorithm())
        self.addAlgorithm(ExportProjectToStandardAlgorithm())
        self.addAlgorithm(ExportProjectsInFolderToStandardAlgorithm())


class MzSToolsProcessingPlugin:
    """Headless plugin object used by qgis_process (classFactory(None) followed by initProcessing())."""

    def __init__(self):
        self.provider = None

    def initProcessing(self):
        self.provider = MzSToolsProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

    def initGui(self):
        pass

    def unload(self):
        if self.provider:
            QgsApplication.processingRegistry().removeProvider(self.provider)
            self.provider = None
