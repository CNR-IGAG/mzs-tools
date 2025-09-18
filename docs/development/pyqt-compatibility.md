# PyQt5/PyQt6 Compatibility Implementation

The plugin features a PyQt5/PyQt6 compatibility implementation trying to make it work across different QGIS installations using either PyQt5 or PyQt6. The compatibility layer should be dropped when QGIS fully transitions to PyQt6.

## Overview

The PyQt5/PyQt6 compatibility layer detects the PyQt version at runtime and provides unified interfaces for PyQt-specific functionality.

## Some Differences Between PyQt5 and PyQt6

1. **QVariant changes**: In PyQt6, `QVariant` is deprecated and Python native types are used instead
2. **QMetaType changes**: API restructuring with nested enum access patterns
3. **Dialog result constants**: Moved from class attributes to enum values (`QDialog.Accepted` → `QDialog.DialogCode.Accepted`)
4. **Cursor shape constants**: Restructured into nested enums (`Qt.ArrowCursor` → `Qt.CursorShape.ArrowCursor`)
5. **Enum structure**: Proper Python enums in PyQt6 vs class attributes in PyQt5

## Compatibility Module Implementation

### Core Implementation

The main compatibility logic is implemented in `mzs_tools/plugin_utils/qt_compat.py`, which provides:

- **Runtime PyQt version detection**: Automatically detects whether PyQt5 or PyQt6 is being used
- **QVariant compatibility**: Handles the deprecation of `QVariant` in PyQt6
- **QMetaType compatibility**: Provides unified access to type constants
- **Dialog result constants**: Unified access to dialog result values
- **Cursor shape constants**: Handles enum structure changes in PyQt6

### Key Components

#### 1. Version Detection

```python
from mzs_tools.plugin_utils import IS_PYQT5, IS_PYQT6, get_qt_version_info

# Runtime detection
if IS_PYQT6:
    # PyQt6 specific code
else:
    # PyQt5 specific code

# Get detailed version info
info = get_qt_version_info()
```

#### 2. QVariant Compatibility

```python
from mzs_tools.plugin_utils import QVariant, qvariant_cast

# Use QVariant types consistently
field.setType(QVariant.Double)  # Works in both PyQt5 and PyQt6
field.setType(QVariant.String)  # Works in both PyQt5 and PyQt6

# Cast values safely
value = qvariant_cast(raw_value, QVariant.Double)
```

#### 3. QMetaType Compatibility

```python
from mzs_tools.plugin_utils import QMetaTypeWrapper as QMetaType

# Use QMetaType consistently
field.setType(QMetaType.Double)   # Works in both versions
field.setType(QMetaType.QString)  # Works in both versions
```

#### 4. Dialog Result Constants

```python
from mzs_tools.plugin_utils import DIALOG_ACCEPTED, DIALOG_REJECTED

# Check dialog results consistently
if dialog.result() == DIALOG_ACCEPTED:
    # Handle accepted dialog
elif dialog.result() == DIALOG_REJECTED:
    # Handle rejected dialog
```

#### 5. Enhanced Enum Handling

```python
from mzs_tools.plugin_utils import enum_value, get_dialog_result

# Generic enum value access
value = enum_value(SomeEnum, "ValueName")

# Specific dialog result handling
accepted = get_dialog_result(QDialog, "Accepted")  # Works in both PyQt5/6
```

## Usage Patterns

### Field Type Setting

```python
from mzs_tools.plugin_utils import QMetaTypeWrapper as QMetaType

# Create a field with double type
field = QgsField()
field.setName("value_field")
field.setType(QMetaType.Double)  # Works in both PyQt5/6
```

### Value Handling

```python
from mzs_tools.plugin_utils import QVariant, qvariant_cast

# Safe value extraction
def extract_value(qvariant_value):
    if qvariant_value is None:
        return None
    elif isinstance(qvariant_value, QVariant):
        if qvariant_value.isNull():
            return None
        else:
            return qvariant_value.value()
    else:
        return qvariant_value
```

### Type Checking

```python
from mzs_tools.plugin_utils import QVariant

# Check field types consistently
if field.type() == QVariant.Double:
    # Handle double field
elif field.type() == QVariant.String:
    # Handle string field
```

## Maintenance

When adding new PyQt-dependent code:

1. **Import from toolbelt**: Use compatibility imports instead of direct PyQt imports
2. **Check compatibility module**: Add new compatibility patterns if needed
3. **Test both versions**: Ensure new code works with both PyQt5 and PyQt6
4. **Update documentation**: Document any new compatibility patterns
