# -*- coding: utf-8 -*-
"""Configuración de la aplicación compatible con:
   - Desarrollo local (MariaDB/Backblaze B2)
   - Vercel (Turso + variables de entorno)
"""

import os
import pymysql.cursors

from dotenv import load_dotenv

# Carga el .env ubicado junto a este archivo (independiente del cwd)
_ROOT = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_ROOT, ".env"))


def _get(name, default=""):
    val = os.environ.get(name)
    return default if val is None or val == "" else val


# ========== CONFIGURACIÓN GENERAL ==========

# Zona horaria institucional
TIMEZONE = _get("TIMEZONE", "America/Guayaquil")

# Secreto de sesiones (cambiar en producción)
SECRET_KEY = _get("SECRET_KEY", "cambiar_por_valor_seguro_en_produccion_mmqep")

# Modo debug de Flask (Vercel lo maneja automáticamente)
FLASK_DEBUG = _get("FLASK_DEBUG", "1") not in ("0", "false", "False", "no")

# Subida de archivos
MAX_UPLOAD_SIZE_BYTES = int(_get("MAX_UPLOAD_SIZE_BYTES", str(5 * 1024 * 1024)))
ALLOWED_EXTENSIONS = {
    e.strip().lower()
    for e in _get("ALLOWED_EXTENSIONS", "png,jpg,jpeg,pdf").split(",")
    if e.strip()
}
UPLOAD_FOLDER = _get("UPLOAD_FOLDER", "static/uploads_test")


# ========== BACKBLAZE B2 (almacenamiento en la nube) ==========
B2_ACCOUNT_ID = _get("B2_ACCOUNT_ID")
B2_APPLICATION_KEY = _get("B2_APPLICATION_KEY")
B2_BUCKET_NAME = _get("B2_BUCKET_NAME")
B2_ENDPOINT_URL = _get("B2_ENDPOINT_URL")


# ========== BASE DE DATOS ==========
# Turso / libSQL (para Vercel)
TURSO_DATABASE_URL = _get("TURSO_DATABASE_URL")
TURSO_AUTH_TOKEN = _get("TURSO_AUTH_TOKEN")

# Compatibilidad con app.py: db.py consumirá esta configuración
DB_CONFIG = {
    "database_url": TURSO_DATABASE_URL,
    "auth_token": TURSO_AUTH_TOKEN,
}

# Si NO estamos en Vercel y no hay Turso, usar MariaDB local
if not TURSO_DATABASE_URL and not os.environ.get('VERCEL'):
    DB_CONFIG = {
        "host": _get("DB_HOST", "localhost"),
        "port": int(_get("DB_PORT", 3306)),
        "user": _get("DB_USER", "root"),
        "password": _get("DB_PASSWORD", "123456"),
        "db": _get("DB_NAME", "mmqep_denuncias_local"),
        "charset": "utf8mb4",
        "init_command": "SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci",
        "use_unicode": True,
        "cursorclass": pymysql.cursors.DictCursor,
        "connect_timeout": 10,
    }