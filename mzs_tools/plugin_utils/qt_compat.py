#! python3  # noqa: E265

"""PyQt5/PyQt6 compatibility module.

This module provides a unified interface for PyQt5 and PyQt6 compatibility,
handling the main differences between the two versions.
"""

from typing import Any, Union

try:
    # Try to determine PyQt version through QGIS
    from qgis.PyQt.QtCore import QT_VERSION_STR

    # Parse version to determine if it's PyQt5 or PyQt6
    qt_major_version = int(QT_VERSION_STR.split(".")[0])
    IS_PYQT6 = qt_major_version >= 6
    IS_PYQT5 = qt_major_version < 6

except ImportError:
    # Fallback: try to detect PyQt version directly
    try:
        import PyQt6  # noqa: F401

        IS_PYQT6 = True
        IS_PYQT5 = False
    except ImportError:
        try:
            import PyQt5  # noqa: F401

            IS_PYQT6 = False
            IS_PYQT5 = True
        except ImportError:
            # Default to PyQt5 if we can't detect
            IS_PYQT6 = False
            IS_PYQT5 = True


def get_qt_version_info() -> dict:
    """Get Qt version information.

    Returns:
        Dictionary with Qt version information
    """
    try:
        from qgis.PyQt.QtCore import PYQT_VERSION_STR, QT_VERSION_STR  # noqa: E402

        return {
            "qt_version": QT_VERSION_STR,
            "pyqt_version": PYQT_VERSION_STR,
            "is_pyqt5": IS_PYQT5,
            "is_pyqt6": IS_PYQT6,
        }
    except ImportError:
        return {
            "qt_version": "unknown",
            "pyqt_version": "unknown",
            "is_pyqt5": IS_PYQT5,
            "is_pyqt6": IS_PYQT6,
        }


# QVariant compatibility
if IS_PYQT6:
    # In PyQt6, QVariant is deprecated and Python types are used directly
    from qgis.PyQt.QtCore import QMetaType  # noqa: E402

    class QVariantCompat:
        """QVariant compatibility class for PyQt6."""

        # Type constants for PyQt6 using QMetaType
        Invalid = QMetaType.Type.UnknownType
        Bool = QMetaType.Type.Bool
        Int = QMetaType.Type.Int
        UInt = QMetaType.Type.UInt
        LongLong = QMetaType.Type.LongLong
        ULongLong = QMetaType.Type.ULongLong
        Double = QMetaType.Type.Double
        String = QMetaType.Type.QString
        Date = QMetaType.Type.QDate
        Time = QMetaType.Type.QTime
        DateTime = QMetaType.Type.QDateTime
        ByteArray = QMetaType.Type.QByteArray

        @staticmethod
        def typeToName(type_val: Union[int, Any]) -> str:
            """Convert type to string name."""
            if hasattr(QMetaType, "typeName"):
                result = QMetaType.typeName(type_val)
                return result if result is not None else str(type_val)
            return str(type_val)

        @staticmethod
        def nameToType(name: str) -> Union[int, Any]:
            """Convert string name to type."""
            if hasattr(QMetaType, "type"):
                return QMetaType.type(name)
            # Fallback mappings
            type_map = {
                "bool": QMetaType.Type.Bool,
                "int": QMetaType.Type.Int,
                "double": QMetaType.Type.Double,
                "QString": QMetaType.Type.QString,
                "QDate": QMetaType.Type.QDate,
                "QTime": QMetaType.Type.QTime,
                "QDateTime": QMetaType.Type.QDateTime,
                "QByteArray": QMetaType.Type.QByteArray,
            }
            return type_map.get(name, QMetaType.Type.UnknownType)

    QVariant = QVariantCompat

    def qvariant_cast(value: Any, target_type: Any) -> Any:
        """Cast value to target type (PyQt6 compatible)."""
        # In PyQt6, we work with native Python types
        if target_type == QVariant.Bool:
            return bool(value) if value is not None else False
        elif target_type == QVariant.Int:
            return int(value) if value is not None else 0
        elif target_type == QVariant.Double:
            return float(value) if value is not None else 0.0
        elif target_type == QVariant.String:
            return str(value) if value is not None else ""
        else:
            return value

else:
    # PyQt5: use QVariant directly
    from qgis.PyQt.QtCore import QVariant  # noqa: E402

    # Create alias for consistency
    QVariantCompat = QVariant

    def qvariant_cast(value: Any, target_type: Any) -> Any:
        """Cast value to target type (PyQt5 compatible)."""
        if hasattr(value, "value"):
            # It's already a QVariant
            return value.value()
        return value


# QMetaType compatibility
if IS_PYQT6:
    from qgis.PyQt.QtCore import QMetaType  # noqa: E402

    class QMetaTypeCompat:
        """QMetaType compatibility for PyQt6."""

        # Common type constants
        UnknownType = QMetaType.Type.UnknownType
        Bool = QMetaType.Type.Bool
        Int = QMetaType.Type.Int
        UInt = QMetaType.Type.UInt
        Double = QMetaType.Type.Double
        QString = QMetaType.Type.QString
        QDate = QMetaType.Type.QDate
        QTime = QMetaType.Type.QTime
        QDateTime = QMetaType.Type.QDateTime

        @staticmethod
        def type(type_name: str) -> Union[int, Any]:
            """Get type ID from name."""
            return QMetaType.fromName(type_name.encode()).id()

        @staticmethod
        def typeName(type_id: Union[int, Any]) -> str:
            """Get type name from ID."""
            meta_type = QMetaType(type_id)
            return meta_type.name().decode() if meta_type.isValid() else ""

    QMetaTypeWrapper = QMetaTypeCompat

else:
    # PyQt5: use QMetaType directly
    from qgis.PyQt.QtCore import QMetaType as QMetaTypeWrapper  # noqa: E402

    # Create alias for consistency
    QMetaTypeCompat = QMetaTypeWrapper


# Enum compatibility
def enum_value(enum_class: Any, value_name: str) -> Any:
    """Get enum value in a compatible way across PyQt versions.

    Args:
        enum_class: The enum class
        value_name: The name of the enum value

    Returns:
        The enum value
    """
    if IS_PYQT6:
        # In PyQt6, enums are proper Python enums
        # First try direct access
        if hasattr(enum_class, value_name):
            return getattr(enum_class, value_name)
        # Then try nested enums (e.g., QDialog.DialogCode.Accepted)
        for attr_name in dir(enum_class):
            attr = getattr(enum_class, attr_name)
            if hasattr(attr, "__class__") and "enum" in str(type(attr)).lower():
                if hasattr(attr, value_name):
                    return getattr(attr, value_name)
    else:
        # In PyQt5, enums are class attributes
        if hasattr(enum_class, value_name):
            return getattr(enum_class, value_name)

    raise AttributeError(f"Enum value '{value_name}' not found in {enum_class}")


def get_dialog_result(dialog_class: Any, result_name: str) -> int:
    """Get dialog result value in a compatible way.

    Args:
        dialog_class: The dialog class (e.g., QDialog)
        result_name: The result name ('Accepted' or 'Rejected')

    Returns:
        The dialog result value
    """
    if IS_PYQT6:
        # In PyQt6: QDialog.DialogCode.Accepted
        if hasattr(dialog_class, "DialogCode"):
            dialog_code = getattr(dialog_class, "DialogCode")
            if hasattr(dialog_code, result_name):
                return getattr(dialog_code, result_name)
    else:
        # In PyQt5: QDialog.Accepted
        if hasattr(dialog_class, result_name):
            return getattr(dialog_class, result_name)

    # Fallback to standard values
    if result_name == "Accepted":
        return 1
    elif result_name == "Rejected":
        return 0
    else:
        raise ValueError(f"Unknown dialog result: {result_name}")


def signal_connect(signal: Any, slot: Any) -> None:
    """Connect signal to slot in a compatible way.

    Args:
        signal: The signal to connect
        slot: The slot to connect to
    """
    # Both PyQt5 and PyQt6 use the same new-style signal connection
    signal.connect(slot)


def signal_disconnect(signal: Any, slot: Any = None) -> None:
    """Disconnect signal from slot in a compatible way.

    Args:
        signal: The signal to disconnect
        slot: The slot to disconnect from (None to disconnect all)
    """
    if slot is None:
        signal.disconnect()
    else:
        signal.disconnect(slot)


def get_cursor_shape(cursor_name: str) -> Any:
    """Get cursor shape constant in a compatible way.

    Args:
        cursor_name: The cursor name (e.g., 'ArrowCursor', 'CrossCursor', 'PointingHandCursor')

    Returns:
        The cursor constant value
    """
    try:
        from qgis.PyQt.QtCore import Qt  # noqa: E402

        if IS_PYQT6:
            # In PyQt6: Qt.CursorShape.ArrowCursor
            if hasattr(Qt, "CursorShape"):
                cursor_shape = getattr(Qt, "CursorShape")
                if hasattr(cursor_shape, cursor_name):
                    return getattr(cursor_shape, cursor_name)
        else:
            # In PyQt5: Qt.ArrowCursor
            if hasattr(Qt, cursor_name):
                return getattr(Qt, cursor_name)

        # Fallback mappings for common cursors
        fallback_values = {
            "ArrowCursor": 0,
            "CrossCursor": 2,
            "PointingHandCursor": 13,
            "WaitCursor": 3,
        }
        return fallback_values.get(cursor_name, 0)  # Default to arrow

    except ImportError:
        # Ultimate fallback
        return 0


def get_selection_behavior(behavior_name: str) -> Any:
    """Get selection behavior constant in a compatible way.

    Args:
        behavior_name: The selection behavior name (e.g., 'SelectRows', 'SelectColumns', 'SelectItems')

    Returns:
        The selection behavior constant value
    """
    try:
        from qgis.PyQt.QtWidgets import QAbstractItemView  # noqa: E402

        if IS_PYQT6:
            # In PyQt6: QAbstractItemView.SelectionBehavior.SelectRows
            if hasattr(QAbstractItemView, "SelectionBehavior"):
                selection_behavior = getattr(QAbstractItemView, "SelectionBehavior")
                if hasattr(selection_behavior, behavior_name):
                    return getattr(selection_behavior, behavior_name)
        else:
            # In PyQt5: QAbstractItemView.SelectRows
            if hasattr(QAbstractItemView, behavior_name):
                return getattr(QAbstractItemView, behavior_name)

        # Fallback mappings for common selection behaviors
        fallback_values = {
            "SelectItems": 0,
            "SelectRows": 1,
            "SelectColumns": 2,
        }
        return fallback_values.get(behavior_name, 0)  # Default to SelectItems

    except ImportError:
        # Ultimate fallback
        return 0


# Export commonly used compatibility items
__all__ = [
    "IS_PYQT5",
    "IS_PYQT6",
    "QVariantCompat",
    "QVariant",
    "QMetaTypeCompat",
    "QMetaType",
    "qvariant_cast",
    "enum_value",
    "get_dialog_result",
    "get_cursor_shape",
    "get_selection_behavior",
    "signal_connect",
    "signal_disconnect",
    "get_qt_version_info",
]  # Dialog result constants for convenience
try:
    from qgis.PyQt.QtWidgets import QDialog  # noqa: E402

    if IS_PYQT6:
        # In PyQt6, enum values are accessed through the enum type
        DIALOG_ACCEPTED = QDialog.DialogCode.Accepted
        DIALOG_REJECTED = QDialog.DialogCode.Rejected
    else:
        # In PyQt5, enum values are class attributes
        DIALOG_ACCEPTED = QDialog.Accepted
        DIALOG_REJECTED = QDialog.Rejected

    __all__.extend(["DIALOG_ACCEPTED", "DIALOG_REJECTED"])
except ImportError:
    # Fallback to standard values
    DIALOG_ACCEPTED = 1
    DIALOG_REJECTED = 0
    __all__.extend(["DIALOG_ACCEPTED", "DIALOG_REJECTED"])
