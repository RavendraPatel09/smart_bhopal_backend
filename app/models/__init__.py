"""Import all models so SQLAlchemy mappers register on the shared Base."""
from app.models.user import User
from app.models.complaint import Complaint, StatusHistory
from app.models.feedback import Feedback
from app.models.notification import Notification
from app.models.certificate import Certificate
from app.models.reference import Ward, Category
from app.models.audit import AuditLog

__all__ = [
    "User",
    "Complaint",
    "StatusHistory",
    "Feedback",
    "Notification",
    "Certificate",
    "Ward",
    "Category",
    "AuditLog",
]
