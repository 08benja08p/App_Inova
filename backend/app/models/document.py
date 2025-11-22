from sqlalchemy import Column, String, Integer, DateTime, Float, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from ..core.db import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True)
    filename = Column(String, nullable=False)
    mime = Column(String, nullable=False)
    size = Column(Integer, nullable=False)
    doc_type = Column(String, nullable=True)
    language_detected = Column(String, nullable=True)
    status = Column(String, default="queued")
    storage_path = Column(String, nullable=False)
    html_preview = Column(Text, nullable=True)  # Stores HTML content for preview
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    entities = relationship(
        "Entity", back_populates="document", cascade="all, delete-orphan"
    )
    keywords = relationship(
        "Keyword", back_populates="document", cascade="all, delete-orphan"
    )
    logs = relationship(
        "ProcessingLog", back_populates="document", cascade="all, delete-orphan"
    )


class Entity(Base):
    __tablename__ = "entities"

    id = Column(String, primary_key=True)
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    type = Column(String, nullable=False)
    value = Column(String, nullable=False)
    confidence = Column(Float, default=0.0)
    page = Column(Integer, nullable=True)

    document = relationship("Document", back_populates="entities")


class Keyword(Base):
    __tablename__ = "keywords"

    id = Column(String, primary_key=True)
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    keyword = Column(String, nullable=False)
    score = Column(Float, default=0.0)

    document = relationship("Document", back_populates="keywords")


class ProcessingLog(Base):
    __tablename__ = "processing_logs"

    id = Column(String, primary_key=True)
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    step = Column(String, nullable=False)
    payload = Column(Text, nullable=True)  # JSON serialized as text
    success = Column(Integer, default=1)
    duration_ms = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("Document", back_populates="logs")
