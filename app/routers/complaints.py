from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db, require_roles
from app.enums import Role
from app.models.user import User
from app.schemas.complaint import (
    CloseRequest,
    ComplaintCreate,
    ComplaintDetailOut,
    ComplaintOut,
    ReopenRequest,
)
from app.schemas.feedback import FeedbackCreate, FeedbackOut
from app.services import complaint_service

router = APIRouter(prefix="/complaints", tags=["Complaints"])


@router.post("", response_model=ComplaintOut, status_code=201)
def create_complaint(
    payload: ComplaintCreate,
    db: Session = Depends(get_db),
    citizen: User = Depends(require_roles(Role.CITIZEN)),
):
    return complaint_service.create_complaint(db, citizen, payload)


@router.get("/mine", response_model=list[ComplaintOut])
def my_complaints(
    status: str | None = Query(default=None),
    skip: int = 0,
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
    citizen: User = Depends(require_roles(Role.CITIZEN)),
):
    return complaint_service.list_complaints(
        db, citizen_id=citizen.id, status=status, skip=skip, limit=limit
    )


@router.get("/track/{tracking_id}", response_model=ComplaintDetailOut)
def track_complaint(
    tracking_id: str,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    complaint = complaint_service.get_by_tracking(db, tracking_id)
    complaint_service.assert_can_view(current, complaint)
    return complaint


@router.get("/{complaint_id}", response_model=ComplaintDetailOut)
def complaint_detail(
    complaint_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    complaint = complaint_service.get_or_404(db, complaint_id)
    complaint_service.assert_can_view(current, complaint)
    return complaint


@router.post("/{complaint_id}/feedback", response_model=FeedbackOut, status_code=201)
def give_feedback(
    complaint_id: int,
    payload: FeedbackCreate,
    db: Session = Depends(get_db),
    citizen: User = Depends(require_roles(Role.CITIZEN)),
):
    complaint = complaint_service.get_or_404(db, complaint_id)
    return complaint_service.submit_feedback(db, citizen, complaint, payload)


@router.post("/{complaint_id}/close-request", response_model=ComplaintOut)
def request_close(
    complaint_id: int,
    payload: CloseRequest,
    db: Session = Depends(get_db),
    citizen: User = Depends(require_roles(Role.CITIZEN)),
):
    complaint = complaint_service.get_or_404(db, complaint_id)
    return complaint_service.request_close(db, citizen, complaint, payload.reason)


@router.post("/{complaint_id}/reopen", response_model=ComplaintOut)
def reopen_complaint(
    complaint_id: int,
    payload: ReopenRequest,
    db: Session = Depends(get_db),
    citizen: User = Depends(require_roles(Role.CITIZEN)),
):
    complaint = complaint_service.get_or_404(db, complaint_id)
    return complaint_service.reopen(db, citizen, complaint, payload.reason)
