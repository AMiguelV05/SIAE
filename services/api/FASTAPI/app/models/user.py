import uuid
from sqlalchemy import Column, String, Boolean, Enum, ForeignKey, SmallInteger, Text
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
from sqlalchemy.orm import relationship
from app.core.database import Base

class Users(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    code = Column(String(12), unique=True, nullable=True)
    name = Column(String(50), nullable=False)
    lastname = Column(String(50), nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    phone = Column(String(20), nullable=True)
    password = Column(String(255), nullable=False)
    id_carrera = Column(UUID(as_uuid=True), ForeignKey("subsections.id"), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=True)
    deleted_at = Column(TIMESTAMP(timezone=True), nullable=True)
    type = Column(Enum("aspirante", "licenciatura", "maestria", "doctorado", "egresado", name="user_role_enum"), nullable=False)
    semester = Column(SmallInteger, nullable=True)
    is_active = Column(Boolean, default=True)
    theme_preference = Column(Enum("light", "dark", "system", name="theme_enum"), default="system")
    avatar_url = Column(Text, nullable=True)

    conversations = relationship("Conversations", back_populates="user")
    tickets = relationship("Tickets", back_populates="user")


class Admins(Base):
    __tablename__ = "admins"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    name = Column(String(50), nullable=False)
    lastname = Column(String(50), nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    phone = Column(String(20), nullable=True)
    password = Column(String(255), nullable=False)
    rol = Column(Enum("superadmin", "admin", name="admin_role_enum"), nullable=False)
    subsections_id = Column(UUID(as_uuid=True), ForeignKey("subsections.id"), nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("admins.id"), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)

    logs = relationship("Admin_Logs", back_populates="admin")
    messages = relationship("Messages", back_populates="admin")
    tickets = relationship("Tickets", back_populates="admin")


class Admin_Logs(Base):
    __tablename__ = "admin_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    admin_id = Column(UUID(as_uuid=True), ForeignKey("admins.id"), nullable=False)
    action = Column(String(50), nullable=False)
    entity_affected = Column(String(50), nullable=False)
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    details = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=True)

    admin = relationship("Admins", back_populates="logs")
