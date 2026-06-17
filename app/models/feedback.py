from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Boolean

from app.database import Base
from app.utils import utcnow


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id"), nullable=False, index=True)
    citizen_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    satisfied = Column(Boolean, nullable=False)
    rating = Column(Integer, nullable=True)  # 1..5
    comment = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)
