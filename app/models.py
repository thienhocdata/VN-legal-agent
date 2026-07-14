from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class Provenance(StrEnum):
    USER_PROVIDED = "user_provided"
    DOCUMENT_EXTRACTED = "document_extracted"
    STAFF_ENTERED = "staff_entered"
    AGENT_INFERRED = "agent_inferred"
    USER_CONFIRMED = "user_confirmed"
    PROFESSIONAL_CONFIRMED = "professional_confirmed"


class CaseStatus(StrEnum):
    DRAFT = "draft"
    INTAKE_IN_PROGRESS = "intake_in_progress"
    RESEARCH_READY = "research_ready"
    RESEARCH_IN_PROGRESS = "research_in_progress"
    ANALYSIS_READY = "analysis_ready"
    REVIEW_REQUIRED = "review_required"
    ACTION_READY = "action_ready"
    CLOSED = "closed"


class Role(StrEnum):
    CASE_PARTICIPANT = "case_participant"
    CASE_STAFF = "case_staff"
    PROFESSIONAL_REVIEWER = "professional_reviewer"


class CaseCreate(BaseModel):
    purpose: str = Field(min_length=3, max_length=2000)
    tenant_id: str = Field(default="demo", min_length=1, max_length=100)
    actor_id: str = Field(default="demo-user", min_length=1, max_length=100)
    actor_role: Role = Role.CASE_PARTICIPANT
    property_ids: list[str] = Field(default_factory=list, max_length=20)


class IntakeRequest(BaseModel):
    actor_id: str = "demo-user"
    actor_role: Role = Role.CASE_PARTICIPANT
    text: str = Field(min_length=1, max_length=10000)


class FactCreate(BaseModel):
    key: str = Field(min_length=1, max_length=100)
    value: Any
    provenance: Provenance
    actor_id: str = Field(min_length=1, max_length=100)
    source_id: str | None = None
    method: str = "manual"


class FactConfirm(BaseModel):
    actor_id: str
    actor_role: Role
    value: Any | None = None


class ContextRequest(BaseModel):
    relevant_date: str | None = None
    locality: str | None = None
    jurisdiction: str = "Vietnam"
    legal_subject: str = "individual"


class ResearchRequest(BaseModel):
    query: str = Field(min_length=3, max_length=2000)


class ReviewRequest(BaseModel):
    actor_id: str
    actor_role: Role
    decision: str = Field(pattern="^(approved|changes_requested|rejected)$")
    rationale: str = Field(min_length=3, max_length=4000)


class Artifact(BaseModel):
    id: str
    type: str
    version: int
    status: str
    data: dict[str, Any]
    created_at: str
    stale: bool = False


class CaseView(BaseModel):
    id: str
    tenant_id: str
    purpose: str
    status: CaseStatus
    version: int
    property_ids: list[str]
    created_at: str
    updated_at: str
    facts: list[dict[str, Any]] = []
    artifacts: list[Artifact] = []

