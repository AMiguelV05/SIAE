import uuid
from sqlalchemy import Column, String, Boolean, Enum, ForeignKey, SmallInteger, Text
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
from sqlalchemy.orm import relationship
from app.core.database import Base

class Section(Base):
    __tablename__ = "sections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    name = Column(String(100), nullable=False)
    type = Column(Enum("division", "secretaria", name="section_type_enum"), nullable=False)
    is_active = Column(Boolean, default=True)

    subsections = relationship("Subsection", back_populates="section")


class Subsection(Base):
    __tablename__ = "subsections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    section_id = Column(UUID(as_uuid=True), ForeignKey("sections.id"), nullable=False)
    name = Column(String(100), nullable=False)
    type = Column(Enum("carrera", "departamento", "coordinacion", "unidad", name="subsection_type_enum"), nullable=False)
    code = Column(String(15), unique=True, nullable=False)
    is_active = Column(Boolean, default=True)

    section = relationship("Section", back_populates="subsections")
    posts = relationship("Posts", back_populates="subsection")


class Posts(Base):
    __tablename__ = "posts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    subsections_id = Column(UUID(as_uuid=True), ForeignKey("subsections.id"), nullable=False)
    author = Column(Enum("aspirante", "licenciatura", "maestria", "doctorado", "egresado", name="user_type_enum"), nullable=False)
    user_type = Column(String(50), nullable=True)
    semester_obj = Column(SmallInteger, nullable=True)
    title = Column(String(100), nullable=False)
    content = Column(Text, nullable=False)
    file = Column(Text, nullable=True)
    published_at = Column(TIMESTAMP(timezone=True), nullable=True)
    expired_at = Column(TIMESTAMP(timezone=True), nullable=True)
    pinned = Column(Boolean, default=False)

    subsection = relationship("Subsection", back_populates="posts")
