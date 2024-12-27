from functools import wraps

from mzs_tools.plugin_utils.logging import MzSToolsLogger


def skip_file_not_found(func):
    """Decorator to catch FileNotFoundError exceptions."""

    @wraps(func)
    def _wrapper(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except FileNotFoundError as e:
            MzSToolsLogger.log(f"File not found: {e}", log_level=1)

    return _wrapper
