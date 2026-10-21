import uuid
from sqlalchemy import Column, String, Integer, Float, Boolean, Enum, ForeignKey, Interval, SmallInteger, Text
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP, JSONB
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from app.core.database import Base

class Conversations(Base):
    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title = Column(String(50), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=True)
    updated_at = Column(TIMESTAMP(timezone=True), nullable=True)
    status = Column(Enum("active", "archived", "deleted", name="conversation_status_enum"), default="active")

    user = relationship("Users", back_populates="conversations")
    messages = relationship("Messages", back_populates="conversation")
    feedback = relationship("Feedback", back_populates="conversation")


class Messages(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False)
    admin_id = Column(UUID(as_uuid=True), ForeignKey("admins.id"), nullable=True)
    content = Column(Text, nullable=False)
    file = Column(Text, nullable=True)
    sender = Column(Enum("user", "system", "admin", name="sender_enum"), nullable=False)
    extracted_features = Column(JSONB, nullable=True)
    embedding = Column(Vector(), nullable=True)
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    response_time = Column(Interval, nullable=True)
    sent_at = Column(TIMESTAMP(timezone=True), nullable=True)

    conversation = relationship("Conversations", back_populates="messages")
    admin = relationship("Admins", back_populates="messages")
    sources = relationship("Message_Sources", back_populates="message")
    tickets = relationship("Tickets", back_populates="message")


class Message_Sources(Base):
    __tablename__ = "message_sources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id"), nullable=False)
    document_id = Column(UUID(as_uuid=True), ForeignKey("docs.id"), nullable=False)
    document_chunk_id = Column(UUID(as_uuid=True), ForeignKey("document_chunks.id"), nullable=False)
    similarity_score = Column(Float, nullable=True)
    rank = Column(Integer, nullable=True)

    message = relationship("Messages", back_populates="sources")
    doc = relationship("Docs", back_populates="message_sources")
    chunk = relationship("Document_Chunks", back_populates="message_sources")


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False)
    is_resolved = Column(Boolean, nullable=False)
    rating = Column(SmallInteger, nullable=False)
    comment = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=True)

    conversation = relationship("Conversations", back_populates="feedback")


class Tickets(Base):
    __tablename__ = "tickets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id"), nullable=False)
    subsection_id = Column(UUID(as_uuid=True), ForeignKey("subsections.id"), nullable=False)
    admin_id = Column(UUID(as_uuid=True), ForeignKey("admins.id"), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    status = Column(Enum("pendiente", "en_proceso", "finalizado", name="ticket_status_enum"), default="pendiente")
    file = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=True)
    updated_at = Column(TIMESTAMP(timezone=True), nullable=True)
    resolved_at = Column(TIMESTAMP(timezone=True), nullable=True)

    message = relationship("Messages", back_populates="tickets")
    admin = relationship("Admins", back_populates="tickets")
    user = relationship("Users", back_populates="tickets")
    subsection = relationship("Subsection")
