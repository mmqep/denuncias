"""Embebe todas las templates Jinja2 en _templates_cache.py para despliegue en Vercel.

Ejecutar antes de cada deploy:
    python build_templates.py
    git add _templates_cache.py
    git commit -m "chore: actualizar cache de templates"
    git push
"""
import os

templates = {}
for root, dirs, files in os.walk("templates"):
    for fname in sorted(files):
        path = os.path.join(root, fname)
        key = os.path.relpath(path, "templates").replace(os.sep, "/")
        with open(path, encoding="utf-8") as f:
            templates[key] = f.read()

with open("_templates_cache.py", "w", encoding="utf-8") as out:
    out.write("# Auto-generado por build_templates.py — no editar manualmente\n")
    out.write("TEMPLATES = {\n")
    for k, v in sorted(templates.items()):
        out.write(f"    {k!r}: {v!r},\n")
    out.write("}\n")

print(f"OK: {len(templates)} templates embebidas en _templates_cache.py")
