from sqlalchemy import Column, DateTime, ForeignKey, Integer, String

from app.database import Base
from app.utils import utcnow


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    actor_role = Column(String, nullable=True)
    action = Column(String, nullable=False)
    entity = Column(String, nullable=True)
    entity_id = Column(Integer, nullable=True)
    detail = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)
