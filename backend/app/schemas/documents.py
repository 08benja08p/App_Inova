from typing import Optional, List, Any
from pydantic import BaseModel, Field
from datetime import datetime


class DocumentCreateResponse(BaseModel):
    id: str
    status: str
    createdAt: datetime


class DocumentDetailResponse(BaseModel):
    id: str
    status: str
    docType: Optional[str] = None
    languageDetected: Optional[str] = None
    createdAt: datetime
    updatedAt: Optional[datetime] = None


class EntityResponse(BaseModel):
    id: str
    type: str
    value: str
    confidence: float
    page: Optional[int] = None


class KeywordResponse(BaseModel):
    keyword: str
    score: float


class BBox(BaseModel):
    x: float
    y: float
    w: float
    h: float


class TextBlock(BaseModel):
    page: int
    text: str
    bbox: Optional[BBox] = None
    confidence: float = 0.0


class InsightIssue(BaseModel):
    severity: str
    title: str
    detail: str
    field: Optional[str] = None


class DocumentInsightsResponse(BaseModel):
    compliance: List[InsightIssue] = Field(default_factory=list)
    spellcheck: List[InsightIssue] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
