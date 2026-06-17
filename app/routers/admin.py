from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.deps import get_db, require_roles
from app.enums import Role
from app.models.audit import AuditLog
from app.models.reference import Category, Ward
from app.models.user import User
from app.schemas.admin import (
    AuditLogOut,
    CategoryCreate,
    CategoryOut,
    CreateUserRequest,
    UpdateUserRequest,
    WardCreate,
    WardOut,
)
from app.schemas.auth import UserOut
from app.schemas.complaint import ComplaintOut
from app.services import audit_service, auth_service, complaint_service

router = APIRouter(prefix="/admin", tags=["Super Admin"])

_admin = require_roles(Role.SUPER_ADMIN)


# ----------------------------- User management ----------------------------- #
@router.post("/users", response_model=UserOut, status_code=201)
def create_user(
    payload: CreateUserRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(_admin),
):
    user = auth_service.create_user(
        db, name=payload.name, phone=payload.phone, password=payload.password,
        role=payload.role, email=payload.email, ward=payload.ward,
        organization=payload.organization,
    )
    audit_service.log(db, action="user.create", user_id=admin.id, actor_role=admin.role,
                      entity="user", entity_id=user.id, detail=user.role)
    db.commit()
    return user


@router.get("/users", response_model=list[UserOut])
def list_users(
    role: Role | None = None,
    skip: int = 0,
    limit: int = Query(default=100, le=500),
    db: Session = Depends(get_db),
    admin: User = Depends(_admin),
):
    q = db.query(User)
    if role:
        q = q.filter(User.role == role.value)
    return q.order_by(User.id).offset(skip).limit(limit).all()


@router.get("/users/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: Session = Depends(get_db), admin: User = Depends(_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    return user


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UpdateUserRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    data = payload.model_dump(exclude_unset=True)
    if "role" in data and data["role"] is not None:
        data["role"] = data["role"].value if isinstance(data["role"], Role) else data["role"]
    for key, value in data.items():
        setattr(user, key, value)
    audit_service.log(db, action="user.update", user_id=admin.id, actor_role=admin.role,
                      entity="user", entity_id=user.id, detail=str(list(data.keys())))
    db.commit()
    db.refresh(user)
    return user


# ------------------------------ Ward management ----------------------------- #
@router.post("/wards", response_model=WardOut, status_code=201)
def create_ward(payload: WardCreate, db: Session = Depends(get_db), admin: User = Depends(_admin)):
    if db.query(Ward).filter((Ward.name == payload.name) | (Ward.code == payload.code)).first():
        raise HTTPException(409, "Ward with this name or code already exists")
    ward = Ward(name=payload.name, code=payload.code, zone=payload.zone)
    db.add(ward)
    db.commit()
    db.refresh(ward)
    return ward


@router.get("/wards", response_model=list[WardOut])
def list_wards(db: Session = Depends(get_db), admin: User = Depends(_admin)):
    return db.query(Ward).order_by(Ward.name).all()


# --------------------------- Category management ---------------------------- #
@router.post("/categories", response_model=CategoryOut, status_code=201)
def create_category(
    payload: CategoryCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(_admin),
):
    if db.query(Category).filter(Category.name == payload.name).first():
        raise HTTPException(409, "Category already exists")
    cat = Category(
        name=payload.name, description=payload.description,
        default_priority=payload.default_priority, sla_hours=payload.sla_hours,
    )
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


@router.get("/categories", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db), admin: User = Depends(_admin)):
    return db.query(Category).order_by(Category.name).all()


# ------------------------------ Oversight ----------------------------------- #
@router.get("/complaints", response_model=list[ComplaintOut])
def all_complaints(
    status: str | None = None,
    ward: str | None = None,
    skip: int = 0,
    limit: int = Query(default=100, le=500),
    db: Session = Depends(get_db),
    admin: User = Depends(_admin),
):
    return complaint_service.list_complaints(
        db, status=status, ward=ward, skip=skip, limit=limit
    )


@router.get("/audit-logs", response_model=list[AuditLogOut])
def audit_logs(
    skip: int = 0,
    limit: int = Query(default=100, le=500),
    db: Session = Depends(get_db),
    admin: User = Depends(_admin),
):
    return (
        db.query(AuditLog)
        .order_by(AuditLog.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
