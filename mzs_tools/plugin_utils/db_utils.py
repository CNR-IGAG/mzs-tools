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

from ..plugin_utils.logging import MzSToolsLogger
from ..tasks.access_db_connection import AccessDbConnection, JVMError


def check_mdb_connection(mdb_path):
    """Test connection to an Access database."""
    connected = False
    mdb_conn = None
    deps_ok = True
    jvm_ok = True

    try:
        mdb_conn = AccessDbConnection(mdb_path)
        connected = mdb_conn.open()

    except ImportError as e:
        error_msg = f"{e}. Python dependencies missing."
        MzSToolsLogger.log(error_msg, log_level=1)
        deps_ok = False

    except JVMError as e:
        MzSToolsLogger.log(f"{e}", log_level=1)
        jvm_ok = False

    except Exception as e:
        MzSToolsLogger.log(f"{e}", log_level=2)

    finally:
        if mdb_conn and connected:
            mdb_conn.close()

    result = {
        "connected": connected,
        "deps_ok": deps_ok,
        "jvm_ok": jvm_ok,
    }

    return result
