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

"""Forward the logs of the MzS Tools tasks to a log file and to the processing feedback."""

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from qgis.core import QgsProcessingFeedback


class FeedbackLogHandler(logging.Handler):
    """Forward the log records to the processing feedback."""

    def __init__(self, feedback: QgsProcessingFeedback):
        super().__init__()
        self.feedback = feedback

    def emit(self, record: logging.LogRecord) -> None:
        msg = self.format(record)
        if record.levelno >= logging.ERROR:
            self.feedback.reportError(msg, fatalError=False)
        elif record.levelno >= logging.WARNING:
            self.feedback.pushWarning(msg)
        else:
            self.feedback.pushInfo(msg)


@contextmanager
def feedback_file_log(
    logger_name: str, log_file: Path, feedback: QgsProcessingFeedback, header: list[str]
) -> Iterator[Path]:
    """Log the records of logger_name to log_file and to the processing feedback, at INFO level.

    The header lines are logged first. The handlers and the logger level are restored on exit.
    """
    logger = logging.getLogger(logger_name)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    feedback_handler = FeedbackLogHandler(feedback)
    old_level = logger.level

    logger.addHandler(file_handler)
    logger.addHandler(feedback_handler)
    logger.setLevel(logging.INFO)
    try:
        for line in header:
            logger.info(line)
        yield log_file
    finally:
        for handler in (file_handler, feedback_handler):
            logger.removeHandler(handler)
            handler.close()
        logger.setLevel(old_level)
