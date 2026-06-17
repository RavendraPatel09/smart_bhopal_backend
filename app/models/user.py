from sqlalchemy import Boolean, Column, DateTime, Integer, String

from app.database import Base
from app.utils import utcnow


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=True)
    phone = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    role = Column(String, nullable=False, default="citizen", index=True)

    ward = Column(String, nullable=True, index=True)
    organization = Column(String, nullable=True)  # NGO name / dept for officials

    points = Column(Integer, nullable=False, default=0)
    badge = Column(String, nullable=False, default="Green Starter")

    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)
