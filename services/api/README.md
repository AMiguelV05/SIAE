SIAE - API Backend (FastAPI)

Este servicio contiene la arquitectura del backend, la conexión a la base de datos PostgreSQL en Supabase y las definiciones de los 17 modelos de SQLAlchemy.

Requisitos Previos

- Python 3.11+
- Git

Pasos para que funcione en local

1. Crear y activar el entorno virtual

En la terminal, ubicado en la carpeta `services/api/`:

```bash
# Crear el entorno virtual
python -m venv venv

# Activar en Windows (PowerShell):
.\venv\Scripts\Activate.ps1

# Activar en Linux / macOS:
source venv/bin/activate
```

2. se deben de instalar las dependencias usa el siguiente comando
pip install -r requirements.txt

3. Configurar las variables del entorno
Copia el archivo de ejemplo .env.example y renómbralo a .env:

```bash
cp .env.example .env
```

Abre el archivo .env y configura la variable DATABASE_URL con la cadena de conexión de Supabase (usando el pooler en el puerto 6543)
Nota importante: La cadena que te da Supabase por defecto empieza con postgresql://, pero debes asegurarte de agregarle +psycopg2 para que SQLAlchemy reconozca el driver de conexión. Debe quedar con esta estructura:

DATABASE_URL=postgresql+psycopg2://postgres.riqnxqfuzdpxnvnirqhg:[YOUR-PASSWORD]@[aws-0-us-east-2.pooler.supabase.com:6543/postgres](https://aws-0-us-east-2.pooler.supabase.com:6543/postgres) 

Link de la API en supabase https://supabase.com/dashboard/project/riqnxqfuzdpxnvnirqhg

SI ALGO NO ABRE O NO FUNCIONA FAVOR DE DECIRMELO 

ATTE: Valentín 
