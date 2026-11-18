# Panel administrativo SIAE

El frontend React consume la API FastAPI ubicada en `SIAE/services/api/FASTAPI` y usa PostgreSQL en Supabase.

## Preparar FastAPI y Supabase

Abre una terminal de PowerShell en `SIAE/services/api/FASTAPI` y ejecuta:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edita `.env` y coloca la URL de conexión de Supabase en `DATABASE_URL`. Usa el pooler del puerto `6543` y el controlador `postgresql+psycopg2://`. No subas ese archivo al repositorio ni compartas su contraseña.

Configura `SIAE_SUPERADMIN_EMAIL`, `SIAE_SUPERADMIN_PASSWORD` y, opcionalmente, `SIAE_SUPERADMIN_NAME`. La contraseña debe tener al menos 12 caracteres. Inicializa las tablas y crea la cuenta raíz:

```powershell
python init_db.py
python test_insert.py
```

`test_insert.py` ahora crea una cuenta superadministradora solo con las variables privadas del `.env` y almacena su contraseña con scrypt. Si el correo ya existe, no modifica la cuenta.

Inicia la API en el puerto que usa el proxy de Vite:

```powershell
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

El proyecto conserva los 17 modelos originales y agrega `admin_access_requests` para guardar el flujo de aprobación. Ejecuta `python init_db.py` para crear esa tabla nueva en Supabase; vuelve a ejecutarlo si se incorpora otro cambio de esquema.

## Iniciar el panel

En una segunda terminal, desde la raíz de este proyecto:

```powershell
npm install
npm run dev
```

Abre `http://localhost:5174`. Vite reenvía las llamadas `/api` al servidor FastAPI en `http://127.0.0.1:8000`.

## Flujo de autenticación

- El inicio de sesión consulta la tabla `admins` y crea una cookie `HttpOnly` de ocho horas.
- Las contraseñas nuevas se almacenan con scrypt. Las cuentas heredadas en texto plano se convierten a hash al iniciar sesión correctamente.
- Las solicitudes recibidas se guardan en Supabase con contraseña cifrada. El superadministrador puede aprobarlas como administrador de área o rechazarlas.
- El modelo actual solo define `superadmin` y `admin`; por eso el permiso de administrador de área corresponde a `admin`.
- La API valida el rol de superadministrador para consultar solicitudes, revisarlas y listar cuentas.

En producción configura `COOKIE_SECURE=true`, HTTPS y el origen publicado en `CORS_ORIGINS`. Las sesiones actuales se guardan en memoria y se invalidan al reiniciar FastAPI.
