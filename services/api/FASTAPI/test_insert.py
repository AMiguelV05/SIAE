from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv

# Al importar app.models, Python ejecuta el __init__.py y registra las 17 tablas en memoria
import app.models
from app.models.user import Admins

# Cargar variables de entorno desde el archivo .env
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# Crear el motor de SQLAlchemy
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def registrar_admin_prueba():
    db = SessionLocal()
    try:
        print("Iniciando registro de administrador en la base de datos...")
        
        # Instanciamos el objeto Admins con los campos exactos de tu modelo
        nuevo_admin = Admins(
            name="Jose",
            lastname="Gallardo",
            email="admin.siae@example.com",
            password="password123",
            rol="superadmin"
        )
        
        # Guardamos en la base de datos
        db.add(nuevo_admin)
        db.commit()
        db.refresh(nuevo_admin)
        
        print(f"¡Administrador registrado exitosamente con ID: {nuevo_admin.id}!")
        
        # Verificamos el total de administradores
        total_admins = db.query(Admins).count()
        print(f"Total de administradores en la base de datos: {total_admins}")

    except Exception as e:
        print(f"Ocurrió un error durante el registro: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    registrar_admin_prueba()