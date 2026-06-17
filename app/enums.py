"""Domain enumerations shared across models, schemas and services."""
import enum


class Role(str, enum.Enum):
    CITIZEN = "citizen"
    WORKER = "worker"
    NGO = "ngo"
    NODAL_OFFICER = "nodal_officer"
    HIGHER_AUTHORITY = "higher_authority"
    SUPER_ADMIN = "super_admin"


class ComplaintStatus(str, enum.Enum):
    SUBMITTED = "submitted"       # citizen submitted, awaiting verification
    VERIFIED = "verified"         # nodal officer approved
    REJECTED = "rejected"         # nodal officer rejected
    ASSIGNED = "assigned"         # worker / ngo assigned
    IN_PROGRESS = "in_progress"   # work started (before image uploaded)
    RESOLVED = "resolved"         # work done + proof uploaded, awaiting feedback
    CLOSED = "closed"             # citizen satisfied / officer closed
    ESCALATED = "escalated"       # escalated to NGO / higher authority
    REOPENED = "reopened"         # citizen not satisfied, reopened


class Priority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EMERGENCY = "emergency"


class NotificationType(str, enum.Enum):
    COMPLAINT_SUBMITTED = "complaint_submitted"
    COMPLAINT_VERIFIED = "complaint_verified"
    COMPLAINT_REJECTED = "complaint_rejected"
    COMPLAINT_ASSIGNED = "complaint_assigned"
    COMPLAINT_IN_PROGRESS = "complaint_in_progress"
    COMPLAINT_RESOLVED = "complaint_resolved"
    COMPLAINT_CLOSED = "complaint_closed"
    COMPLAINT_REOPENED = "complaint_reopened"
    COMPLAINT_ESCALATED = "complaint_escalated"
    BADGE_EARNED = "badge_earned"
    CERTIFICATE_EARNED = "certificate_earned"


# Badge thresholds (inclusive lower bound) -> badge name.
# Ordered ascending; see rewards_service.badge_for_points.
BADGE_LEVELS = [
    (0, "Green Starter"),
    (51, "Active Citizen"),
    (151, "Cleanliness Champion"),
    (301, "Swachh Hero"),
    (501, "Smart Bhopal Ambassador"),
]


class EscalationTarget(str, enum.Enum):
    NGO = "ngo"
    HIGHER_AUTHORITY = "higher_authority"
