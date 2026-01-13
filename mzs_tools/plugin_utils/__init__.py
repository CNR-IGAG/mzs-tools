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

from .logging import MzSToolsLogger  # noqa: F401
from .qt_compat import (  # noqa: F401
    DIALOG_ACCEPTED,
    DIALOG_REJECTED,
    IS_PYQT5,
    IS_PYQT6,
    QMetaTypeWrapper,
    QVariant,
    enum_value,
    get_cursor_shape,
    get_dialog_result,
    get_qt_version_info,
    get_selection_behavior,
    qvariant_cast,
    signal_connect,
    signal_disconnect,
)
from .settings import PlgOptionsManager  # noqa: F401
