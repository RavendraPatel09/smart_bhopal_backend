"""Authentication & user provisioning service."""
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.enums import Role
from app.models.user import User
from app.security import hash_password, verify_password


def _check_unique(db: Session, phone: str, email: str | None, exclude_id: int | None = None):
    q = db.query(User).filter(User.phone == phone)
    if exclude_id:
        q = q.filter(User.id != exclude_id)
    if q.first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Phone number already registered")
    if email:
        q = db.query(User).filter(User.email == email)
        if exclude_id:
            q = q.filter(User.id != exclude_id)
        if q.first():
            raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")


def register_citizen(db: Session, *, name: str, phone: str, password: str,
                     email: str | None = None, ward: str | None = None) -> User:
    _check_unique(db, phone, email)
    user = User(
        name=name,
        phone=phone,
        email=email,
        password=hash_password(password),
        role=Role.CITIZEN.value,
        ward=ward,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_user(db: Session, *, name: str, phone: str, password: str, role: Role,
                email: str | None = None, ward: str | None = None,
                organization: str | None = None) -> User:
    _check_unique(db, phone, email)
    user = User(
        name=name,
        phone=phone,
        email=email,
        password=hash_password(password),
        role=role.value if isinstance(role, Role) else str(role),
        ward=ward,
        organization=organization,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, *, phone: str, password: str) -> User:
    user = db.query(User).filter(User.phone == phone).first()
    if not user or not verify_password(password, user.password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid phone number or password")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account is deactivated")
    return user
