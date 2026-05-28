import sys
import os

# Agrega la raíz del proyecto al path para que app.py, config.py y db.py
# sean importables desde este archivo (que vive en api/).
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import app as handler  # noqa: E402 — Vercel busca la variable 'handler'
