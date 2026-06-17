from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.deps import get_db, require_roles
from app.enums import Role
from app.models.user import User
from app.schemas.auth import UserOut
from app.schemas.complaint import (
    AssignRequest,
    CloseRequest,
    ComplaintDetailOut,
    ComplaintOut,
    EscalateRequest,
    VerifyRequest,
    WorkVerifyRequest,
)
from app.services import complaint_service

router = APIRouter(prefix="/nodal", tags=["Nodal Officer"])

_officer = require_roles(Role.NODAL_OFFICER)


@router.get("/complaints", response_model=list[ComplaintOut])
def queue(
    status: str | None = None,
    ward: str | None = None,
    category: str | None = None,
    priority: str | None = None,
    skip: int = 0,
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
    officer: User = Depends(_officer),
):
    return complaint_service.list_complaints(
        db, status=status, ward=ward, category=category, priority=priority,
        skip=skip, limit=limit,
    )


@router.get("/complaints/{complaint_id}", response_model=ComplaintDetailOut)
def detail(complaint_id: int, db: Session = Depends(get_db), officer: User = Depends(_officer)):
    return complaint_service.get_or_404(db, complaint_id)


@router.get("/workers", response_model=list[UserOut])
def workers(
    ward: str | None = None,
    db: Session = Depends(get_db),
    officer: User = Depends(_officer),
):
    q = db.query(User).filter(User.role == Role.WORKER.value, User.is_active.is_(True))
    if ward:
        q = q.filter(User.ward == ward)
    return q.order_by(User.name).all()


@router.post("/complaints/{complaint_id}/verify", response_model=ComplaintOut)
def verify(
    complaint_id: int,
    payload: VerifyRequest,
    db: Session = Depends(get_db),
    officer: User = Depends(_officer),
):
    complaint = complaint_service.get_or_404(db, complaint_id)
    return complaint_service.verify(
        db, officer, complaint, approve=payload.approve, note=payload.note,
        priority=payload.priority,
    )


@router.post("/complaints/{complaint_id}/assign", response_model=ComplaintOut)
def assign(
    complaint_id: int,
    payload: AssignRequest,
    db: Session = Depends(get_db),
    officer: User = Depends(_officer),
):
    complaint = complaint_service.get_or_404(db, complaint_id)
    return complaint_service.assign(
        db, officer, complaint, worker_id=payload.worker_id,
        deadline_hours=payload.deadline_hours, note=payload.note,
    )


@router.post("/complaints/{complaint_id}/verify-work", response_model=ComplaintOut)
def verify_work(
    complaint_id: int,
    payload: WorkVerifyRequest,
    db: Session = Depends(get_db),
    officer: User = Depends(_officer),
):
    complaint = complaint_service.get_or_404(db, complaint_id)
    return complaint_service.verify_work(
        db, officer, complaint, approve=payload.approve, note=payload.note
    )


@router.post("/complaints/{complaint_id}/escalate", response_model=ComplaintOut)
def escalate(
    complaint_id: int,
    payload: EscalateRequest,
    db: Session = Depends(get_db),
    officer: User = Depends(_officer),
):
    complaint = complaint_service.get_or_404(db, complaint_id)
    return complaint_service.escalate(
        db, officer, complaint, target=payload.target, reason=payload.reason
    )


@router.post("/complaints/{complaint_id}/close", response_model=ComplaintOut)
def close(
    complaint_id: int,
    payload: CloseRequest,
    db: Session = Depends(get_db),
    officer: User = Depends(_officer),
):
    complaint = complaint_service.get_or_404(db, complaint_id)
    return complaint_service.officer_close(db, officer, complaint, payload.reason)
