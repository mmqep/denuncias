# -*- coding: utf-8 -*-
"""Carga la configuración desde el archivo .env (no se versiona).

Expone los mismos símbolos que esperaba el resto de la aplicación
(`TIMEZONE`, `SECRET_KEY`, `MAX_UPLOAD_SIZE_BYTES`, `ALLOWED_EXTENSIONS`,
`UPLOAD_FOLDER`, `DB_CONFIG`) más las claves de conexión a Turso/libSQL.
No cambia el contrato de import de app.py.
"""

import os

from dotenv import load_dotenv

# Carga el .env ubicado junto a este archivo (independiente del cwd).
_ROOT = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_ROOT, ".env"))


def _get(name, default=""):
    val = os.environ.get(name)
    return default if val is None or val == "" else val


# --- Zona horaria institucional ---
TIMEZONE = _get("TIMEZONE", "America/Guayaquil")

# --- Secreto de sesiones ---
SECRET_KEY = _get("SECRET_KEY", "cambiar_por_valor_seguro")

# --- Modo debug de Flask ---
FLASK_DEBUG = _get("FLASK_DEBUG", "1") not in ("0", "false", "False", "no")

# --- Subida de archivos ---
MAX_UPLOAD_SIZE_BYTES = int(_get("MAX_UPLOAD_SIZE_BYTES", str(5 * 1024 * 1024)))
ALLOWED_EXTENSIONS = {
    e.strip().lower()
    for e in _get("ALLOWED_EXTENSIONS", "png,jpg,jpeg,pdf").split(",")
    if e.strip()
}
UPLOAD_FOLDER = _get("UPLOAD_FOLDER", "static/uploads")

# --- Turso / libSQL (réplica embebida) ---
TURSO_DATABASE_URL = _get("TURSO_DATABASE_URL")
TURSO_AUTH_TOKEN = _get("TURSO_AUTH_TOKEN")

# Compatibilidad: app.py importa y registra `DB_CONFIG` en app.config.
# db.py es quien realmente lo consume para conectar a Turso.
DB_CONFIG = {
    "database_url": TURSO_DATABASE_URL,
    "auth_token": TURSO_AUTH_TOKEN,
}
