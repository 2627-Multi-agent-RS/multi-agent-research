# app/schemas/research.py
from typing import Literal

from pydantic import BaseModel, Field


class ResearchPlan(BaseModel):
    topic: str
    sub_queries: list[str] = Field(min_length=1, max_length=5)
    expected_metrics: list[str] = Field(default_factory=list)


class Finding(BaseModel):
    claim: str
    evidence: str
    source_url: str
    source_title: str
    published_at: str | None = None


class ResearcherOutput(BaseModel):
    status: Literal["complete", "partial", "failed"]
    findings: list[Finding]
    search_queries: list[str]
    limitations: list[str] = Field(default_factory=list)


class FollowUpRequest(BaseModel):
    questions: list[str]
    preferred_sources: list[str] = Field(default_factory=list)


class AnalystOutput(BaseModel):
    status: Literal["complete", "needs_more_research"]
    confidence_score: float = Field(ge=0.0, le=1.0)
    verified_findings: list[Finding]
    conclusions: list[str]
    insights: list[str]
    conflicts: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    follow_up_request: FollowUpRequest | None = None


class Citation(BaseModel):
    id: int
    title: str
    url: str
    snippet: str


class WriterOutput(BaseModel):
    status: Literal["complete", "partial"]
    title: str
    content: str
    citations: list[Citation]
    warnings: list[str] = Field(default_factory=list)
