import os
import sqlite3
import time
from functools import wraps
from pathlib import Path
from subprocess import PIPE, STDOUT, Popen
from typing import Optional

from qgis.core import (
    QgsApplication,
    QgsMapRendererCustomPainterJob,
    QgsMapSettings,
)
from qgis.PyQt.QtCore import QCoreApplication, QSize, Qt
from qgis.PyQt.QtGui import QImage, QPainter
from qgis.PyQt.QtWidgets import QLabel, QMessageBox, QProgressDialog
from qgis.utils import iface

from ..plugin_utils.logging import MzSToolsLogger


def require_mzs_project(func):
    """Decorator to check if an MzS Tools project is opened before executing the action.

    If no MzS project is opened, logs a warning message and returns without executing the function.
    Qt5/Qt6 compatibility: accepts signal arguments but doesn't forward them since
    decorated functions are typically action handlers that don't need them.
    """

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if not self.prj_manager.is_mzs_project:
            msg = QCoreApplication.translate("MzSTools", "The tool must be used within an opened MS project!")
            self.log(msg, log_level=1)
            return
        # Call function without signal arguments for Qt5/Qt6 compatibility
        return func(self)

    return wrapper


def skip_file_not_found(func):
    """Decorator to catch FileNotFoundError exceptions."""

    @wraps(func)
    def _wrapper(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except FileNotFoundError as e:
            MzSToolsLogger.log(f"File not found: {e}", log_level=1)

    return _wrapper


def retry_on_lock(retries=5, delay=1):
    """Decorator to retry a database operation if the database is locked."""

    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(retries):
                try:
                    return func(*args, **kwargs)
                except sqlite3.OperationalError as e:
                    if "database is locked" in str(e):
                        args[0].log(f"Database is locked, retrying in {delay} seconds...", log_level=1)
                        time.sleep(delay)
                    else:
                        raise
            raise sqlite3.OperationalError("Database is locked after multiple retries")

        return wrapper

    return decorator


def save_map_image(image_path, zoom_to_layer, canvas, width=1280, height=1024):
    """Creates and saves a PNG image of the map canvas
    zoomed to the `zoom_to_layer` layer's extent.

    :param image_path: destination file path for the image
    :type image_path: str
    :param zoom_to_layer: vector layer for the map extent
    :type zoom_to_layer: QgsVectorLayer
    :param canvas: map canvas
    :type canvas: QgsMapCanvas
    :param width: image width in pixels (default: 1280)
    :type width: int
    :param height: image height in pixels (default: 1024)
    :type height: int
    """
    # Validate inputs
    if not zoom_to_layer or not zoom_to_layer.isValid():
        MzSToolsLogger.log("Error: zoom_to_layer is invalid", log_level=1)
        return

    # Get the extent from the layer
    extent = zoom_to_layer.extent()
    if extent.isEmpty():
        MzSToolsLogger.log("Error: zoom_to_layer extent is empty", log_level=1)
        return

    # Get canvas layers
    canvas_layers = canvas.layers()
    if not canvas_layers:
        MzSToolsLogger.log("Warning: no layers visible in canvas, attempting direct layer rendering", log_level=1)
        # If canvas has no layers, create a minimal layer set with just the zoom layer
        canvas_layers = [zoom_to_layer]

    MzSToolsLogger.log(f"Creating map image: {width}x{height} pixels, extent: {extent}")
    MzSToolsLogger.log(
        f"Using {len(canvas_layers)} canvas layers: {[layer.name() for layer in canvas_layers]}", log_level=4
    )

    # Create map settings
    settings = QgsMapSettings()
    settings.setLayers(canvas_layers)  # Use canvas layers to maintain visibility and order
    settings.setExtent(extent)
    settings.setOutputSize(QSize(width, height))
    settings.setDestinationCrs(zoom_to_layer.crs())

    # Create image
    image = QImage(QSize(width, height), QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(0)  # Transparent background

    # Create painter and render
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Create and run the rendering job
    render_job = QgsMapRendererCustomPainterJob(settings, painter)
    render_job.start()
    render_job.waitForFinished()

    painter.end()

    # Save the image
    success = image.save(image_path, "PNG")
    if success:
        MzSToolsLogger.log(f"Map image saved to {image_path} ({width}x{height} pixels)")
    else:
        MzSToolsLogger.log(f"Failed to save map image to {image_path}", log_level=1)


def save_map_image_from_canvas(image_path, zoom_to_layer, canvas, width=1280, height=1024):
    """Creates and saves a PNG image using the map canvas directly.
    This is an alternative approach that preserves the current canvas styling.

    :param image_path: destination file path for the image
    :type image_path: str
    :param zoom_to_layer: vector layer for the map extent
    :type zoom_to_layer: QgsVectorLayer
    :param canvas: map canvas
    :type canvas: QgsMapCanvas
    :param width: image width in pixels (default: 1280)
    :type width: int
    :param height: image height in pixels (default: 1024)
    :type height: int
    """
    # Store current canvas state
    original_extent = canvas.extent()
    original_size = canvas.size()

    try:
        # Set the canvas to the desired extent and size
        extent = zoom_to_layer.extent()
        canvas.setExtent(extent)
        canvas.resize(width, height)
        canvas.refresh()

        # Capture the canvas as an image
        pixmap = canvas.grab()
        pixmap.save(image_path, "PNG")

        MzSToolsLogger.log(f"Map image saved to {image_path} ({width}x{height} pixels)")

    finally:
        # Restore original canvas state
        canvas.setExtent(original_extent)
        canvas.resize(original_size)
        canvas.refresh()


def save_map_image_direct(image_path, layers, extent, crs, width=1280, height=1024):
    """Creates and saves a PNG image directly from specified layers and extent.
    This approach doesn't rely on the canvas and is more reliable for programmatic use.

    :param image_path: destination file path for the image
    :type image_path: str
    :param layers: list of layers to render
    :type layers: list[QgsMapLayer]
    :param extent: map extent to render
    :type extent: QgsRectangle
    :param crs: coordinate reference system
    :type crs: QgsCoordinateReferenceSystem
    :param width: image width in pixels (default: 1280)
    :type width: int
    :param height: image height in pixels (default: 1024)
    :type height: int
    """
    if not layers:
        MzSToolsLogger.log("Error: no layers provided for rendering", log_level=1)
        return

    if extent.isEmpty():
        MzSToolsLogger.log("Error: extent is empty", log_level=1)
        return

    MzSToolsLogger.log(f"Creating map image directly: {width}x{height} pixels")
    MzSToolsLogger.log(f"Using {len(layers)} layers: {[layer.name() for layer in layers]}", log_level=4)
    MzSToolsLogger.log(f"Extent: {extent}", log_level=4)

    # Create map settings
    settings = QgsMapSettings()
    settings.setLayers(layers)
    settings.setExtent(extent)
    settings.setOutputSize(QSize(width, height))
    settings.setDestinationCrs(crs)

    # Create image
    image = QImage(QSize(width, height), QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(0)  # Transparent background

    # Create painter and render
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Create and run the rendering job
    render_job = QgsMapRendererCustomPainterJob(settings, painter)
    render_job.start()
    render_job.waitForFinished()

    painter.end()

    # Save the image
    success = image.save(image_path, "PNG")
    if success:
        MzSToolsLogger.log(f"Map image saved to {image_path} ({width}x{height} pixels)")
    else:
        MzSToolsLogger.log(f"Failed to save map image to {image_path}", log_level=1)


def get_subdir_path(root_dir_path, subdir_name):
    """case insensitive recursive search for a subdirectory in the provided path"""
    subdir_name = subdir_name.lower()
    for root, dirs, _ in Path(root_dir_path).walk():
        for d in dirs:
            if d.lower() == subdir_name:
                return root / d
    return None


def get_file_path(root_dir_path, file_name):
    """case insensitive recursive search for a file in the provided path"""
    file_name = file_name.lower()
    for root, _, files in Path(root_dir_path).walk():
        for file in files:
            if file.lower() == file_name:
                return root / file
    return None


def get_path_for_name(root_dir_path, name):
    """case insensitive recursive search for a file or subdirectory in the provided path"""
    name = name.lower()
    # MzSToolsLogger.log(f"Searching for {name} in {root_dir_path}", log_level=4)
    for root, dirs, files in Path(root_dir_path).walk():
        for f in files:
            if f.lower() == name:
                return root / f
        for d in dirs:
            if d.lower() == name:
                return root / d
    return None


def run_cmd(args, description="running a system command"):
    """Run a system command from QGIS and show a progress dialog with real-time output.
    Adapted and improved from https://github.com/opengisch/qpip/blob/main/a00_qpip/utils.py

    :param args: command and arguments as a list
    :type args: list[str]
    :param description: description for the progress dialog
    :type description: str
    :return: True if the command succeeded, False otherwise
    :rtype: bool
    """
    parent = iface.mainWindow()  # type: ignore
    progress_dlg = QProgressDialog(description, "Abort", 0, 0, parent=parent)
    progress_dlg.setWindowTitle("Please wait...")
    progress_dlg.setFixedWidth(500)
    progress_dlg.setMaximumHeight(500)
    label = QLabel(description)
    label.setMargin(5)
    label.setWordWrap(True)
    progress_dlg.setLabel(label)
    progress_dlg.setWindowModality(Qt.WindowModality.WindowModal)
    progress_dlg.show()

    startupinfo = None
    if os.name == "nt":
        from subprocess import (
            STARTF_USESHOWWINDOW,
            STARTF_USESTDHANDLES,
            STARTUPINFO,
            SW_HIDE,
        )

        startupinfo = STARTUPINFO()
        startupinfo.dwFlags |= STARTF_USESTDHANDLES | STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = SW_HIDE

    process = Popen(args, stdout=PIPE, stderr=STDOUT, startupinfo=startupinfo, universal_newlines=True, bufsize=1)

    full_output = ""
    while True:
        QgsApplication.processEvents()

        # Check if process has finished
        if process.poll() is not None:
            # Read any remaining output
            remaining_output = process.stdout.read()
            if remaining_output:
                full_output += remaining_output
                # Split by lines and update progress dialog with last line
                lines = remaining_output.strip().split("\n")
                for line in lines:
                    if line.strip():
                        progress_dlg.setLabelText(line.strip())
                        MzSToolsLogger.log("COMMAND OUTPUT: " + line.strip(), log_level=4)
            break

        # Read output line by line
        try:
            # Use readline with a small timeout simulation by checking if data is available
            import select

            if hasattr(select, "select"):  # Unix-like systems
                ready, _, _ = select.select([process.stdout], [], [], 0.1)
                if ready:
                    line = process.stdout.readline()
                    if line:
                        output = line.strip()
                        full_output += line
                        if output:
                            progress_dlg.setLabelText(output)
                            MzSToolsLogger.log("COMMAND OUTPUT: " + output, log_level=4)
            else:  # Windows fallback
                # On Windows, just try to read with a timeout
                line = process.stdout.readline()
                if line:
                    output = line.strip()
                    full_output += line
                    if output:
                        progress_dlg.setLabelText(output)
                        MzSToolsLogger.log("COMMAND OUTPUT: " + output, log_level=4)

        except Exception:
            # If reading fails, just continue
            pass

        if progress_dlg.wasCanceled():
            process.kill()
            break

    progress_dlg.close()

    if process.returncode != 0:
        MzSToolsLogger.log("Command failed.", log_level=2)
        message = QMessageBox(
            QMessageBox.Icon.Critical,
            "Command failed",
            f"Encountered an error while {description}!",
            parent=parent,
        )
        message.setDetailedText(full_output)
        message.exec()
        return False
    else:
        MzSToolsLogger.log("Command succeeded.", log_level=3, push=True, duration=5)
        return True


def find_libjvm(java_home: str, max_depth: int = 4, save_to_settings: bool = True) -> Optional[str]:
    """
    Recursively search for libjvm.so (Linux), libjvm.dylib (macOS), or jvm.dll (Windows)
    in the provided Java home directory.

    Args:
        java_home: Path to Java JRE installation directory
        max_depth: Maximum depth for recursive search (default: 4)
        save_to_settings: If True, save the java_home path to plugin settings when libjvm is found (default: True)

    Returns:
        Full path to libjvm file if found, None otherwise
    """
    if not java_home or not java_home.strip():
        return None

    java_home_path = Path(java_home)
    if not java_home_path.exists() or not java_home_path.is_dir():
        return None

    # Determine the library name based on platform
    import platform

    system = platform.system()
    if system == "Linux":
        lib_names = ["libjvm.so"]
    elif system == "Darwin":  # macOS
        lib_names = ["libjvm.dylib"]
    elif system == "Windows":
        lib_names = ["jvm.dll"]
    else:
        lib_names = ["libjvm.so", "libjvm.dylib", "jvm.dll"]

    # Search for the library file with depth limit
    for lib_name in lib_names:
        for lib_path in java_home_path.rglob(lib_name):
            # Calculate depth relative to java_home_path
            try:
                relative_path = lib_path.relative_to(java_home_path)
                depth = len(relative_path.parents)
                if depth <= max_depth and lib_path.is_file():
                    # Save the directory containing the found library to settings if requested
                    if save_to_settings:
                        from ..plugin_utils.settings import PlgOptionsManager

                        lib_dir = str(lib_path.parent)
                        plg_settings = PlgOptionsManager()
                        current_settings = plg_settings.get_plg_settings()
                        # Only update if different from current value
                        if current_settings.java_home_path != lib_dir:
                            MzSToolsLogger.log(
                                f"Updating java_home_path setting to: {lib_dir}", log_level=3, push=True, duration=5
                            )
                            plg_settings.set_value_from_key("java_home_path", lib_dir)

                    return str(lib_path)
            except ValueError:
                # Skip if path is not relative to java_home_path
                continue

    return None
