import uuid
from sqlalchemy import Column, String, Integer, Enum, ForeignKey, Date, Text
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP, JSONB
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from app.core.database import Base

class ML_Models(Base):
    __tablename__ = "ml_models"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    model_name = Column(String(100), nullable=False)
    version = Column(Integer, nullable=False)
    parameters = Column(JSONB, nullable=True)
    details = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=True)

    demand_forecasts = relationship("Demand_Forecasts", back_populates="ml_model")


class Academic_Periods(Base):
    __tablename__ = "academic_periods"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    name = Column(String(100), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)

    demand_forecasts = relationship("Demand_Forecasts", back_populates="academic_period")


class Topics(Base):
    __tablename__ = "topics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    subsection_id = Column(UUID(as_uuid=True), ForeignKey("subsections.id"), nullable=False)
    name = Column(String(100), nullable=False)
    embedding = Column(Vector(), nullable=True)

    subsection = relationship("Subsection")
    demand_forecasts = relationship("Demand_Forecasts", back_populates="topic")


class Demand_Forecasts(Base):
    __tablename__ = "demand_forecasts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    model_id = Column(UUID(as_uuid=True), ForeignKey("ml_models.id"), nullable=False)
    topic_id = Column(UUID(as_uuid=True), ForeignKey("topics.id"), nullable=False)
    academic_period_id = Column(UUID(as_uuid=True), ForeignKey("academic_periods.id"), nullable=False)
    target_date = Column(Date, nullable=False)
    predicted_volume = Column(Integer, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=True)

    ml_model = relationship("ML_Models", back_populates="demand_forecasts")
    topic = relationship("Topics", back_populates="demand_forecasts")
    academic_period = relationship("Academic_Periods", back_populates="demand_forecasts")


class Docs(Base):
    __tablename__ = "docs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    subsections_id = Column(UUID(as_uuid=True), ForeignKey("subsections.id"), nullable=False)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("admins.id"), nullable=False)
    title = Column(String(200), nullable=False)
    file_name = Column(String(200), nullable=False)
    storage_in = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    doc_hashed = Column(Text, nullable=False)
    rag_status = Column(Enum("pendiente", "procesando", "vectorizado", "error", name="rag_status_enum"), default="pendiente")
    uploaded_at = Column(TIMESTAMP(timezone=True), nullable=True)

    chunks = relationship("Document_Chunks", back_populates="doc")
    message_sources = relationship("Message_Sources", back_populates="doc")


class Document_Chunks(Base):
    __tablename__ = "document_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    document_id = Column(UUID(as_uuid=True), ForeignKey("docs.id"), nullable=False)
    subsection_id = Column(UUID(as_uuid=True), ForeignKey("subsections.id"), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(Enum("titulacion", "servicio_social", "ceneval", "practicas", "articulos", name="chunk_category_enum"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    embedding = Column(Vector(), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=True)

    doc = relationship("Docs", back_populates="chunks")
    message_sources = relationship("Message_Sources", back_populates="chunk")
