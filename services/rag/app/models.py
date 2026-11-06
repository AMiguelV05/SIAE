"""Tablas de base de datos del backend RAG y de asistencia estudiantil.

Las tablas pequeñas de secciones, subsecciones, usuarios y administradores son
una estructura local provisional. Permiten ejecutar este módulo antes de que el
equipo web o móvil entregue el catálogo completo y los módulos de autenticación.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Section(Base):
    __tablename__ = "sections"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False)
    type = Column(String(20), nullable=False, default="division")
    is_active = Column(Boolean, nullable=False, default=True)

    __table_args__ = (CheckConstraint("type IN ('division', 'secretaria')", name="ck_sections_type"),)


class Subsection(Base):
    __tablename__ = "subsections"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    section_id = Column(String(36), ForeignKey("sections.id"), nullable=True)
    name = Column(String(100), nullable=False)
    type = Column(String(20), nullable=False, default="unidad")
    code = Column(String(15), nullable=True, unique=True)
    is_active = Column(Boolean, nullable=False, default=True)


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    code = Column(String(12), nullable=True, unique=True)
    name = Column(String(50), nullable=False, default="Usuario local")
    lastname = Column(String(50), nullable=False, default="")
    email = Column(String(150), nullable=True, unique=True)
    phone = Column(String(20), nullable=True)
    password = Column(String(255), nullable=True)
    id_carrera = Column(String(36), ForeignKey("subsections.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    type = Column(String(20), nullable=False, default="licenciatura")
    semester = Column(Integer, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    theme_preference = Column(String(10), nullable=False, default="system")
    avatar_url = Column(Text, nullable=True)


class Admin(Base):
    __tablename__ = "admins"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(50), nullable=False)
    lastname = Column(String(50), nullable=False)
    email = Column(String(150), nullable=False, unique=True)
    phone = Column(String(20), nullable=True)
    password = Column(String(255), nullable=True)
    role = Column(String(20), nullable=False, default="admin")
    subsections_id = Column(String(36), ForeignKey("subsections.id"), nullable=True)
    created_by = Column(String(36), ForeignKey("admins.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    is_active = Column(Boolean, nullable=False, default=True)


class Doc(Base):
    __tablename__ = "docs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    subsections_id = Column(String(36), ForeignKey("subsections.id"), nullable=True)
    uploaded_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    title = Column(String(200), nullable=False)
    file_name = Column(String(200), nullable=False)
    storage_in = Column(String(500), nullable=False)
    file_size = Column(BigInteger, nullable=True)
    doc_hashed = Column(String(64), nullable=False, unique=True, index=True)
    rag_status = Column(String(20), nullable=False, default="pendiente", index=True)
    uploaded_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    # Al eliminar una fuente también se eliminan sus fragmentos indexados.
    chunks = relationship(
        "DocumentChunk", back_populates="document", cascade="all, delete-orphan"
    )


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), ForeignKey("docs.id", ondelete="CASCADE"), nullable=False, index=True)
    subsection_id = Column(String(36), ForeignKey("subsections.id"), nullable=True)
    content = Column(Text, nullable=False)
    metadata_json = Column(Text, nullable=False, default="{}")
    category = Column(String(50), nullable=True, index=True)
    chunk_index = Column(Integer, nullable=False)
    page_number = Column(Integer, nullable=True)
    embedding_json = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    document = relationship("Doc", back_populates="chunks")


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(50), nullable=True)
    status = Column(String(20), nullable=False, default="active", index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    messages = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan"
    )


class Message(Base):
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    conversation_id = Column(String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    admin_id = Column(String(36), ForeignKey("admins.id"), nullable=True)
    content = Column(Text, nullable=False)
    file = Column(Text, nullable=True)
    sender = Column(String(10), nullable=False)
    extracted_features = Column(Text, nullable=True)
    embedding_json = Column(Text, nullable=True)
    prompt_tokens = Column(Integer, nullable=False, default=0)
    completion_tokens = Column(Integer, nullable=False, default=0)
    total_tokens = Column(BigInteger, nullable=False, default=0)
    response_time_seconds = Column(Float, nullable=False, default=0.0)
    sent_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, index=True)

    __table_args__ = (CheckConstraint("sender IN ('user', 'system', 'admin')", name="ck_messages_sender"),)

    conversation = relationship("Conversation", back_populates="messages")
    sources = relationship(
        "MessageSource", back_populates="message", cascade="all, delete-orphan"
    )


class MessageSource(Base):
    __tablename__ = "message_sources"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    message_id = Column(String(36), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = Column(String(36), ForeignKey("docs.id"), nullable=False)
    document_chunk_id = Column(String(36), ForeignKey("document_chunks.id"), nullable=False)
    similarity_score = Column(Float, nullable=False)
    rank = Column(Integer, nullable=False)

    message = relationship("Message", back_populates="sources")


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    message_id = Column(String(36), ForeignKey("messages.id"), nullable=True)
    # Chat independiente de soporte humano. message_id conserva la pregunta RAG
    # que lo originó, mientras que este chat sirve para el seguimiento entre usuario y administrador.
    conversation_id = Column(String(36), ForeignKey("conversations.id"), nullable=True, index=True)
    subsection_id = Column(String(36), ForeignKey("subsections.id"), nullable=True)
    admin_id = Column(String(36), ForeignKey("admins.id"), nullable=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="pendiente", index=True)
    file = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
