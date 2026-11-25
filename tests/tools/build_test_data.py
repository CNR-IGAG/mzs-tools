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
"""Build the reduced Accumoli test archives used by the e2e tests.

The archives keep the file names and folder layout of the original (non-public) Accumoli data, with a few
features/rows per layer, coordinates shifted by a constant offset, slightly changed attributes and fake attachments.

Run from the repository root:

    export UV_ENV_FILE=.env.uv QT_QPA_PLATFORM=offscreen
    uv run python tests/tools/build_test_data.py standard --source ~/mzs-tools-test-data-originals/Accumoli.zip
    uv run python tests/tools/build_test_data.py imported
    uv run python tests/tools/build_test_data.py legacy \
        --source ~/mzs-tools-test-data-originals/057001_Accumoli_v1.9.4_imported.zip

`imported` reads the output of `standard` and must be rerun after every plugin version bump (`just test-data-imported`).
`legacy` is independent of the other two.
"""

import argparse
import os
import re
import shutil
import sqlite3
import sys
import tempfile
import zipfile
from contextlib import closing, suppress
from decimal import Decimal
from pathlib import Path

from osgeo import ogr

ogr.UseExceptions()

REPO_ROOT = Path(__file__).resolve().parents[2]

DX, DY = 120.0, -80.0  # metres, EPSG:32633
# P1 owns all the CSV/Curve.txt rows and has a .jpg attachment; P82, P89, P238 and P240 are required by
# test_manage_attachments; P10 (SPT), P237 (DH) and P209 (DP) are the first sites with parametri for each of those
# survey types.
KEEP_SPU = [1, 10, 82, 89, 209, 237, 238, 240]  # pkey_spu == pkuid; site IDs 057001P<n>
# the first 4 linear sites with parametri
KEEP_SLN = [2, 3, 4, 5]  # pkey_sln; site IDs 057001L<n>
ANCHOR = (356555.781307674, 4728451.1127115)  # Ind_pu point of 057001P1, before the shift
K_NEAREST = 5
MDB_TEST_PASSWORD = "mzstest"
REAL_FACTOR = 1.03
REAL_FACTOR_FIELDS = {  # compared lower-case
    "fa", "fv", "ft", "fh0105", "fh0510", "fh0515", "fpga", "fa0105", "fa0408", "fa0711",
    "frt", "frr", "il", "disl", "fs", "s", "valore", "valore2",
}  # fmt: skip
NULL_TEXT_COLUMNS = {  # lower-case column names set to NULL (sqlite) / "" (CSV) when not empty
    "sito_puntuale": ["desc_modcoord", "note_sito"],
    "sito_lineare": ["desc_modcoord", "note_sito"],
    "indagini_puntuali": ["id_indpuex", "arch_ex", "note_ind"],
    "indagini_lineari": ["id_indlnex", "arch_ex", "note_indln"],
    "parametri_puntuali": ["note_par"],
    "parametri_lineari": ["note_par"],
}
ZIP_DATE = (2026, 1, 1, 0, 0, 0)

COD_ISTAT = "057001"
SPU_IDS = [f"{COD_ISTAT}P{n}" for n in KEEP_SPU]
SLN_IDS = [f"{COD_ISTAT}L{n}" for n in KEEP_SLN]
NEAREST_LAYERS = [
    "GeoTec/Elineari.shp",
    "GeoTec/Epuntuali.shp",
    "GeoTec/Forme.shp",
    "GeoTec/Geoidr.shp",
    "GeoTec/Geotec.shp",
    "GeoTec/Instab_geotec.shp",
    "MS1/Instab.shp",
    "MS1/Isosub.shp",
    "MS1/Stab.shp",
    "MS23/Instab.shp",
    "MS23/Isosub.shp",
    "MS23/Stab.shp",
]
SMALL_AREA_LAYERS = {"MS1/Instab.shp", "MS1/Stab.shp", "MS23/Instab.shp", "MS23/Stab.shp"}
INVALID_GEOM_LAYERS = {"MS23/Instab.shp"}
SPETTRO_ALWAYS = "AccumoliPSAOm02.txt"
# the project databases hold all the Italian municipalities (18 MB): keep only Lazio, like the committed *_new.zip
# projects (057002 Amatrice, used by test_merge_projects, is in Lazio too)
COMUNI_KEEP_COD_REGIO = "12"
# original 1.9.4 project files larger than 1 MB, replaced by a small fake image with the same name
LEGACY_LARGE_IMAGES = ["progetto/loghi/mappa_reg.png"]
LEGACY_LAYER_TABLES = [
    "elineari", "epuntuali", "forme", "geoidr", "geotec", "instab_geotec",
    "instab_l1", "instab_l23", "stab_l1", "stab_l23", "isosub_l1", "isosub_l23",
]  # fmt: skip

# survey CSV files: lower-case file stem -> (filter column, key set name, produced key column, produced key set name)
CSV_CHAIN = [
    ("sito_puntuale", "pkey_spu", "spu", None, None),
    ("indagini_puntuali", "pkey_spu", "spu", "pkey_indpu", "indpu"),
    ("parametri_puntuali", "pkey_indpu", "indpu", "pkey_parpu", "parpu"),
    ("curve", "pkey_parpu", "parpu", None, None),
    ("sito_lineare", "pkey_sln", "sln", None, None),
    ("indagini_lineari", "pkey_sln", "sln", "pkey_indln", "indln"),
    ("parametri_lineari", "pkey_indln", "indln", None, None),
]


# ----------------------------------------------------------------------------- shared helpers


def _columns(conn: sqlite3.Connection, table: str) -> dict[str, str]:
    """Lower-case column name -> actual column name."""
    return {row[1].lower(): row[1] for row in conn.execute(f'PRAGMA table_info("{table}")')}


def _tables(conn: sqlite3.Connection) -> dict[str, str]:
    """Lower-case table name -> actual table name."""
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    return {name.lower(): name for (name,) in rows}


def sanitize_survey_db(conn: sqlite3.Connection, key_col_spu: str) -> None:
    tables = _tables(conn)
    for table_lc, columns in NULL_TEXT_COLUMNS.items():
        table = tables.get(table_lc)
        if table is None:
            continue
        cols = _columns(conn, table)
        for col_lc in columns:
            if col_lc in cols:
                c = cols[col_lc]
                conn.execute(f'UPDATE "{table}" SET "{c}" = NULL WHERE "{c}" IS NOT NULL AND "{c}" <> \'\'')

    if "sito_puntuale" in tables:
        t = tables["sito_puntuale"]
        cols = _columns(conn, t)
        if "indirizzo" in cols and key_col_spu.lower() in cols:
            c, k = cols["indirizzo"], cols[key_col_spu.lower()]
            conn.execute(
                f'UPDATE "{t}" SET "{c}" = \'Via di prova \' || "{k}" WHERE "{c}" IS NOT NULL AND "{c}" <> \'\''
            )
        if "quota_slm" in cols:
            c = cols["quota_slm"]
            conn.execute(f'UPDATE "{t}" SET "{c}" = "{c}" + 3 WHERE "{c}" IS NOT NULL')

    if "parametri_lineari" in tables:
        t = tables["parametri_lineari"]
        c = _columns(conn, t).get("valore")
        if c:
            conn.execute(f'UPDATE "{t}" SET "{c}" = ROUND("{c}" * {REAL_FACTOR}, 2) WHERE "{c}" IS NOT NULL')

    if "parametri_puntuali" in tables:
        t = tables["parametri_puntuali"]
        c = _columns(conn, t).get("valore")
        if c:
            conn.execute(
                f'UPDATE "{t}" SET "{c}" = printf(\'%.2f\', CAST("{c}" AS REAL) * {REAL_FACTOR}) '
                f"WHERE \"{c}\" <> '' AND \"{c}\" NOT GLOB '*[^0-9.]*'"
            )


def sanitize_metadati(conn: sqlite3.Connection) -> None:
    values = {
        "_nome": "Autore di prova",
        "_email": "test@example.com",
        "_sito": "https://www.example.com",
        "_telefono": "0000000000",
    }
    for table_lc, table in _tables(conn).items():
        if table_lc != "metadati":
            continue
        for col_lc, col in _columns(conn, table).items():
            for suffix, value in values.items():
                if col_lc.endswith(suffix):
                    conn.execute(f'UPDATE "{table}" SET "{col}" = ? WHERE "{col}" IS NOT NULL', (value,))


def translate_geom(g: ogr.Geometry) -> None:
    if g.GetGeometryCount() > 0:
        for i in range(g.GetGeometryCount()):
            translate_geom(g.GetGeometryRef(i))
        return
    for i in range(g.GetPointCount()):
        x, y, z = g.GetPoint(i)
        if g.GetCoordinateDimension() == 3:
            g.SetPoint(i, x + DX, y + DY, z)
        else:
            g.SetPoint_2D(i, x + DX, y + DY)


def _fake_pdf() -> bytes:
    content = b"BT /F1 10 Tf 10 50 Td (MzS Tools test attachment) Tj ET"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 100] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(content) + content + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for n, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % n + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    for offset in offsets:
        out += b"%010d 00000 n \n" % offset
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objects) + 1, xref)
    return bytes(out)


def write_fake(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        path.write_bytes(_fake_pdf())
    elif suffix in (".jpg", ".jpeg", ".png"):
        from qgis.PyQt.QtGui import QColor, QImage

        image_format = "PNG" if suffix == ".png" else "JPG"
        image = QImage(16, 16, QImage.Format.Format_RGB32)
        image.fill(QColor(200, 200, 200))
        if not image.save(str(path), image_format):
            raise SystemExit(f"Cannot write fake {image_format} image {path}")
    else:
        path.write_text(f"MzS Tools test attachment: {path.name}\n", encoding="utf-8")


def trim_comuni(conn: sqlite3.Connection) -> None:
    """Delete the municipalities outside COMUNI_KEEP_COD_REGIO (mod_spatialite must be loaded for the triggers)."""
    conn.execute("DELETE FROM comuni WHERE cod_regio <> ?", (COMUNI_KEEP_COD_REGIO,))


def open_spatialite(db: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db)
    conn.enable_load_extension(True)
    conn.load_extension("mod_spatialite")
    return conn


def write_fake_spettro(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("T(s) PSA(g)\n0.00 0.250\n0.10 0.500\n0.50 0.400\n1.00 0.200\n2.00 0.080\n", encoding="utf-8")


def _basename(value: str) -> str:
    return re.split(r"[\\/]", value.strip())[-1]


def zip_dir(root: Path, zip_path: Path) -> None:
    entries = [root]
    for dirpath, dirnames, filenames in os.walk(root):
        entries += [Path(dirpath) / name for name in dirnames + filenames]
    items = sorted((p.relative_to(root.parent).as_posix() + ("/" if p.is_dir() else ""), p) for p in entries)
    tmp_path = zip_path.with_suffix(".zip.tmp")
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for arcname, path in items:
            info = zipfile.ZipInfo(arcname, date_time=ZIP_DATE)
            if path.is_dir():
                info.external_attr = (0o755 << 16) | 0x10
                zf.writestr(info, b"")
            else:
                info.external_attr = 0o644 << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                zf.writestr(info, path.read_bytes(), compresslevel=9)
    tmp_path.replace(zip_path)
    print(f"Written {zip_path} ({zip_path.stat().st_size / 1024:.0f} KiB)")


def extract(zip_path: Path, dest: Path) -> None:
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(dest)


def start_qgis():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    import qgis.utils
    from pytest_qgis.mock_qgis_classes import MockMessageBar
    from pytest_qgis.qgis_interface import QgisInterface
    from qgis.core import QgsApplication
    from qgis.gui import QgsGui, QgsMapCanvas
    from qgis.PyQt.QtWidgets import QMainWindow

    app = QgsApplication([], True)
    app.initQgis()
    QgsGui.editorWidgetRegistry().initEditors()
    main_window = QMainWindow()
    canvas = QgsMapCanvas(main_window)
    qgis.utils.iface = QgisInterface(canvas, MockMessageBar(), main_window)
    sys.path.insert(0, str(REPO_ROOT))
    return app, main_window, canvas


def import_standard(standard_dir: Path, out_dir: Path) -> Path:
    from qgis.core import QgsProcessingFeedback

    from mzs_tools.processing.standard_project_import import (
        IMPORT_STATUS_CREATED,
        import_standard_project,
        load_comuni_names,
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    result = import_standard_project(
        standard_dir,
        out_dir,
        cod_istat=None,
        indagini_source="auto",
        mdb_password=None,
        csv_dir=None,
        study_author="MzS Tools test",
        author_email="test@example.com",
        comuni_names=load_comuni_names(),
        feedback=QgsProcessingFeedback(),
    )
    assert result.status == IMPORT_STATUS_CREATED, result.message
    assert result.indagini_source == "sqlite", result.indagini_source
    assert result.project_path is not None
    return result.project_path


def export_mdb(project_dir: Path, out_dir: Path) -> Path:
    from qgis.core import QgsProcessingFeedback

    from mzs_tools.processing.standard_project_export import export_project_to_standard

    out_dir.mkdir(parents=True, exist_ok=True)
    result = export_project_to_standard(
        project_dir / "progetto_MS.qgz", out_dir, indagini_format="mdb", feedback=QgsProcessingFeedback()
    )
    assert result.export_path is not None, result.message
    return result.export_path / "Indagini" / "CdI_Tabelle.mdb"


def rc4(key: bytes, data: bytes) -> bytes:
    s = list(range(256))
    j = 0
    for i in range(256):
        j = (j + s[i] + key[i % len(key)]) % 256
        s[i], s[j] = s[j], s[i]
    out = bytearray()
    i = j = 0
    for byte in data:
        i = (i + 1) % 256
        j = (j + s[i]) % 256
        s[i], s[j] = s[j], s[i]
        out.append(byte ^ s[(s[i] + s[j]) % 256])
    return bytes(out)


def set_mdb_password(src: Path, dst: Path, password: str) -> None:
    """Write a copy of the Jet4 MDB src (without password) protected by password."""
    key = b"\xc7\xda\x39\x6b"
    data = src.read_bytes()
    assert data[0x14] == 1, "not a Jet4 database"
    dec = rc4(key, data[0x18:0x98])
    mask = dec[0x2A:0x52]  # the password field of a database without password is exactly the XOR mask
    pw = password.encode("utf-16-le").ljust(40, b"\0")
    new = dec[:0x2A] + bytes(m ^ p for m, p in zip(mask, pw, strict=True)) + dec[0x52:]
    dst.write_bytes(data[:0x18] + rc4(key, new) + data[0x98:])


def verify_mdbs(no_pwd: Path, pwd: Path) -> None:
    from mzs_tools.tasks.access_db_connection import AccessDbConnection, MdbAuthError

    conn = AccessDbConnection(str(no_pwd))
    if not conn.open():
        raise SystemExit(f"Cannot open {no_pwd} without password")
    conn.close()

    try:
        conn = AccessDbConnection(str(pwd))
        conn.open()
    except MdbAuthError:
        pass
    else:
        conn.close()
        raise SystemExit(f"{pwd} opens without password: the password patch did not work")

    conn = AccessDbConnection(str(pwd), password=MDB_TEST_PASSWORD)
    try:
        opened = conn.open()
    except MdbAuthError as e:
        raise SystemExit(f"{pwd} does not open with the test password: the password patch did not work") from e
    if not opened:
        raise SystemExit(f"Cannot open {pwd} with the test password")
    conn.close()


# ----------------------------------------------------------------------------- standard


def _in_list(values) -> str:
    return "(" + ",".join(str(int(v)) for v in values) + ")"


def reduce_survey_sqlite(db: Path) -> None:
    with closing(sqlite3.connect(db)) as conn:
        spu, sln = _in_list(KEEP_SPU), _in_list(KEEP_SLN)
        kept_indpu = f"(SELECT pkey_indpu FROM indagini_puntuali WHERE pkey_spu IN {spu})"
        kept_parpu = f"(SELECT pkey_parpu FROM parametri_puntuali WHERE pkey_indpu IN {kept_indpu})"
        kept_indln = f"(SELECT pkey_indln FROM indagini_lineari WHERE pkey_sln IN {sln})"
        conn.execute(f"DELETE FROM curve WHERE pkey_parpu IS NULL OR pkey_parpu NOT IN {kept_parpu}")
        conn.execute(f"DELETE FROM parametri_puntuali WHERE pkey_indpu IS NULL OR pkey_indpu NOT IN {kept_indpu}")
        conn.execute(f"DELETE FROM indagini_puntuali WHERE pkey_spu IS NULL OR pkey_spu NOT IN {spu}")
        conn.execute(f"DELETE FROM sito_puntuale WHERE pkey_spu NOT IN {spu}")
        conn.execute(f"DELETE FROM parametri_lineari WHERE pkey_indln IS NULL OR pkey_indln NOT IN {kept_indln}")
        conn.execute(f"DELETE FROM indagini_lineari WHERE pkey_sln IS NULL OR pkey_sln NOT IN {sln}")
        conn.execute(f"DELETE FROM sito_lineare WHERE pkey_sln NOT IN {sln}")
        conn.execute(f"UPDATE sito_puntuale SET coord_X = coord_X + {DX}, coord_Y = coord_Y + {DY}")
        conn.execute(
            f"UPDATE sito_lineare SET Acoord_X = Acoord_X + {DX}, Acoord_Y = Acoord_Y + {DY}, "
            f"Bcoord_X = Bcoord_X + {DX}, Bcoord_Y = Bcoord_Y + {DY}"
        )
        sanitize_survey_db(conn, "pkey_spu")
        sanitize_metadati(conn)
        conn.commit()
        conn.execute("VACUUM")


def _parse_raw_csv(text: str) -> list[list[tuple[str, bool]]]:
    """Parse a ;-separated file into records of (value, was_quoted) pairs."""
    records: list[list[tuple[str, bool]]] = []
    record: list[tuple[str, bool]] = []
    i, n = 0, len(text)
    while i < n:
        if text[i] == '"':
            i += 1
            value = []
            while True:
                if i >= n:
                    raise ValueError("unterminated quoted value")
                if text[i] == '"':
                    if i + 1 < n and text[i + 1] == '"':
                        value.append('"')
                        i += 2
                        continue
                    i += 1
                    break
                value.append(text[i])
                i += 1
            record.append(("".join(value), True))
        else:
            start = i
            while i < n and text[i] not in ";\r\n":
                i += 1
            record.append((text[start:i], False))
        if i < n and text[i] == ";":
            i += 1
            if i == n:
                record.append(("", False))
            continue
        # end of record
        if text.startswith("\r\n", i):
            i += 2
        elif i < n:
            i += 1
        records.append(record)
        record = []
    if record:
        records.append(record)
    return records


def _shift(value: str, delta: float) -> str:
    if not value.strip():
        return value
    decimals = len(value.split(".")[1]) if "." in value else 0
    return f"{Decimal(value) + Decimal(str(delta)):.{decimals}f}"


def _csv_row_edits(table: str, row: dict[str, str]) -> None:
    """Apply the same value edits as the sqlite survey database (row keys are lower-case)."""
    for col in NULL_TEXT_COLUMNS.get(table, []):
        if col in row:
            row[col] = ""
    if table == "sito_puntuale":
        row["coord_x"] = _shift(row["coord_x"], DX)
        row["coord_y"] = _shift(row["coord_y"], DY)
        row["quota_slm"] = _shift(row["quota_slm"], 3)
        if row.get("indirizzo"):
            row["indirizzo"] = f"Via di prova {row['pkey_spu']}"
    elif table == "sito_lineare":
        for prefix in ("a", "b"):
            row[f"{prefix}coord_x"] = _shift(row[f"{prefix}coord_x"], DX)
            row[f"{prefix}coord_y"] = _shift(row[f"{prefix}coord_y"], DY)
    elif table in ("parametri_puntuali", "parametri_lineari"):
        value = row.get("valore", "").strip()
        # parametri_puntuali.valore is a text column: only plain positive numbers are changed, as in the sqlite update
        if value and (table == "parametri_lineari" or re.fullmatch(r"[0-9.]+", value)):
            with suppress(ValueError):
                row["valore"] = f"{float(value) * REAL_FACTOR:.2f}"


def reduce_csv(src_dir: Path, out_dir: Path) -> None:
    files = {p.stem.lower(): p for p in src_dir.iterdir() if p.is_file()}
    keys: dict[str, set[str]] = {"spu": {str(n) for n in KEEP_SPU}, "sln": {str(n) for n in KEEP_SLN}}
    out_dir.mkdir(parents=True, exist_ok=True)
    for table, filter_col, filter_set, produced_col, produced_set in CSV_CHAIN:
        src = files[table]
        records = _parse_raw_csv(src.read_bytes().decode("latin-1"))
        header = [value for value, _quoted in records[0]]
        header_lc = [h.lower() for h in header]
        data = records[1:]
        quoted = []
        for col in range(len(header)):
            first = next((rec[col] for rec in data if col < len(rec) and rec[col][0] != ""), ("", False))
            quoted.append(first[1])

        rows = []
        for rec in data:
            row = dict(zip(header_lc, (value for value, _quoted in rec), strict=True))
            if row[filter_col] not in keys[filter_set]:
                continue
            _csv_row_edits(table, row)
            rows.append(row)
        if produced_col:
            keys[produced_set] = {row[produced_col] for row in rows}

        def fmt(value: str, quote: bool) -> str:
            if value == "":
                return ""
            return '"' + value.replace('"', '""') + '"' if quote else value

        lines = [";".join('"' + h.replace('"', '""') + '"' for h in header)]
        lines += [";".join(fmt(row[h], q) for h, q in zip(header_lc, quoted, strict=True)) for row in rows]
        (out_dir / src.name).write_bytes("".join(line + "\r\n" for line in lines).encode("latin-1"))


def _edit_feature(feat: ogr.Feature, fid: int) -> None:
    defn = feat.GetDefnRef()
    for i in range(defn.GetFieldCount()):
        fdefn = defn.GetFieldDefn(i)
        name = fdefn.GetName().lower()
        if not feat.IsFieldSetAndNotNull(i):
            continue
        if fdefn.GetType() == ogr.OFTReal and name in REAL_FACTOR_FIELDS:
            value = feat.GetFieldAsDouble(i)
            if value != 0:
                feat.SetField(i, round(value * REAL_FACTOR, 3))
        elif (
            fdefn.GetType() == ogr.OFTString
            and (name.startswith("descr") or name == "note")
            and feat.GetFieldAsString(i) != ""
        ):
            feat.SetField(i, f"Descrizione di prova {fid}")


def _select_nearest(layer_path: str, features: list[ogr.Feature]) -> set[int]:
    anchor = ogr.Geometry(ogr.wkbPoint)
    anchor.AddPoint_2D(*ANCHOR)
    with_geom = [f for f in features if f.GetGeometryRef() is not None]
    by_distance = sorted(with_geom, key=lambda f: (f.GetGeometryRef().Distance(anchor), f.GetFID()))
    kept = {f.GetFID() for f in by_distance[:K_NEAREST]}
    if layer_path in SMALL_AREA_LAYERS:
        small = [f.GetFID() for f in with_geom if f.GetGeometryRef().GetArea() < 1]
        if small:
            kept.add(min(small))
    if layer_path in INVALID_GEOM_LAYERS:
        invalid = [f.GetFID() for f in with_geom if not f.GetGeometryRef().IsValid()]
        if invalid:
            kept.add(min(invalid))
    return kept


def reduce_shapefile(src: Path, dst: Path, layer_path: str) -> list[ogr.Feature]:
    """Write the reduced copy of src to dst and return the kept (edited) features."""
    src_ds = ogr.Open(str(src))
    src_layer = src_ds.GetLayer()
    features = list(src_layer)
    if layer_path == "Indagini/Ind_pu.shp":
        kept = {f.GetFID() for f in features if f.GetField("ID_SPU") in SPU_IDS}
    elif layer_path == "Indagini/Ind_ln.shp":
        kept = {f.GetFID() for f in features if f.GetField("ID_SLN") in SLN_IDS}
    else:
        kept = _select_nearest(layer_path, features)

    dst.parent.mkdir(parents=True, exist_ok=True)
    driver = ogr.GetDriverByName("ESRI Shapefile")
    dst_ds = driver.CreateDataSource(str(dst))
    src_defn = src_layer.GetLayerDefn()
    dst_layer = dst_ds.CreateLayer(
        dst.stem, src_layer.GetSpatialRef(), src_layer.GetGeomType(), options=["ENCODING=UTF-8"]
    )
    for i in range(src_defn.GetFieldCount()):
        dst_layer.CreateField(src_defn.GetFieldDefn(i))
    dst_defn = dst_layer.GetLayerDefn()

    written = []
    for feat in sorted((f for f in features if f.GetFID() in kept), key=lambda f: f.GetFID()):
        out = ogr.Feature(dst_defn)
        out.SetFrom(feat)
        geom = feat.GetGeometryRef()
        if geom is not None:
            geom = geom.Clone()
            translate_geom(geom)
            out.SetGeometry(geom)
        _edit_feature(out, feat.GetFID())
        dst_layer.CreateFeature(out)
        written.append(out)
    dst_ds = None  # flush
    return written


def build_standard(source: Path, out_zip: Path) -> None:
    with tempfile.TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)
        extract(source, tmp / "src")
        src = tmp / "src" / "Accumoli"
        out = tmp / "out" / "Accumoli"
        out.mkdir(parents=True)

        # survey sqlite
        db = out / "Indagini" / "CdI_Tabelle.sqlite"
        db.parent.mkdir(parents=True)
        shutil.copy2(src / "Indagini" / "CdI_Tabelle.sqlite", db)
        reduce_survey_sqlite(db)

        # survey CSV
        reduce_csv(src / "CSV", out / "CSV")

        # shapefiles
        spettri: set[str] = {SPETTRO_ALWAYS}
        for layer_path in ["Indagini/Ind_pu.shp", "Indagini/Ind_ln.shp", *NEAREST_LAYERS]:
            features = reduce_shapefile(src / layer_path, out / layer_path, layer_path)
            if layer_path in ("MS23/Stab.shp", "MS23/Instab.shp"):
                for feat in features:
                    value = feat.GetField("SPETTRI")
                    if value and value.strip():
                        spettri.add(_basename(value))

        # fake attachments
        with closing(sqlite3.connect(db)) as conn:
            refs = conn.execute(
                "SELECT doc_ind FROM indagini_puntuali UNION SELECT doc_ind FROM indagini_lineari "
                "UNION SELECT tab_curve FROM parametri_puntuali"
            ).fetchall()
        doc_names = {_basename(value) for (value,) in refs if value and value.strip()}
        src_docs = {p.name for p in (src / "Indagini" / "Documenti").rglob("*") if p.is_file()}
        for name in sorted(doc_names & src_docs):
            write_fake(out / "Indagini" / "Documenti" / name)
        src_spettri = {p.name for p in (src / "MS23" / "Spettri").iterdir() if p.is_file()}
        for name in sorted(spettri & src_spettri):
            write_fake_spettro(out / "MS23" / "Spettri" / name)

        # MDB files, exported from a project imported from the reduced sqlite
        project = import_standard(out, tmp / "imp")
        mdb = export_mdb(project, tmp / "exp")
        no_pwd = out / "Indagini" / "CdI_Tabelle_no_pwd.mdb"
        pwd = out / "Indagini" / "CdI_Tabelle.mdb"
        shutil.copy2(mdb, no_pwd)
        set_mdb_password(no_pwd, pwd, MDB_TEST_PASSWORD)
        verify_mdbs(no_pwd, pwd)

        zip_dir(out, out_zip)


# ----------------------------------------------------------------------------- imported


def build_imported(standard: Path, out_dir: Path) -> None:
    from mzs_tools.__about__ import __base_version__

    with tempfile.TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)
        extract(standard, tmp / "std")
        project = import_standard(tmp / "std" / "Accumoli", tmp / "imp")
        for backup in (project / "db").glob("*backup*.sqlite"):
            backup.unlink()
        with closing(open_spatialite(project / "db" / "indagini.sqlite")) as conn:
            trim_comuni(conn)
            conn.commit()
            conn.execute("VACUUM")
        zip_dir(project, out_dir / f"057001_Accumoli_v{__base_version__}_imported.zip")


# ----------------------------------------------------------------------------- legacy


def reduce_legacy_db(db: Path) -> set[str]:
    """Reduce the 1.9.4 project database; return the basenames of the attachments still referenced."""
    with closing(open_spatialite(db)) as conn:
        k = "(" + ",".join(f"'{v}'" for v in SPU_IDS) + ")"
        kl = "(" + ",".join(f"'{v}'" for v in SLN_IDS) + ")"
        kept_indpu = f"(SELECT id_indpu FROM indagini_puntuali WHERE id_spu IN {k})"
        kept_parpu = (
            "(SELECT p.id_parpu FROM parametri_puntuali p JOIN indagini_puntuali i ON p.id_indpu = i.id_indpu "
            f"WHERE i.id_spu IN {k})"
        )
        kept_indln = f"(SELECT id_indln FROM indagini_lineari WHERE id_sln IN {kl})"
        conn.execute(f"DELETE FROM curve WHERE id_parpu NOT IN {kept_parpu}")
        conn.execute(f"DELETE FROM hvsr WHERE id_indpu NOT IN {kept_indpu}")
        conn.execute(f"DELETE FROM parametri_puntuali WHERE id_indpu NOT IN {kept_indpu}")
        conn.execute(f"DELETE FROM indagini_puntuali WHERE id_spu NOT IN {k}")
        conn.execute(f"DELETE FROM sito_puntuale WHERE id_spu NOT IN {k}")
        conn.execute(f"DELETE FROM parametri_lineari WHERE id_indln NOT IN {kept_indln}")
        conn.execute(f"DELETE FROM indagini_lineari WHERE id_sln NOT IN {kl}")
        conn.execute(f"DELETE FROM sito_lineare WHERE id_sln NOT IN {kl}")
        for t in LEGACY_LAYER_TABLES:
            conn.execute(
                f"DELETE FROM {t} WHERE pkuid NOT IN (SELECT pkuid FROM {t} ORDER BY pkuid LIMIT {K_NEAREST})"
            )

        # one UPDATE per table, so that the triggers see consistent values
        conn.execute(
            f"UPDATE sito_puntuale SET coord_x = coord_x + {DX}, coord_y = coord_y + {DY}, "
            f"geom = ST_Translate(geom, {DX}, {DY}, 0)"
        )
        conn.execute(
            f"UPDATE sito_lineare SET acoord_x = acoord_x + {DX}, acoord_y = acoord_y + {DY}, "
            f"bcoord_x = bcoord_x + {DX}, bcoord_y = bcoord_y + {DY}, geom = ST_Translate(geom, {DX}, {DY}, 0)"
        )
        for t in LEGACY_LAYER_TABLES:
            conn.execute(f"UPDATE {t} SET geom = ST_Translate(geom, {DX}, {DY}, 0)")

        sanitize_survey_db(conn, "pkuid")
        sanitize_metadati(conn)
        trim_comuni(conn)
        for t in LEGACY_LAYER_TABLES:
            for col_lc, col in _columns(conn, t).items():
                if col_lc in REAL_FACTOR_FIELDS:
                    conn.execute(
                        f'UPDATE {t} SET "{col}" = ROUND("{col}" * {REAL_FACTOR}, 3) '
                        f'WHERE "{col}" IS NOT NULL AND "{col}" <> 0'
                    )
        conn.commit()
        conn.execute("VACUUM")

        refs = conn.execute(
            "SELECT doc_ind FROM indagini_puntuali UNION SELECT doc_ind FROM indagini_lineari "
            "UNION SELECT tab_curve FROM parametri_puntuali UNION SELECT SPETTRI FROM stab_l23 "
            "UNION SELECT SPETTRI FROM instab_l23"
        ).fetchall()
    return {_basename(value) for (value,) in refs if value and str(value).strip()}


def build_legacy(source: Path, out_zip: Path) -> None:
    with tempfile.TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)
        extract(source, tmp / "src")
        project = tmp / "src" / "057001_Accumoli"
        kept = reduce_legacy_db(project / "db" / "indagini.sqlite")

        allegati = project / "Allegati"
        for path in allegati.rglob("*"):
            if path.is_file():
                path.unlink()
        with zipfile.ZipFile(source) as zf:
            members = [m for m in zf.namelist() if m.startswith("057001_Accumoli/Allegati/") and not m.endswith("/")]
        for member in members:
            if member.rsplit("/", 1)[-1] not in kept:
                continue
            path = tmp / "src" / member
            if member.startswith("057001_Accumoli/Allegati/Spettri/"):
                write_fake_spettro(path)
            else:
                write_fake(path)
        for image in LEGACY_LARGE_IMAGES:
            write_fake(project / image)

        zip_dir(project, out_zip)


# ----------------------------------------------------------------------------- main


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("standard", help="build the reduced standard project archive")
    p.add_argument("--source", type=Path, required=True, help="original Accumoli.zip")
    p.add_argument("--out", type=Path, default=REPO_ROOT / "tests/data/standard_projects/Accumoli.zip")

    p = sub.add_parser("imported", help="build the reduced imported project archive for the current plugin version")
    p.add_argument("--standard", type=Path, default=REPO_ROOT / "tests/data/standard_projects/Accumoli.zip")
    p.add_argument("--out-dir", type=Path, default=REPO_ROOT / "tests/data/mzs_projects")

    p = sub.add_parser("legacy", help="build the reduced 1.9.4 imported project archive")
    p.add_argument("--source", type=Path, required=True, help="original 057001_Accumoli_v1.9.4_imported.zip")
    p.add_argument(
        "--out", type=Path, default=REPO_ROOT / "tests/data/mzs_projects/057001_Accumoli_v1.9.4_imported.zip"
    )

    args = parser.parse_args()
    if args.command == "legacy":
        build_legacy(args.source.expanduser(), args.out)
        return

    qgis_objects = start_qgis()  # noqa: F841 - keep references alive while the QGIS objects are in use
    if args.command == "standard":
        build_standard(args.source.expanduser(), args.out)
    else:
        build_imported(args.standard, args.out_dir)


if __name__ == "__main__":
    main()
