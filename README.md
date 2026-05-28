# Sistema de quejas y denuncias MMQEP

Aplicación **Flask** sobre **Turso / libSQL** (réplica embebida) para el
registro ciudadano de quejas/denuncias y la gestión interna institucional.
Interfaz con **HTML, CSS y JS** estáticos, sin SPA. Uso **local**.

## Requisitos

- **Python 3.11+**
- [Turso CLI](https://docs.turso.tech/cli/installation) y una cuenta Turso

## Ambiente virtual

**Windows**

```powershell
py -3.11 -m venv venv
venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

**Linux / macOS**

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## Configuración (`.env`)

No hay valores hardcodeados: toda la configuración vive en `.env` (no se
versiona). Copie la plantilla y complete los valores:

```powershell
copy .env.example .env
```

Genere un `SECRET_KEY` seguro:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

Variables relevantes: `TURSO_DATABASE_URL`, `TURSO_AUTH_TOKEN`,
`TURSO_LOCAL_DB_PATH`, `SECRET_KEY`, `FLASK_DEBUG`, `TIMEZONE`,
`MAX_UPLOAD_SIZE_BYTES`, `ALLOWED_EXTENSIONS`, `UPLOAD_FOLDER`.

## Base de datos (Turso / libSQL)

La aplicación usa **réplica embebida**: un archivo libSQL local
(`TURSO_LOCAL_DB_PATH`, p. ej. `local_replica.db`) que sincroniza con la base
Turso en la nube. El archivo local se crea y sincroniza automáticamente al
arrancar; **el esquema se carga una sola vez en Turso**:

```powershell
# 1. Autenticar (una vez)
turso auth login

# 2. Crear la base (omitir si ya existe) e inspeccionarla
turso db create mmqep-denuncias
turso db show mmqep-denuncias            # muestra la URL libsql://
turso db tokens create mmqep-denuncias   # genera el TURSO_AUTH_TOKEN

# 3. Cargar el esquema + datos semilla en la base Turso (en la nube)
turso db shell mmqep-denuncias < schema.sql

# 4. Verificar
turso db shell mmqep-denuncias "SELECT name FROM sqlite_master WHERE type='table';"
turso db shell mmqep-denuncias "SELECT correo, rol FROM usuarios;"
```

Copie la URL (`turso db show`) y el token (`turso db tokens create`) a las
variables `TURSO_DATABASE_URL` y `TURSO_AUTH_TOKEN` del `.env`.

**Usuario administrador inicial** (semilla de `schema.sql`):

- Correo: `admin@mmqep.local`
- Contraseña provisional: **`Admin123!`**
  Cámbiela apenas ingrese creando otro administrador y desactivando este.

## Ejecución local

Desde esta carpeta, con el venv activado y el `.env` configurado:

```powershell
python app.py
```

Luego:

- Portal ciudadano: <http://127.0.0.1:5000/denuncias/>
- Administración: <http://127.0.0.1:5000/denuncias/admin/login>

En el primer arranque se crea el archivo de réplica local y se sincroniza
desde Turso. Si no hay red, la app sigue funcionando contra la réplica local
y reintenta sincronizar en el siguiente `commit`/arranque.

## Archivos cargados

Se guardan bajo `static/uploads/`. Mantenga ese directorio con permisos de
escritura.

## Roles

| Rol           | Alcance principal                                       |
|---------------|---------------------------------------------------------|
| Administrador | Bandeja completa, asignaciones, usuarios, estados, cierre |
| Responsable   | Solo expedientes **asignados**; gestión y estados acotados |
| Consulta      | Solo lectura sobre denuncias y reportes dentro de su vista |

Los **informes Excel** aplican los mismos límites de visibilidad que la bandeja.

## Auditoría (`seguimientos`)

Se registra el alta pública sin `usuario_id` interno y las acciones de personal
(reasignaciones, cambios de estado, observaciones internas y gestiones).
