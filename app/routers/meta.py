"""Read-only reference data for frontend dropdowns (categories, wards, enums)."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db
from app.enums import ComplaintStatus, Priority, Role
from app.models.reference import Category, Ward
from app.models.user import User
from app.schemas.admin import CategoryOut, WardOut

router = APIRouter(prefix="/meta", tags=["Reference Data"])


@router.get("/categories", response_model=list[CategoryOut])
def categories(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(Category).order_by(Category.name).all()


@router.get("/wards", response_model=list[WardOut])
def wards(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(Ward).order_by(Ward.name).all()


@router.get("/enums")
def enums(user: User = Depends(get_current_user)):
    return {
        "roles": [r.value for r in Role],
        "statuses": [s.value for s in ComplaintStatus],
        "priorities": [p.value for p in Priority],
    }
