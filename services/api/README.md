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
En teoria deberia de ser esta 
postgresql://postgres.riqnxqfuzdpxnvnirqhg:[YOUR-PASSWORD]@aws-0-us-east-2.pooler.supabase.com:6543/postgres
 igual puedes revisarlo en supabase https://supabase.com/dashboard/project/riqnxqfuzdpxnvnirqhg

SI ALGO NO ABRE O NO FUNCIONA FAVOR DE DECIRMELO 

ATTE: Valentín 
