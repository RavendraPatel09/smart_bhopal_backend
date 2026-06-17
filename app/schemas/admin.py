from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.enums import Role


class CreateUserRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=10, max_length=15)
    password: str = Field(min_length=6, max_length=128)
    role: Role
    email: EmailStr | None = None
    ward: str | None = None
    organization: str | None = None


class UpdateUserRequest(BaseModel):
    name: str | None = None
    ward: str | None = None
    organization: str | None = None
    is_active: bool | None = None
    role: Role | None = None


class WardCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    code: str = Field(min_length=1, max_length=40)
    zone: str | None = None


class WardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str
    zone: str | None


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: str | None = None
    default_priority: str = "medium"
    sla_hours: int = Field(default=36, ge=1, le=720)


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    default_priority: str
    sla_hours: int


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None
    actor_role: str | None
    action: str
    entity: str | None
    entity_id: int | None
    detail: str | None
    created_at: datetime
