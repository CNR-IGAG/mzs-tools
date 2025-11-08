# Database Operations Quick Reference

Quick guide for using the new `DatabaseManager` in MzS Tools.

## Basic Setup

```python
from mzs_tools.core.db_manager import DatabaseManager

# Initialize
db_manager = DatabaseManager(db_path, logger=self)

# Connect
db_manager.connect()

# Use as context manager (auto-connect/disconnect)
with DatabaseManager(db_path, logger=self) as db_manager:
    results = db_manager.execute_query("SELECT * FROM table")
```

## Using a `@property` to wrap access to the db manager

For classes that manage a database connection (like `MzSProjectManager`), always use a property instead of accessing `DatabaseManager` directly:

**Example of the property implementation:**

```python
@property
def db(self) -> DatabaseManager:
    """Get database manager with validation."""
    if not self.db_manager:
        self.log("Database manager not initialized", log_level=2)
        raise RuntimeError("Database manager not initialized")
    if not self.db_manager.is_connected():
        self.log("Database is not connected", log_level=2)
        raise RuntimeError("Database is not connected")
    return self.db_manager
```

Usage:

```python
# ✅ Correct - Use the property
row = self.db.execute_query("SELECT * FROM table", fetch_mode="one")

# ❌ Wrong - Don't access directly
row = self.db_manager.execute_query("SELECT * FROM table", fetch_mode="one")
```

### Why Use the Property?

The `db` property provides automatic validation:

1. **Checks if DatabaseManager is initialized** - Ensures `db_manager` exists
2. **Checks if connection is active** - Ensures `is_connected()` returns True
3. **Raises clear exceptions** - Fails fast with `RuntimeError` if checks fail
4. **Works for external code** - Other modules accessing `prj_manager.db` get the same validation

### External Module Usage

External modules (like dialog classes) also benefit from the property:

```python
# In dlg_metadata_edit.py or similar

# ✅ Correct - Property validates automatically
try:
    count = self.prj_manager.db.execute_query(
        "SELECT COUNT(*) FROM metadati WHERE id = ?",
        (record_id,),
        fetch_mode="value"
    )
except RuntimeError as e:
    self.show_error("Database not available")
    return

# ❌ Wrong - Manual checks needed, error-prone
if self.prj_manager.db_manager and self.prj_manager.db_manager.is_connected():
    count = self.prj_manager.db_manager.execute_query(...)
```

**Key advantages:**

- **Single source of truth**: Validation logic in one place
- **Fail-fast**: Immediate exceptions instead of silent None returns
- **Cleaner external code**: No repetitive checks needed
- **Type-safe**: IDE autocomplete works perfectly

## Common Patterns

### Simple SELECT Query

```python
# Before (old way)
cursor = self.db_connection.cursor()
try:
    cursor.execute("SELECT * FROM comune_progetto LIMIT 1")
    row = cursor.fetchone()
    if row:
        # process row
finally:
    cursor.close()

# After (new way)
row = self.db.execute_query(
    "SELECT * FROM comune_progetto LIMIT 1",
    fetch_mode="one"
)
if row:
    # process row
```

### SELECT with Parameters

```python
# Before
cursor = self.db_connection.cursor()
try:
    cursor.execute("SELECT * FROM table WHERE id > ?", (10,))
    rows = cursor.fetchall()
finally:
    cursor.close()

# After
rows = self.db.execute_query(
    "SELECT * FROM table WHERE id > ?",
    (10,)
)
```

### Get Single Value

```python
# Before
cursor = self.db_connection.cursor()
try:
    cursor.execute("SELECT COUNT(*) FROM table")
    count = cursor.fetchone()[0]
finally:
    cursor.close()

# After
count = self.db.execute_query(
    "SELECT COUNT(*) FROM table",
    fetch_mode="value"
)
```

### INSERT with Auto-Commit

```python
# Before
cursor = self.db_connection.cursor()
try:
    cursor.execute("INSERT INTO table (name) VALUES (?)", ("value",))
    self.db_connection.commit()
    last_id = cursor.lastrowid
except Exception as e:
    self.db_connection.rollback()
    raise
finally:
    cursor.close()

# After
last_id = self.db.execute_update(
    "INSERT INTO table (name) VALUES (?)",
    ("value",)
)
```

### UPDATE/DELETE

```python
# Before
cursor = self.db_connection.cursor()
try:
    cursor.execute("UPDATE table SET status = ? WHERE id = ?", ("active", 1))
    self.db_connection.commit()
    affected = cursor.rowcount
except Exception as e:
    self.db_connection.rollback()
    raise
finally:
    cursor.close()

# After
affected = self.db.execute_update(
    "UPDATE table SET status = ? WHERE id = ?",
    ("active", 1)
)
```

### Multiple Operations in Transaction

```python
# Before
cursor = self.db_connection.cursor()
try:
    cursor.execute("INSERT INTO table1 VALUES (?)", (1,))
    cursor.execute("INSERT INTO table2 VALUES (?)", (2,))
    self.db_connection.commit()
except Exception as e:
    self.db_connection.rollback()
    raise
finally:
    cursor.close()

# After
with self.db.transaction() as cursor:
    cursor.execute("INSERT INTO table1 VALUES (?)", (1,))
    cursor.execute("INSERT INTO table2 VALUES (?)", (2,))
    # Auto-commit on success, auto-rollback on error
```

### Execute SQL Script File

```python
# Before
cursor = self.db_connection.cursor()
try:
    with open(script_path) as f:
        cursor.executescript(f.read())
    self.db_connection.commit()
finally:
    cursor.close()

# After
self.db.execute_script_file(script_path)
```

### Check if Table Exists

```python
# Before
cursor = self.db_connection.cursor()
try:
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    exists = cursor.fetchone() is not None
finally:
    cursor.close()

# After
exists = self.db.table_exists(table_name)
```

### Count Rows

```python
# Before
cursor = self.db_connection.cursor()
try:
    cursor.execute("SELECT COUNT(*) FROM sito_puntuale WHERE status = ?", ("active",))
    count = cursor.fetchone()[0]
finally:
    cursor.close()

# After
count = self.db.get_row_count("sito_puntuale", "status = ?", ("active",))
```

### Get/Reset Sequence

```python
# Before
cursor = self.db_connection.cursor()
try:
    cursor.execute('SELECT seq FROM sqlite_sequence WHERE name=?', (table_name,))
    row = cursor.fetchone()
    seq = row[0] if row else 0
finally:
    cursor.close()

# After
seq = self.db.get_sequence_value(table_name)

# Reset sequence
self.db.reset_sequence(table_name, 0)
```

## Fetch Modes

The `execute_query()` method supports three fetch modes:

- **`"all"`** (default): Returns list of all rows as tuples
- **`"one"`**: Returns first row as tuple (or None)
- **`"value"`**: Returns first column of first row (or None)

```python
# Get all rows
rows = db.execute_query("SELECT * FROM table")  # [(1, 'a'), (2, 'b')]

# Get single row
row = db.execute_query("SELECT * FROM table WHERE id = 1", fetch_mode="one")  # (1, 'a')

# Get single value
count = db.execute_query("SELECT COUNT(*) FROM table", fetch_mode="value")  # 42
```

## Error Handling

The `DatabaseManager` automatically:

- Closes cursors (even on error)
- Rolls back transactions on error
- Logs errors using the provided logger
- Raises `DatabaseError` with descriptive messages

```python
from mzs_tools.core.db_manager import DatabaseError

try:
    db.execute_update("INSERT INTO table VALUES (?)", (value,))
except DatabaseError as e:
    # Error already logged by DatabaseManager
    # Handle error appropriately
    pass
```

## Context Managers

### Manual Cursor Operations

For complex operations needing direct cursor access:

```python
with self.db.cursor() as cursor:
    cursor.execute("SELECT * FROM table1")
    rows1 = cursor.fetchall()

    cursor.execute("SELECT * FROM table2")
    rows2 = cursor.fetchall()
    # Cursor auto-closed
```

### Transaction Block

For multiple related operations:

```python
with self.db.transaction() as cursor:
    cursor.execute("INSERT INTO table1 VALUES (?)", (1,))
    cursor.execute("UPDATE table2 SET count = count + 1")
    cursor.execute("DELETE FROM table3 WHERE id = ?", (5,))
    # Auto-commit on success, auto-rollback on exception
```

## Tips

1. **Use helper methods**: `table_exists()`, `get_row_count()`, `get_sequence_value()`
2. **Prefer `execute_update()` over manual cursor**: For INSERT/UPDATE/DELETE
3. **Use transactions**: For multiple related operations
4. **Let DatabaseManager handle errors**: It logs automatically
5. **Use fetch modes**: Simplifies code compared to multiple fetchone/fetchall calls

## Common Mistakes to Avoid

❌ **Don't manually close cursors**

```python
with db.cursor() as cursor:
    cursor.execute("SELECT ...")
    cursor.close()  # NOT NEEDED! Auto-closed by context manager
```

❌ **Don't manually commit in execute_update**

```python
db.execute_update("INSERT ...", commit=True)  # commit=True is default
db.connection.commit()  # NOT NEEDED! Already committed
```

❌ **Don't mix old and new approaches**

```python
cursor = db.connection.cursor()  # Use db.cursor() context manager instead
```

✅ **Do use context managers**

```python
with db.cursor() as cursor:
    cursor.execute("...")
```

✅ **Do use appropriate wrapper methods**

```python
count = db.get_row_count("table")  # Instead of manual COUNT query
```

✅ **Do handle DatabaseError when needed**

```python
try:
    db.execute_update("INSERT ...")
except DatabaseError:
    # Handle specific case
    pass
```
