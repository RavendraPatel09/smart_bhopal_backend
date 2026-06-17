from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.deps import get_db, require_roles
from app.enums import ComplaintStatus, Role
from app.models.user import User
from app.schemas.complaint import (
    CloseRequest,
    ComplaintDetailOut,
    ComplaintOut,
    EscalateRequest,
)
from app.services import analytics_service, complaint_service

router = APIRouter(prefix="/authority", tags=["Higher Authority"])

_authority = require_roles(Role.HIGHER_AUTHORITY, Role.SUPER_ADMIN)


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), user: User = Depends(_authority)):
    return analytics_service.overview(db)


@router.get("/complaints", response_model=list[ComplaintOut])
def all_complaints(
    status: str | None = None,
    ward: str | None = None,
    category: str | None = None,
    priority: str | None = None,
    skip: int = 0,
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(_authority),
):
    return complaint_service.list_complaints(
        db, status=status, ward=ward, category=category, priority=priority,
        skip=skip, limit=limit,
    )


@router.get("/complaints/{complaint_id}", response_model=ComplaintDetailOut)
def detail(complaint_id: int, db: Session = Depends(get_db), user: User = Depends(_authority)):
    return complaint_service.get_or_404(db, complaint_id)


@router.get("/escalated", response_model=list[ComplaintOut])
def escalated(
    skip: int = 0,
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(_authority),
):
    return complaint_service.list_complaints(
        db, status=ComplaintStatus.ESCALATED.value, skip=skip, limit=limit
    )


@router.get("/analytics/areas")
def areas(db: Session = Depends(get_db), user: User = Depends(_authority)):
    return analytics_service.by_area(db)


@router.get("/analytics/top-issues")
def top_issues(db: Session = Depends(get_db), user: User = Depends(_authority)):
    return analytics_service.top_issues(db)


@router.get("/analytics/ward-performance")
def ward_performance(db: Session = Depends(get_db), user: User = Depends(_authority)):
    return analytics_service.ward_performance(db)


@router.get("/analytics/worker-performance")
def worker_performance(db: Session = Depends(get_db), user: User = Depends(_authority)):
    return analytics_service.worker_performance(db)


@router.get("/analytics/ngo-performance")
def ngo_performance(db: Session = Depends(get_db), user: User = Depends(_authority)):
    return analytics_service.ngo_performance(db)


@router.get("/analytics/heatmap")
def heatmap(db: Session = Depends(get_db), user: User = Depends(_authority)):
    return analytics_service.heatmap(db)


@router.get("/analytics/engagement")
def engagement(db: Session = Depends(get_db), user: User = Depends(_authority)):
    return analytics_service.citizen_engagement(db)


@router.post("/complaints/{complaint_id}/escalate", response_model=ComplaintOut)
def take_escalation_action(
    complaint_id: int,
    payload: EscalateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(_authority),
):
    complaint = complaint_service.get_or_404(db, complaint_id)
    return complaint_service.escalate(
        db, user, complaint, target=payload.target, reason=payload.reason
    )


@router.post("/complaints/{complaint_id}/close", response_model=ComplaintOut)
def force_close(
    complaint_id: int,
    payload: CloseRequest,
    db: Session = Depends(get_db),
    user: User = Depends(_authority),
):
    complaint = complaint_service.get_or_404(db, complaint_id)
    return complaint_service.officer_close(db, user, complaint, payload.reason)
