"""Pydantic models for API request/response."""
from pydantic import BaseModel, Field
from typing import Literal


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    model: Literal["gemini"] = "gemini"
    use_cot: bool = False


class SourceDoc(BaseModel):
    doc_id: str = ""
    title: str = ""
    content: str = ""
    source: str = "statpearls"
    score: float = 0.0


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceDoc] = []
    model: str
    is_confident: bool = True


class IngestRequest(BaseModel):
    limit: int | None = Field(None, description="Max chunks to ingest (None = all)")


class IngestResponse(BaseModel):
    status: str
    chunks_ingested: int


class HealthResponse(BaseModel):
    status: str
    qdrant: str
    version: str = "0.1.0"
