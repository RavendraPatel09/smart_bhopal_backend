from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.deps import get_db, require_roles
from app.enums import ComplaintStatus, Role
from app.models.user import User
from app.schemas.complaint import ComplaintDetailOut, ComplaintOut, ImageUploadRequest
from app.services import complaint_service

router = APIRouter(prefix="/worker", tags=["Worker"])

_worker = require_roles(Role.WORKER)


@router.get("/tasks", response_model=list[ComplaintOut])
def my_tasks(
    status: str | None = Query(default=None, description="Filter by status"),
    skip: int = 0,
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
    worker: User = Depends(_worker),
):
    return complaint_service.list_complaints(
        db, assigned_worker_id=worker.id, status=status, skip=skip, limit=limit
    )


@router.get("/tasks/{complaint_id}", response_model=ComplaintDetailOut)
def task_detail(complaint_id: int, db: Session = Depends(get_db), worker: User = Depends(_worker)):
    complaint = complaint_service.get_or_404(db, complaint_id)
    complaint_service.assert_can_view(worker, complaint)
    return complaint


@router.post("/tasks/{complaint_id}/accept", response_model=ComplaintOut)
def accept_task(complaint_id: int, db: Session = Depends(get_db), worker: User = Depends(_worker)):
    complaint = complaint_service.get_or_404(db, complaint_id)
    return complaint_service.worker_accept(db, worker, complaint)


@router.post("/tasks/{complaint_id}/start", response_model=ComplaintOut)
def start_task(
    complaint_id: int,
    payload: ImageUploadRequest,
    db: Session = Depends(get_db),
    worker: User = Depends(_worker),
):
    complaint = complaint_service.get_or_404(db, complaint_id)
    return complaint_service.start_work(db, worker, complaint, before_image=payload.image_url)


@router.post("/tasks/{complaint_id}/complete", response_model=ComplaintOut)
def complete_task(
    complaint_id: int,
    payload: ImageUploadRequest,
    db: Session = Depends(get_db),
    worker: User = Depends(_worker),
):
    complaint = complaint_service.get_or_404(db, complaint_id)
    return complaint_service.complete_work(db, worker, complaint, after_image=payload.image_url)
