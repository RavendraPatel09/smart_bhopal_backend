from sqlalchemy import Column, DateTime, ForeignKey, Integer, String

from app.database import Base
from app.utils import utcnow


class Certificate(Base):
    __tablename__ = "certificates"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    code = Column(String, unique=True, index=True, nullable=False)
    title = Column(String, nullable=False)
    badge = Column(String, nullable=False)
    points_snapshot = Column(Integer, nullable=False, default=0)
    issued_at = Column(DateTime, nullable=False, default=utcnow)
