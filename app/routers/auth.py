from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserOut
from app.security import create_access_token
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Auth"])


def _token_for(user: User) -> TokenResponse:
    token = create_access_token(subject=user.id, role=user.role)
    return TokenResponse(access_token=token, role=user.role, user_id=user.id)


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    """Public self-registration (citizens only)."""
    user = auth_service.register_citizen(
        db, name=payload.name, phone=payload.phone, password=payload.password,
        email=payload.email, ward=payload.ward,
    )
    return _token_for(user)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """JSON login with phone + password."""
    user = auth_service.authenticate(db, phone=payload.phone, password=payload.password)
    return _token_for(user)


@router.post("/token", response_model=TokenResponse, include_in_schema=True)
def login_oauth(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """OAuth2 password flow (Swagger 'Authorize'); send phone as `username`."""
    user = auth_service.authenticate(db, phone=form.username, password=form.password)
    return _token_for(user)


@router.get("/me", response_model=UserOut)
def me(current: User = Depends(get_current_user)):
    return current
