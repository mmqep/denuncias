# -*- coding:utf-8 -*-
"""Capa de datos: Turso / libSQL (conexión remota directa).

Toda la traducción MySQL -> libSQL vive aquí dentro de un *shim* de
compatibilidad para que app.py siga usando la misma API que tenía con
PyMySQL (cursor como context manager, placeholders ``%s``, filas como
diccionarios con ``.get()``, ``lastrowid``, ``commit()/rollback()``).

`app.py` solo necesita: ``from db import close_db, get_db`` y
``from db import IntegrityError``.
"""

from datetime import date, datetime, time

import libsql
from flask import g

import config


class IntegrityError(Exception):
    """Violación de restricción UNIQUE / FOREIGN KEY / CHECK.

    Sustituye a ``pymysql.err.IntegrityError`` para que los bloques
    ``except IntegrityError`` de app.py sigan funcionando.
    """


# Subcadenas que delatan una violación de restricción en libSQL/SQLite.
_INTEGRITY_MARKERS = (
    "unique constraint",
    "foreign key constraint",
    "check constraint",
    "constraint failed",
    "not null constraint",
)

# Columnas temporales del esquema: se reconvierten al leer para preservar
# exactamente el comportamiento que daba PyMySQL (objetos datetime/date/time).
_DATETIME_COLS = {"fecha_creacion", "fecha_actualizacion", "fecha_cierre"}
_DATE_COLS = {"fecha_hecho"}
_TIME_COLS = {"hora_hecho"}


def _adapt_param(v):
    """Convierte datetime/date/time a texto ISO antes de bindear."""
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(v, date):
        return v.strftime("%Y-%m-%d")
    if isinstance(v, time):
        return v.strftime("%H:%M:%S")
    return v

#funcion adaptar parametros
def _adapt_params(params):
    if params is None:
        return ()
    if isinstance(params, (list, tuple)):
        return [_adapt_param(p) for p in params]
    return params


def _parse_dt(s):
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except (ValueError, TypeError):
            continue
    return s


def _parse_date(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return s


def _parse_time(s):
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(s, fmt).time()
        except (ValueError, TypeError):
            continue
    return s


def _convert_value(col, val):
    if val is None or not isinstance(val, str):
        return val
    if col in _DATETIME_COLS:
        return _parse_dt(val)
    if col in _DATE_COLS:
        return _parse_date(val)
    if col in _TIME_COLS:
        return _parse_time(val)
    return val


class CursorWrapper:
    """Imita el DictCursor de PyMySQL sobre un cursor libSQL."""

    def __init__(self, cursor):
        self._cur = cursor

    # --- context manager (app.py usa `with conn.cursor() as cur:`) ---
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            self._cur.close()
        except Exception:
            pass
        return False

    # --- ejecución ---
    def execute(self, sql, params=None):
        sql = sql.replace("%s", "?")
        try:
            self._cur.execute(sql, _adapt_params(params))
        except IntegrityError:
            raise
        except Exception as e:
            msg = str(e).lower()
            if any(m in msg for m in _INTEGRITY_MARKERS):
                raise IntegrityError(str(e)) from e
            raise
        return self

    def executemany(self, sql, seq):
        sql = sql.replace("%s", "?")
        self._cur.executemany(sql, [_adapt_params(p) for p in seq])
        return self

    # --- columnas para construir dicts ---
    def _columns(self):
        desc = getattr(self._cur, "description", None)
        if not desc:
            return None
        return [d[0] for d in desc]

    def _row_to_dict(self, row, cols):
        if row is None:
            return None
        return {c: _convert_value(c, row[i]) for i, c in enumerate(cols)}

    def fetchone(self):
        row = self._cur.fetchone()
        if row is None:
            return None
        cols = self._columns()
        if cols is None:
            return row
        return self._row_to_dict(row, cols)

    def fetchall(self):
        rows = self._cur.fetchall()
        cols = self._columns()
        if cols is None:
            return list(rows)
        return [self._row_to_dict(r, cols) for r in rows]

    @property
    def lastrowid(self):
        return self._cur.lastrowid

    @property
    def rowcount(self):
        return getattr(self._cur, "rowcount", -1)

    def close(self):
        try:
            self._cur.close()
        except Exception:
            pass


class ConnWrapper:
    """Envuelve la conexión libSQL con la API que usa app.py."""

    def __init__(self, conn):
        self._conn = conn

    def cursor(self):
        return CursorWrapper(self._conn.cursor())

    def commit(self):
        self._conn.commit()

    def rollback(self):
        try:
            self._conn.rollback()
        except Exception:
            pass

    def close(self):
        try:
            self._conn.close()
        except Exception:
            pass


def connect_db():
    url = config.TURSO_DATABASE_URL
    if not url:
        raise RuntimeError(
            "TURSO_DATABASE_URL no está configurado en .env. "
            "Ejecuta `turso db show <db>` y copia la URL libsql://."
        )
    conn = libsql.connect(url, auth_token=config.TURSO_AUTH_TOKEN or None)
    # SQLite/libSQL solo aplica FKs (ON DELETE SET NULL / CASCADE) si el
    # pragma está activo por conexión.
    conn.execute("PRAGMA foreign_keys=ON")
    return ConnWrapper(conn)


def get_db():
    if "db" not in g:
        g.db = connect_db()
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()
