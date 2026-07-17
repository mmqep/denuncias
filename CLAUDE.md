# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Resumen ejecutivo

**"Tu voz cuenta"** es el sistema de gestión de quejas y denuncias ciudadanas del
**Mercado Mayorista de Quito (MMQEP)**. Permite al ciudadano registrar irregularidades
(especulación, movilidad, operaciones, etc.) desde un portal público, obtener un código
de seguimiento (`MMQ-XXXXXXXX`), y consultar el estado de su caso. Internamente, el
equipo institucional gestiona los expedientes a través de un panel administrativo con
roles, asignaciones, seguimiento de estados y generación de reportes.

Tecnologías centrales: **Flask · Jinja2 · Turso/libSQL · Backblaze B2 · ReportLab ·
openpyxl · Leaflet/OpenStreetMap**. Despliegue en **Vercel** (Python serverless).

---

## Tecnologías

| Capa | Tecnología |
|---|---|
| Backend | Python 3.11+, Flask 2.x |
| Base de datos | Turso/libSQL (SQLite compatible, nube) |
| ORM/acceso DB | Raw SQL con shim PyMySQL-compatible (`db.py`) |
| Templates | Jinja2 (DictLoader en Vercel, FileSystemLoader local) |
| Frontend | HTML/CSS/JS vanilla — sin SPA, sin build step |
| Mapa | Leaflet 1.9.4 + OpenStreetMap (tiles gratuitos) |
| Archivos | Backblaze B2 (boto3 vía S3-API) |
| PDF | ReportLab (comprobante ciudadano + reporte de bandeja) |
| Excel | openpyxl (exportación de bandeja) |
| Autenticación | Sesiones Flask (session), Werkzeug password hashing |
| Config | python-dotenv (.env) |
| Zona horaria | pytz — `America/Guayaquil` por defecto |
| Deploy | Vercel (vercel.json, @vercel/python) |

---

## Estructura de archivos

```
Quejas_Vercel/
├── app.py                   # Toda la lógica de la aplicación (~2500 líneas)
├── db.py                    # Shim PyMySQL→libSQL (CursorWrapper, ConnWrapper)
├── config.py                # Variables de entorno; detección Turso vs MariaDB local
├── cloud_storage.py         # Subida/lectura en Backblaze B2 (compresión automática)
├── pdf_comprobante.py       # PDF del comprobante para el ciudadano
├── pdf_reporte_bandeja.py   # PDF de reporte interno/externo de expediente
├── build_templates.py       # Pre-build: embebe templates en _templates_cache.py
├── _templates_cache.py      # Auto-generado; usado por DictLoader en Vercel
├── vercel.json              # Config de Vercel (buildCommand, routes)
├── requirements.txt         # Dependencias pip
├── .env.example             # Plantilla de variables de entorno
├── schema.sql               # DDL SQLite/libSQL — única fuente de verdad del esquema
├── static/
│   ├── css/styles.css       # Estilos globales
│   ├── js/app.js            # JS del portal público
│   └── uploads/             # Archivos subidos (solo desarrollo local; B2 en Vercel)
└── templates/
    ├── base_public.html     # Layout base portal ciudadano (Leaflet incluido)
    ├── base_admin.html      # Layout base panel administrativo (Leaflet incluido)
    ├── auth/login.html      # Formulario de login
    ├── public/
    │   ├── index.html       # Formulario de denuncia (7 pasos, mapa)
    │   ├── consulta.html    # Consulta de estado por código
    │   └── resultado.html   # Confirmación tras registro
    └── admin/
        ├── dashboard.html   # Métricas y resumen del panel
        ├── denuncias.html   # Bandeja de expedientes
        ├── detalle_denuncia.html  # Vista individual + mapa + historial
        ├── usuarios.html    # CRUD de usuarios institucionales
        ├── usuario_editar.html
        ├── categorias.html  # CRUD categorías/subcategorías
        ├── areas.html       # CRUD de áreas y asignación de responsable
        ├── reportes.html    # Estadísticas y exportación
        └── mis_reasignaciones.html  # Historial de reasignaciones del Responsable
```

---

## Arquitectura de `app.py`

Todo el código de aplicación vive en un único archivo de ~2500 líneas. Leerlo
con este mapa antes de editar:

1. **Imports y constantes globales** (líneas ~1–50)
   - `ESTADOS_PERMITIDOS`: lista de estados válidos para las denuncias.
   - `PRIORIDADES`: `["Baja", "Media", "Alta", "Crítica"]`.

2. **Helpers compartidos** (líneas ~55–420): funciones puras usadas por ambos blueprints:
   - Catálogo público, resolución de área/responsable, reasignación por desactivación,
     contadores, `registrar_seguimiento()`, `codigo_denuncia_unico()`.

3. **`create_app()`** (línea ~421): fábrica Flask. Registra dos Blueprints:
   - `public_denuncias` → prefijo `/denuncias`
   - `admin_denuncias` → prefijo `/denuncias/admin`
   - Configura DictLoader (Vercel) o FileSystemLoader (local).
   - Carga variables de Backblaze B2 en `app.config`.

4. **`register_public_routes(bp)`** (línea ~603): portal ciudadano.
5. **`register_admin_routes(bp)`** (línea ~907): panel institucional.

> Todos los endpoints son funciones anidadas dentro de los registradores.
> Los nombres de endpoint se referencian como `public_denuncias.<fn>` y
> `admin_denuncias.<fn>` en `url_for`.

---

## Flujo de usuario

### Portal ciudadano (`/denuncias/`)

1. **Registro** (`/denuncias/`) — formulario multi-paso (7 pasos):
   - Paso 1: Datos del denunciante (o registro anónimo).
   - Paso 2: Clasificación (categoría → subcategoría, cargado dinámicamente).
   - Paso 3: Ubicación en mapa interactivo (Leaflet/OSM); guarda `latitud`/`longitud`.
   - Paso 4: Fecha y hora del hecho.
   - Paso 5: Descripción detallada (mín. 30 caracteres) e involucrado.
   - Paso 6: Carga de evidencias (imágenes/PDF → Backblaze B2).
   - Paso 7: Declaraciones de veracidad y tratamiento de datos.
2. **Resultado** (`/denuncias/resultado`) — muestra el código `MMQ-XXXXXXXX` y
   ofrece descargar el comprobante PDF.
3. **Consulta** (`/denuncias/consulta`) — el ciudadano ingresa su código para ver
   el estado actual del expediente.

### Panel administrativo (`/denuncias/admin/`)

1. **Login** (`/denuncias/admin/login`) — autenticación por correo y contraseña.
2. **Dashboard** (`/denuncias/admin/dashboard`) — métricas por estado y área.
3. **Bandeja** (`/denuncias/admin/denuncias`) — lista filtrable de expedientes
   (filtros por código, estado, prioridad, área, categoría, fecha).
4. **Detalle** (`/denuncias/admin/denuncias/<id>`) — vista completa: datos del
   expediente, mapa con pin de ubicación, historial de seguimientos, archivos
   adjuntos, y formularios para cambiar estado/prioridad, asignar área, agregar nota.
5. **Reportes** (`/denuncias/admin/reportes`) — estadísticas y exportación a
   Excel o PDF.

---

## Roles y permisos

La autenticación es por sesión Flask (`session['uid']`, `session['rol']`,
`session['area_id']`). Los decoradores `@login_required` y `@roles_required(*roles)`
protegen las rutas admin.

| Rol | Acceso |
|---|---|
| `AdministradorGlobal` | Todo (sin filtro de área). Puede hacer todo lo que `Administrador` más ver cualquier expediente. |
| `Administrador` | Bandeja completa, asignar expedientes, gestionar usuarios/áreas/categorías, cambiar estados, cerrar casos. |
| `AdminCierre` | Igual que `AdministradorGlobal` en visibilidad; rol especializado para cierre de expedientes. |
| `Responsable` | Solo ve expedientes de su `area_id` (o asignados directamente a él). Puede agregar seguimientos, reasignar a otra área. |
| `Supervisor` | Solo ve expedientes de su `area_id`. Sin capacidad de edición (lectura de área). |
| `Consulta` | Lectura de toda la bandeja (sin filtro de área), sin modificar estados ni asignar. |

La visibilidad debe mantenerse **consistente en dos lugares**:
- `usuario_puede_ver_denuncia()` — para acceso a un expediente individual.
- `listar_where_base()` / `sql_y_args_bandeja_denuncias()` — para listados y exportación Excel.

Un Responsable tiene **un solo área** (`usuarios.area_id`). Desactivar un usuario
dispara `reasignar_denuncias_abiertas_por_desactivacion()` — los expedientes abiertos
asignados a él se mueven a un candidato válido.

---

## Base de datos

**Schema** (`schema.sql`, libSQL/SQLite DDL). Tablas principales:

| Tabla | Propósito |
|---|---|
| `areas` | Unidades organizativas (una sola por responsable) |
| `categorias` | Tipos de denuncia (con campo `orden`) |
| `subcategorias` | Subtipo de categoría; tiene `area_id_principal` para asignación automática |
| `usuarios` | Personal institucional; `rol`, `area_id`, `activo` |
| `denuncias` | Expedientes; incluye snapshot de `categoria`/`subcategoria` como texto |
| `seguimientos` | Auditoría append-only de cada expediente |
| `archivos_adjuntos` | Metadata de archivos subidos (nombre guardado en B2, URL, etc.) |

Invariantes clave:
- ENUMs → `TEXT + CHECK (col IN (...))`. Deben sincronizarse con `ESTADOS_PERMITIDOS`
  y `PRIORIDADES` en `app.py`.
- `denuncias.categoria` / `denuncias.subcategoria` son **snapshots de texto** al momento
  del registro; los FK `categoria_id`/`subcategoria_id` son nullable (`ON DELETE SET NULL`).
- `PRAGMA foreign_keys=ON` se activa por cada conexión en `connect_db()`.
- Código único: formato `MMQ-XXXXXXXX` (8 alfanuméricos mayúsculos), generado con
  reintentos en `codigo_denuncia_unico()`.

**`db.py` — shim de compatibilidad**:
- Traduce `%s` → `?` en tiempo de ejecución.
- Retorna filas como `dict` (compatible con `row["col"]` y `row.get()`).
- Convierte `datetime/date/time` ↔ texto ISO en params y en lectura.
- Relanza errores de constraint como `db.IntegrityError`.
- `ConnWrapper.commit()` llama `conn.commit()` (en Turso remoto envía los cambios).

No usar sintaxis MySQL exclusiva en `app.py` (p. ej., `IF()` → usar `CASE WHEN`).

---

## Integraciones

### Mapa (Leaflet + OpenStreetMap)
- Incluido vía CDN en ambas templates base (`base_public.html`, `base_admin.html`).
- En el formulario público (Paso 3): el ciudadano hace clic para fijar un pin;
  las coordenadas se guardan en campos ocultos `latitud`/`longitud`.
- En el detalle de expediente admin: si hay coordenadas, se renderiza un mapa de
  solo lectura con un marcador.

### Backblaze B2 (`cloud_storage.py`)
- API S3-compatible vía `boto3`.
- `subir_archivo_b2()`: comprime imágenes automáticamente con Pillow (calidad 75 %,
  ancho máx. 1500 px → JPEG) antes de subir. PDFs se suben sin modificar.
- Los archivos se guardan con nombre UUID (sin nombre original).
- El acceso es mediante URLs pre-firmadas (`generate_presigned_url`, 1 h de expiración).
- Variables requeridas: `B2_ACCOUNT_ID`, `B2_APPLICATION_KEY`, `B2_BUCKET_NAME`,
  `B2_ENDPOINT_URL`.

### PDF (ReportLab)
- `pdf_comprobante.py` — comprobante ciudadano en A4, paleta MMQEP (azul `#003366`).
  Incluye logo institucional desde URL CDN.
- `pdf_reporte_bandeja.py` — reporte interno (con seguimientos completos) y externo
  (solo seguimientos tipo `GESTION_REALIZADA`) de un expediente individual.

### Excel (openpyxl)
- Generado dentro de la ruta `/reportes/excel` en `app.py`.
- Aplica los mismos filtros de rol que la bandeja.

---

## Despliegue en Vercel

Vercel ejecuta la app como función Python serverless (`api/index.py` o `app.py`).

**Problema crítico con templates**: el filesystem de Vercel es de solo lectura y las
templates no quedan en el bundle si se usan con `FileSystemLoader`. La solución es:
1. Antes de cada `git push`, ejecutar `python build_templates.py` → genera
   `_templates_cache.py` con todas las templates embebidas como strings.
2. Commit del archivo generado: `git add _templates_cache.py && git commit`.
3. En `create_app()`, se intenta importar `_templates_cache.TEMPLATES` y se usa
   `DictLoader`; si no existe, cae en `FileSystemLoader` (desarrollo local).

**`vercel.json`**:
```json
{
  "buildCommand": "python build_templates.py",
  "builds": [{ "src": "app.py", "use": "@vercel/python" }],
  "routes": [{ "src": "/(.*)", "dest": "app.py" }]
}
```

> Siempre ejecutar `python build_templates.py` y commitear `_templates_cache.py`
> antes de cualquier deploy cuando se modifiquen templates.

---

## Entorno local

### Variables de entorno (`.env`)

```env
# Turso / libSQL
TURSO_DATABASE_URL=libsql://tu-base-tu-org.turso.io
TURSO_AUTH_TOKEN=<token>

# Flask
SECRET_KEY=<secreto-seguro>   # python -c "import secrets; print(secrets.token_hex(32))"
FLASK_DEBUG=1

# Aplicación
TIMEZONE=America/Guayaquil
MAX_UPLOAD_SIZE_BYTES=5242880
ALLOWED_EXTENSIONS=png,jpg,jpeg,pdf
UPLOAD_FOLDER=static/uploads

# Backblaze B2
B2_ACCOUNT_ID=
B2_APPLICATION_KEY=
B2_BUCKET_NAME=
B2_ENDPOINT_URL=
```

### Comandos

```powershell
# Crear y activar venv (Windows)
py -3.11 -m venv venv
venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Aplicar schema a Turso (una sola vez o tras cambios de schema)
turso db shell <db-name> < schema.sql

# Arrancar servidor de desarrollo → http://127.0.0.1:5000/denuncias/
python app.py

# Pre-deploy: embeber templates para Vercel
python build_templates.py
git add _templates_cache.py
```

No hay test suite, no hay linter, no hay sistema de migraciones. Para cambios de
schema: editar `schema.sql` y re-ejecutarlo contra Turso con `turso db shell`.

---

## Convenciones y decisiones de diseño

- **Todo el código fuente está en español**: comentarios, flash messages, strings de
  usuario, nombres de template. Mantener ese idioma al editar.
- **SQL parametrizado con `%s`**: el shim `db.py` lo convierte a `?`. Nunca
  interpolar input de usuario en queries.
- **Sin ORM**: SQL crudo en `app.py`, traducción de dialectos solo en `db.py`.
- **Monolito intencional**: toda la lógica de negocio en `app.py` para facilitar
  el despliegue serverless y la lectura lineal del código. No separar en módulos
  salvo que haya una razón clara.
- **Snapshot de texto en denuncias**: `denuncias.categoria` y `denuncias.subcategoria`
  se copian al registrar para que el expediente sobreviva ediciones/borrados del catálogo.
- **Una sola conexión por request**: `get_db()` la abre lazily y se cierra en
  `teardown_appcontext`.
- **Auditoría obligatoria**: todo cambio de estado, asignación o nota debe pasar por
  `registrar_seguimiento()`. El `usuario_id` es NULL para acciones del portal público.
- **`MAX_CONTENT_LENGTH` = 5× el límite por archivo**: permite subir múltiples archivos
  en un mismo request sin disparar el límite de Flask prematuramente.
- **Compatibilidad MariaDB local**: `config.py` detecta si hay `TURSO_DATABASE_URL`; si
  no, usa parámetros MariaDB/PyMySQL (solo para desarrollo sin Turso). La app en
  producción siempre usa Turso.
