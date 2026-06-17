from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.database import Base
from app.utils import utcnow


class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(Integer, primary_key=True, index=True)
    tracking_id = Column(String, unique=True, index=True, nullable=True)

    citizen_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    category = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=False)

    image_url = Column(String, nullable=True)      # citizen submitted photo
    before_image = Column(String, nullable=True)    # worker / ngo before-work proof
    after_image = Column(String, nullable=True)     # worker / ngo after-work proof

    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    address = Column(String, nullable=True)
    landmark = Column(String, nullable=True)
    ward = Column(String, nullable=True, index=True)

    priority = Column(String, nullable=False, default="medium", index=True)
    status = Column(String, nullable=False, default="submitted", index=True)

    # AI verification layer
    ai_validated = Column(Boolean, nullable=False, default=False)
    ai_confidence = Column(Float, nullable=True)
    is_duplicate = Column(Boolean, nullable=False, default=False)

    # Assignment / ownership
    assigned_worker_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    assigned_ngo_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    nodal_officer_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    # Quality assurance
    work_verified = Column(Boolean, nullable=False, default=False)
    work_verified_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    deadline = Column(DateTime, nullable=True)
    rejection_reason = Column(String, nullable=True)
    close_reason = Column(String, nullable=True)
    close_requested = Column(Boolean, nullable=False, default=False)
    escalation_reason = Column(String, nullable=True)
    escalated_to = Column(String, nullable=True)

    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)
    verified_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)

    citizen = relationship("User", foreign_keys=[citizen_id])
    worker = relationship("User", foreign_keys=[assigned_worker_id])
    ngo = relationship("User", foreign_keys=[assigned_ngo_id])
    officer = relationship("User", foreign_keys=[nodal_officer_id])

    history = relationship(
        "StatusHistory",
        back_populates="complaint",
        cascade="all, delete-orphan",
        order_by="StatusHistory.id",
    )


class StatusHistory(Base):
    __tablename__ = "status_history"

    id = Column(Integer, primary_key=True, index=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id"), nullable=False, index=True)
    status = Column(String, nullable=False)
    note = Column(String, nullable=True)
    changed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    changed_by_role = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)

    complaint = relationship("Complaint", back_populates="history")
