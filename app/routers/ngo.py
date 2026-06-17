from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.deps import get_db, require_roles
from app.enums import Role
from app.models.user import User
from app.schemas.complaint import ComplaintDetailOut, ComplaintOut
from app.services import complaint_service

router = APIRouter(prefix="/ngo", tags=["NGO"])

_ngo = require_roles(Role.NGO)


class NgoProofRequest(BaseModel):
    after_image: str = Field(min_length=1)
    before_image: str | None = None


@router.get("/available", response_model=list[ComplaintOut])
def available(
    skip: int = 0,
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
    ngo: User = Depends(_ngo),
):
    return complaint_service.ngo_available(db, ngo, skip=skip, limit=limit)


@router.get("/adopted", response_model=list[ComplaintOut])
def adopted(
    status: str | None = None,
    skip: int = 0,
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
    ngo: User = Depends(_ngo),
):
    return complaint_service.list_complaints(
        db, assigned_ngo_id=ngo.id, status=status, skip=skip, limit=limit
    )


@router.get("/complaints/{complaint_id}", response_model=ComplaintDetailOut)
def detail(complaint_id: int, db: Session = Depends(get_db), ngo: User = Depends(_ngo)):
    complaint = complaint_service.get_or_404(db, complaint_id)
    complaint_service.assert_can_view(ngo, complaint)
    return complaint


@router.post("/complaints/{complaint_id}/adopt", response_model=ComplaintOut)
def adopt(complaint_id: int, db: Session = Depends(get_db), ngo: User = Depends(_ngo)):
    complaint = complaint_service.get_or_404(db, complaint_id)
    return complaint_service.ngo_adopt(db, ngo, complaint)


@router.post("/complaints/{complaint_id}/submit-proof", response_model=ComplaintOut)
def submit_proof(
    complaint_id: int,
    payload: NgoProofRequest,
    db: Session = Depends(get_db),
    ngo: User = Depends(_ngo),
):
    complaint = complaint_service.get_or_404(db, complaint_id)
    return complaint_service.ngo_submit_proof(
        db, ngo, complaint, after_image=payload.after_image, before_image=payload.before_image
    )
