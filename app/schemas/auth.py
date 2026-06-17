from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.enums import Role


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=10, max_length=15)
    password: str = Field(min_length=6, max_length=128)
    email: EmailStr | None = None
    ward: str | None = None


class LoginRequest(BaseModel):
    phone: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: Role
    user_id: int


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    phone: str
    email: EmailStr | None = None
    role: Role
    ward: str | None = None
    organization: str | None = None
    points: int
    badge: str
    is_active: bool
