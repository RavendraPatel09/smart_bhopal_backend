from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db
from app.models.certificate import Certificate
from app.models.user import User
from app.schemas.certificate import CertificateOut

router = APIRouter(prefix="/certificates", tags=["Certificates"])


@router.get("/me", response_model=list[CertificateOut])
def my_certificates(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return (
        db.query(Certificate)
        .filter(Certificate.user_id == user.id)
        .order_by(Certificate.issued_at.desc())
        .all()
    )


@router.get("/verify/{code}", response_model=CertificateOut)
def verify_certificate(
    code: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Public-within-app certificate verification by code."""
    cert = db.query(Certificate).filter(Certificate.code == code).first()
    if not cert:
        raise HTTPException(404, "Certificate not found")
    return cert
