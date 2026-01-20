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

from configparser import ConfigParser
from datetime import date
from pathlib import Path

from packaging.version import parse

# used during development to speed up some processes (i.e destructive data deletion)
# set to False before releasing!
DEBUG_MODE: bool = False

DIR_PLUGIN_ROOT: Path = Path(__file__).parent
PLG_METADATA_FILE: Path = DIR_PLUGIN_ROOT.resolve() / "metadata.txt"


def plugin_metadata_as_dict() -> dict:
    """Read plugin metadata.txt and returns it as a Python dict.

    Raises:
        IOError: if metadata.txt is not found

    Returns:
        dict: dict of dicts.
    """
    config = ConfigParser()
    if PLG_METADATA_FILE.is_file():
        config.read(PLG_METADATA_FILE.resolve(), encoding="UTF-8")
        return {s: dict(config.items(s)) for s in config.sections()}
    else:
        raise OSError(f"Plugin metadata.txt not found at: {PLG_METADATA_FILE}")


__plugin_md__: dict = plugin_metadata_as_dict()

__author__: str = __plugin_md__.get("general").get("author")
__copyright__: str = f"2018 - {date.today().year}, {__author__}"
__email__: str = __plugin_md__.get("general").get("email")
__icon_path__: Path = DIR_PLUGIN_ROOT.resolve() / __plugin_md__.get("general").get("icon")
__keywords__: list = [t.strip() for t in __plugin_md__.get("general").get("repository").split("tags")]
__license__: str = "GPLv3"
__summary__: str = "{}\n\n{}".format(
    __plugin_md__.get("general").get("description"),
    __plugin_md__.get("general").get("about"),
)
__summary_it__: str = "{}\n\n{}".format(
    __plugin_md__.get("general").get("description[it]"),
    __plugin_md__.get("general").get("about[it]"),
)

__title__: str = __plugin_md__.get("general").get("name")
__title_clean__: str = "".join(e for e in __title__ if e.isalnum())

__uri_homepage__: str = __plugin_md__.get("general").get("homepage")
__uri_docs__: str = "https://cnr-igag.github.io/mzs-tools/"
__uri_repository__: str = __plugin_md__.get("general").get("repository")
__uri_tracker__: str = __plugin_md__.get("general").get("tracker")
__uri__: str = __uri_repository__

__version__: str = __plugin_md__.get("general").get("version")
__base_version__: str = parse(__version__).base_version
__version_info__: tuple = tuple(
    [int(num) if num.isdigit() else num for num in __version__.replace("-", ".", 1).split(".")]
)

if __name__ == "__main__":
    plugin_md = plugin_metadata_as_dict()
    assert isinstance(plugin_md, dict)
    assert plugin_md.get("general").get("name") == __title__
    print(f"Plugin: {__title__}")
    print(f"By: {__author__}")
    print(f"Version: {__version__}")
    print(f"Description: {__summary__}")
    print(f"Icon: {__icon_path__}")
    print(
        "For: {} > QGIS > {}".format(
            plugin_md.get("general").get("qgisminimumversion"),
            plugin_md.get("general").get("qgismaximumversion"),
        )
    )
    print(__title_clean__)
