from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.enums import ComplaintStatus, EscalationTarget, Priority


class ComplaintCreate(BaseModel):
    category: str = Field(min_length=2, max_length=80)
    description: str = Field(min_length=5, max_length=2000)
    image_url: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    address: str | None = None
    landmark: str | None = None
    ward: str | None = None
    priority: Priority | None = None


class StatusHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    note: str | None = None
    changed_by_role: str | None = None
    created_at: datetime


class ComplaintOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tracking_id: str | None
    citizen_id: int
    category: str
    description: str
    image_url: str | None
    before_image: str | None
    after_image: str | None
    latitude: float | None
    longitude: float | None
    address: str | None
    landmark: str | None
    ward: str | None
    priority: Priority
    status: ComplaintStatus
    ai_validated: bool
    ai_confidence: float | None
    is_duplicate: bool
    assigned_worker_id: int | None
    assigned_ngo_id: int | None
    nodal_officer_id: int | None
    work_verified: bool
    deadline: datetime | None
    rejection_reason: str | None
    close_reason: str | None
    close_requested: bool
    escalation_reason: str | None
    escalated_to: str | None
    created_at: datetime
    updated_at: datetime
    verified_at: datetime | None
    resolved_at: datetime | None
    closed_at: datetime | None


class ComplaintDetailOut(ComplaintOut):
    history: list[StatusHistoryOut] = []


class VerifyRequest(BaseModel):
    approve: bool
    note: str | None = None
    priority: Priority | None = None  # officer may set/adjust priority on approval


class AssignRequest(BaseModel):
    worker_id: int
    deadline_hours: int = Field(default=36, ge=1, le=720)
    note: str | None = None


class ImageUploadRequest(BaseModel):
    image_url: str = Field(min_length=1)
    note: str | None = None


class WorkVerifyRequest(BaseModel):
    approve: bool
    note: str | None = None


class EscalateRequest(BaseModel):
    target: EscalationTarget
    reason: str = Field(min_length=3, max_length=500)


class CloseRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


class ReopenRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)
