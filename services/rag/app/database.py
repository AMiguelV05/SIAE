"""Configuración de SQLAlchemy para el backend independiente de SIAE."""

import json
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()  # Carga la configuración guardada en .env.

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./siae_local.db")  # Dirección de la base de datos.

engine_options = {"pool_pre_ping": True}  # Opciones para comprobar conexiones antes de reutilizarlas.
if DATABASE_URL.startswith("sqlite"):
    engine_options["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **engine_options)  # Administra las conexiones con la base.
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)  # Crea sesiones de trabajo.
Base = declarative_base()  # Clase base de los modelos que representan tablas.


if DATABASE_URL.startswith("sqlite"):
    # Este evento configura cada conexión nueva de SQLite.
    @event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(connection, _record):
        # SQLite no aplica claves foráneas en una conexión nueva si no se habilitan aquí.
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def get_db():
    # Dependencia de FastAPI: entrega una sesión y la cierra al terminar la solicitud.
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    # Prepara las tablas y adapta algunas columnas de bases de versiones anteriores.
    # Importa los modelos para que SQLAlchemy registre todas las tablas antes de create_all.
    import app.models  # noqa: F401 — se importa para registrar los modelos.

    Base.metadata.create_all(bind=engine)
    # ``create_all`` no agrega columnas a tablas existentes de SQLite o PostgreSQL.
    chunk_columns = {column["name"] for column in inspect(engine).get_columns("document_chunks")}
    if "metadata_json" not in chunk_columns:
        # Actualización ligera para bases existentes; no elimina ni recrea sus datos.
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE document_chunks ADD COLUMN metadata_json TEXT NOT NULL DEFAULT '{}'"))

    # Algunas bases locales son anteriores al chat de soporte separado entre usuario y administrador.
    ticket_columns = {column["name"] for column in inspect(engine).get_columns("tickets")}
    if "conversation_id" not in ticket_columns:
        with engine.begin() as connection:
            connection.execute(text(
                "ALTER TABLE tickets ADD COLUMN conversation_id VARCHAR(36) "
                "REFERENCES conversations(id)"
            ))

    # Completa los metadatos de los fragmentos existentes sin regenerar sus vectores.
    # Así, las fuentes anteriores también se buscan por título, URL, tipo y ubicación.
    from app.models import Doc, DocumentChunk
    from app.ingestion import derive_source_metadata

    with SessionLocal() as db:
        rows = (
            db.query(DocumentChunk, Doc)
            .join(Doc, DocumentChunk.document_id == Doc.id)
            .all()
        )
        for chunk, doc in rows:
            source = doc.storage_in or ""
            suffix = os.path.splitext(source)[1].lower()
            source_type = suffix.lstrip(".") or ("html" if source.startswith(("http://", "https://")) else "local_file")
            try:
                metadata = json.loads(chunk.metadata_json or "{}")
            except (TypeError, ValueError):
                metadata = {}
            base_metadata = {
                "source_title": doc.title,
                "source_url": source if source.startswith(("http://", "https://")) else None,
                "source_name": doc.file_name,
                "source_type": source_type,
                "category": chunk.category,
                "page_number": chunk.page_number,
                "chunk_index": chunk.chunk_index,
            }
            for key, value in base_metadata.items():
                metadata.setdefault(key, value)
            if "source_scope" not in metadata or "recency_date" not in metadata:
                derived = derive_source_metadata(doc.title, source, chunk.content)
                for key, value in derived.items():
                    if value is not None:
                        metadata.setdefault(key, value)
            chunk.metadata_json = json.dumps(
                metadata,
                ensure_ascii=False,
                separators=(",", ":"),
            )
        if rows:
            db.commit()
