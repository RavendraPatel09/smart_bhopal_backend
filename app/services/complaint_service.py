"""Complaint lifecycle: the heart of the grievance redressal state machine.

Master flow (architecture diagram):
    Citizen submit -> AI validation -> Nodal verify -> Worker/NGO assign ->
    work execution -> proof upload -> Nodal work-verify -> Citizen feedback -> Closed
"""
from datetime import timedelta

from fastapi import HTTPException, status as http_status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.config import settings
from app.enums import (
    ComplaintStatus,
    EscalationTarget,
    NotificationType,
    Priority,
    Role,
)
from app.models.complaint import Complaint, StatusHistory
from app.models.feedback import Feedback
from app.models.user import User
from app.services import audit_service, notification_service, rewards_service
from app.utils import gen_tracking_id, utcnow

S = ComplaintStatus


# --------------------------------------------------------------------------- #
# Internal helpers
# --------------------------------------------------------------------------- #
def _add_history(db: Session, complaint: Complaint, new_status: str,
                 note: str | None, actor: User | None) -> None:
    db.add(StatusHistory(
        complaint_id=complaint.id,
        status=new_status,
        note=note,
        changed_by_id=actor.id if actor else None,
        changed_by_role=actor.role if actor else None,
    ))


def _conflict(msg: str):
    return HTTPException(http_status.HTTP_409_CONFLICT, msg)


def _not_found():
    return HTTPException(http_status.HTTP_404_NOT_FOUND, "Complaint not found")


def _forbidden(msg: str = "You cannot act on this complaint"):
    return HTTPException(http_status.HTTP_403_FORBIDDEN, msg)


def _require_status(complaint: Complaint, *allowed: ComplaintStatus):
    allowed_values = {s.value for s in allowed}
    if complaint.status not in allowed_values:
        raise _conflict(
            f"Action not allowed while complaint is '{complaint.status}'. "
            f"Expected one of: {', '.join(sorted(allowed_values))}."
        )


def _run_ai_validation(db: Session, complaint: Complaint) -> None:
    """Mock AI/image verification layer (architecture box 5.1)."""
    has_image = bool(complaint.image_url)
    desc_ok = len((complaint.description or "").strip()) >= 10
    complaint.ai_validated = bool(has_image and desc_ok)
    complaint.ai_confidence = 0.92 if complaint.ai_validated else 0.40

    # Duplicate detection: same citizen + category + address with an open complaint.
    if complaint.address:
        exists = (
            db.query(Complaint.id)
            .filter(
                Complaint.citizen_id == complaint.citizen_id,
                Complaint.category == complaint.category,
                Complaint.address == complaint.address,
                Complaint.id != complaint.id,
                Complaint.status.notin_([S.CLOSED.value, S.REJECTED.value]),
            )
            .first()
        )
        complaint.is_duplicate = exists is not None


def _notify_role(db: Session, role: Role, *, type: NotificationType, title: str,
                 message: str, complaint_id: int, ward: str | None = None) -> None:
    q = db.query(User).filter(User.role == role.value, User.is_active.is_(True))
    if ward:
        # Prefer officials in the same ward, but fall back to all if none match.
        ward_users = q.filter(User.ward == ward).all()
        users = ward_users if ward_users else q.all()
    else:
        users = q.all()
    for u in users:
        notification_service.notify(
            db, user_id=u.id, type=type, title=title, message=message,
            complaint_id=complaint_id,
        )


# --------------------------------------------------------------------------- #
# Lookups
# --------------------------------------------------------------------------- #
def get_or_404(db: Session, complaint_id: int) -> Complaint:
    c = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not c:
        raise _not_found()
    return c


def assert_can_view(user: User, complaint: Complaint) -> None:
    """Authorize read access to a single complaint based on role / ownership."""
    role = user.role
    if role in (Role.NODAL_OFFICER.value, Role.HIGHER_AUTHORITY.value, Role.SUPER_ADMIN.value):
        return
    if role == Role.CITIZEN.value and complaint.citizen_id == user.id:
        return
    if role == Role.WORKER.value and complaint.assigned_worker_id == user.id:
        return
    if role == Role.NGO.value and (
        complaint.assigned_ngo_id == user.id
        or (complaint.escalated_to == EscalationTarget.NGO.value
            and complaint.status == S.ESCALATED.value)
    ):
        return
    raise _forbidden("You are not allowed to view this complaint")


def get_by_tracking(db: Session, tracking_id: str) -> Complaint:
    c = db.query(Complaint).filter(Complaint.tracking_id == tracking_id).first()
    if not c:
        raise _not_found()
    return c


def list_complaints(db: Session, *, status: str | None = None, ward: str | None = None,
                    category: str | None = None, priority: str | None = None,
                    escalated_to: str | None = None, assigned_worker_id: int | None = None,
                    assigned_ngo_id: int | None = None, citizen_id: int | None = None,
                    skip: int = 0, limit: int = 50) -> list[Complaint]:
    q = db.query(Complaint)
    if status:
        q = q.filter(Complaint.status == status)
    if ward:
        q = q.filter(Complaint.ward == ward)
    if category:
        q = q.filter(Complaint.category == category)
    if priority:
        q = q.filter(Complaint.priority == priority)
    if escalated_to:
        q = q.filter(Complaint.escalated_to == escalated_to)
    if assigned_worker_id is not None:
        q = q.filter(Complaint.assigned_worker_id == assigned_worker_id)
    if assigned_ngo_id is not None:
        q = q.filter(Complaint.assigned_ngo_id == assigned_ngo_id)
    if citizen_id is not None:
        q = q.filter(Complaint.citizen_id == citizen_id)
    return (
        q.order_by(Complaint.created_at.desc(), Complaint.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


# --------------------------------------------------------------------------- #
# Citizen actions
# --------------------------------------------------------------------------- #
def create_complaint(db: Session, citizen: User, data) -> Complaint:
    priority = (data.priority.value if isinstance(data.priority, Priority)
                else data.priority) or Priority.MEDIUM.value
    complaint = Complaint(
        citizen_id=citizen.id,
        category=data.category,
        description=data.description,
        image_url=data.image_url,
        latitude=data.latitude,
        longitude=data.longitude,
        address=data.address,
        landmark=data.landmark,
        ward=data.ward or citizen.ward,
        priority=priority,
        status=S.SUBMITTED.value,
    )
    db.add(complaint)
    db.flush()  # assigns complaint.id

    complaint.tracking_id = gen_tracking_id(complaint.id)
    _run_ai_validation(db, complaint)
    _add_history(db, complaint, S.SUBMITTED.value, "Complaint registered", citizen)

    rewards_service.award_points(db, citizen, settings.POINTS_ON_SUBMIT)
    notification_service.notify(
        db, user_id=citizen.id, type=NotificationType.COMPLAINT_SUBMITTED,
        title="Complaint registered",
        message=f"Your complaint {complaint.tracking_id} has been registered successfully.",
        complaint_id=complaint.id,
    )
    _notify_role(
        db, Role.NODAL_OFFICER, type=NotificationType.COMPLAINT_SUBMITTED,
        title="New complaint to verify",
        message=f"Complaint {complaint.tracking_id} awaits verification.",
        complaint_id=complaint.id, ward=complaint.ward,
    )
    audit_service.log(db, action="complaint.create", user_id=citizen.id,
                      actor_role=citizen.role, entity="complaint",
                      entity_id=complaint.id, detail=complaint.tracking_id)
    db.commit()
    db.refresh(complaint)
    return complaint


def submit_feedback(db: Session, citizen: User, complaint: Complaint, payload) -> Feedback:
    if complaint.citizen_id != citizen.id:
        raise _forbidden("Only the complaint owner can give feedback")
    _require_status(complaint, S.RESOLVED)

    fb = Feedback(
        complaint_id=complaint.id,
        citizen_id=citizen.id,
        satisfied=payload.satisfied,
        rating=payload.rating,
        comment=payload.comment,
    )
    db.add(fb)

    if payload.satisfied:
        complaint.status = S.CLOSED.value
        complaint.closed_at = utcnow()
        complaint.close_reason = "Citizen satisfied"
        _add_history(db, complaint, S.CLOSED.value, "Citizen satisfied", citizen)
        rewards_service.award_points(db, citizen, settings.POINTS_ON_CLOSED)
        notification_service.notify(
            db, user_id=citizen.id, type=NotificationType.COMPLAINT_CLOSED,
            title="Complaint closed",
            message=f"Complaint {complaint.tracking_id} is resolved and closed. Thank you!",
            complaint_id=complaint.id,
        )
    else:
        complaint.status = S.REOPENED.value
        _add_history(db, complaint, S.REOPENED.value,
                     payload.comment or "Citizen not satisfied", citizen)
        notification_service.notify(
            db, user_id=citizen.id, type=NotificationType.COMPLAINT_REOPENED,
            title="Complaint reopened",
            message=f"Complaint {complaint.tracking_id} reopened for rework.",
            complaint_id=complaint.id,
        )
        if complaint.nodal_officer_id:
            notification_service.notify(
                db, user_id=complaint.nodal_officer_id,
                type=NotificationType.COMPLAINT_REOPENED,
                title="Complaint reopened",
                message=f"Complaint {complaint.tracking_id} needs reassignment.",
                complaint_id=complaint.id,
            )
    audit_service.log(db, action="complaint.feedback", user_id=citizen.id,
                      actor_role=citizen.role, entity="complaint",
                      entity_id=complaint.id,
                      detail=f"satisfied={payload.satisfied}")
    db.commit()
    db.refresh(fb)
    return fb


def request_close(db: Session, citizen: User, complaint: Complaint, reason: str) -> Complaint:
    if complaint.citizen_id != citizen.id:
        raise _forbidden("Only the complaint owner can request closure")
    if complaint.status in (S.CLOSED.value, S.REJECTED.value):
        raise _conflict("Complaint is already closed")
    complaint.close_requested = True
    complaint.close_reason = reason
    _add_history(db, complaint, complaint.status, f"Close requested: {reason}", citizen)
    if complaint.nodal_officer_id:
        notification_service.notify(
            db, user_id=complaint.nodal_officer_id,
            type=NotificationType.COMPLAINT_CLOSED,
            title="Closure requested",
            message=f"Citizen requested closing {complaint.tracking_id}: {reason}",
            complaint_id=complaint.id,
        )
    else:
        _notify_role(db, Role.NODAL_OFFICER, type=NotificationType.COMPLAINT_CLOSED,
                     title="Closure requested",
                     message=f"Citizen requested closing {complaint.tracking_id}.",
                     complaint_id=complaint.id, ward=complaint.ward)
    audit_service.log(db, action="complaint.close_request", user_id=citizen.id,
                      actor_role=citizen.role, entity="complaint",
                      entity_id=complaint.id, detail=reason)
    db.commit()
    db.refresh(complaint)
    return complaint


def reopen(db: Session, citizen: User, complaint: Complaint, reason: str) -> Complaint:
    if complaint.citizen_id != citizen.id:
        raise _forbidden("Only the complaint owner can reopen")
    _require_status(complaint, S.CLOSED)
    complaint.status = S.REOPENED.value
    complaint.closed_at = None
    complaint.close_requested = False
    _add_history(db, complaint, S.REOPENED.value, reason, citizen)
    _notify_role(db, Role.NODAL_OFFICER, type=NotificationType.COMPLAINT_REOPENED,
                 title="Complaint reopened",
                 message=f"Complaint {complaint.tracking_id} reopened: {reason}",
                 complaint_id=complaint.id, ward=complaint.ward)
    audit_service.log(db, action="complaint.reopen", user_id=citizen.id,
                      actor_role=citizen.role, entity="complaint",
                      entity_id=complaint.id, detail=reason)
    db.commit()
    db.refresh(complaint)
    return complaint


# --------------------------------------------------------------------------- #
# Nodal officer actions
# --------------------------------------------------------------------------- #
def verify(db: Session, officer: User, complaint: Complaint, *, approve: bool,
           note: str | None = None, priority: Priority | None = None) -> Complaint:
    _require_status(complaint, S.SUBMITTED)
    complaint.nodal_officer_id = officer.id
    complaint.verified_at = utcnow()

    if approve:
        complaint.status = S.VERIFIED.value
        if priority is not None:
            complaint.priority = priority.value if isinstance(priority, Priority) else priority
        _add_history(db, complaint, S.VERIFIED.value, note or "Verified by nodal officer", officer)
        notification_service.notify(
            db, user_id=complaint.citizen_id, type=NotificationType.COMPLAINT_VERIFIED,
            title="Complaint verified",
            message=f"Complaint {complaint.tracking_id} verified and awaiting assignment.",
            complaint_id=complaint.id,
        )
    else:
        complaint.status = S.REJECTED.value
        complaint.rejection_reason = note or "Rejected by nodal officer"
        _add_history(db, complaint, S.REJECTED.value, complaint.rejection_reason, officer)
        notification_service.notify(
            db, user_id=complaint.citizen_id, type=NotificationType.COMPLAINT_REJECTED,
            title="Complaint rejected",
            message=f"Complaint {complaint.tracking_id} was rejected: {complaint.rejection_reason}",
            complaint_id=complaint.id,
        )
    audit_service.log(db, action="complaint.verify", user_id=officer.id,
                      actor_role=officer.role, entity="complaint",
                      entity_id=complaint.id, detail=f"approve={approve}")
    db.commit()
    db.refresh(complaint)
    return complaint


def assign(db: Session, officer: User, complaint: Complaint, *, worker_id: int,
           deadline_hours: int = 36, note: str | None = None) -> Complaint:
    _require_status(complaint, S.VERIFIED, S.REOPENED, S.ESCALATED, S.ASSIGNED, S.IN_PROGRESS)
    worker = db.query(User).filter(User.id == worker_id).first()
    if not worker or worker.role != Role.WORKER.value:
        raise HTTPException(http_status.HTTP_400_BAD_REQUEST, "worker_id must reference a worker")
    if not worker.is_active:
        raise HTTPException(http_status.HTTP_400_BAD_REQUEST, "Worker account is inactive")

    if complaint.nodal_officer_id is None:
        complaint.nodal_officer_id = officer.id
    complaint.assigned_worker_id = worker.id
    complaint.status = S.ASSIGNED.value
    complaint.deadline = utcnow() + timedelta(hours=deadline_hours)
    complaint.work_verified = False
    _add_history(db, complaint, S.ASSIGNED.value,
                 note or f"Assigned to worker #{worker.id}", officer)

    notification_service.notify(
        db, user_id=worker.id, type=NotificationType.COMPLAINT_ASSIGNED,
        title="New task assigned",
        message=f"You have been assigned complaint {complaint.tracking_id}.",
        complaint_id=complaint.id,
    )
    notification_service.notify(
        db, user_id=complaint.citizen_id, type=NotificationType.COMPLAINT_ASSIGNED,
        title="Worker assigned",
        message=f"A worker has been assigned to {complaint.tracking_id}.",
        complaint_id=complaint.id,
    )
    audit_service.log(db, action="complaint.assign", user_id=officer.id,
                      actor_role=officer.role, entity="complaint",
                      entity_id=complaint.id, detail=f"worker={worker.id}")
    db.commit()
    db.refresh(complaint)
    return complaint


def verify_work(db: Session, officer: User, complaint: Complaint, *, approve: bool,
                note: str | None = None) -> Complaint:
    _require_status(complaint, S.RESOLVED)
    if approve:
        complaint.work_verified = True
        complaint.work_verified_by = officer.id
        _add_history(db, complaint, complaint.status,
                     note or "Work quality verified by officer", officer)
        notification_service.notify(
            db, user_id=complaint.citizen_id, type=NotificationType.COMPLAINT_RESOLVED,
            title="Please confirm resolution",
            message=f"Work on {complaint.tracking_id} is verified. Please share your feedback.",
            complaint_id=complaint.id,
        )
    else:
        complaint.work_verified = False
        complaint.status = S.IN_PROGRESS.value
        complaint.resolved_at = None
        _add_history(db, complaint, S.IN_PROGRESS.value,
                     note or "Work rejected by officer, rework needed", officer)
        worker_id = complaint.assigned_worker_id or complaint.assigned_ngo_id
        if worker_id:
            notification_service.notify(
                db, user_id=worker_id, type=NotificationType.COMPLAINT_IN_PROGRESS,
                title="Rework required",
                message=f"Work on {complaint.tracking_id} was rejected. Please redo and resubmit.",
                complaint_id=complaint.id,
            )
    audit_service.log(db, action="complaint.verify_work", user_id=officer.id,
                      actor_role=officer.role, entity="complaint",
                      entity_id=complaint.id, detail=f"approve={approve}")
    db.commit()
    db.refresh(complaint)
    return complaint


def escalate(db: Session, officer: User, complaint: Complaint, *,
             target: EscalationTarget, reason: str) -> Complaint:
    _require_status(complaint, S.VERIFIED, S.ASSIGNED, S.IN_PROGRESS, S.REOPENED, S.RESOLVED)
    complaint.status = S.ESCALATED.value
    complaint.escalation_reason = reason
    complaint.escalated_to = target.value if isinstance(target, EscalationTarget) else target
    if complaint.nodal_officer_id is None:
        complaint.nodal_officer_id = officer.id
    _add_history(db, complaint, S.ESCALATED.value,
                 f"Escalated to {complaint.escalated_to}: {reason}", officer)

    if complaint.escalated_to == EscalationTarget.NGO.value:
        _notify_role(db, Role.NGO, type=NotificationType.COMPLAINT_ESCALATED,
                     title="Complaint available for adoption",
                     message=f"Complaint {complaint.tracking_id} escalated to NGOs: {reason}",
                     complaint_id=complaint.id, ward=complaint.ward)
    else:
        _notify_role(db, Role.HIGHER_AUTHORITY, type=NotificationType.COMPLAINT_ESCALATED,
                     title="Complaint escalated",
                     message=f"Complaint {complaint.tracking_id} escalated: {reason}",
                     complaint_id=complaint.id, ward=complaint.ward)
    notification_service.notify(
        db, user_id=complaint.citizen_id, type=NotificationType.COMPLAINT_ESCALATED,
        title="Complaint escalated",
        message=f"Complaint {complaint.tracking_id} has been escalated for faster resolution.",
        complaint_id=complaint.id,
    )
    audit_service.log(db, action="complaint.escalate", user_id=officer.id,
                      actor_role=officer.role, entity="complaint",
                      entity_id=complaint.id, detail=complaint.escalated_to)
    db.commit()
    db.refresh(complaint)
    return complaint


def officer_close(db: Session, officer: User, complaint: Complaint, reason: str) -> Complaint:
    if complaint.status in (S.CLOSED.value, S.REJECTED.value):
        raise _conflict("Complaint is already closed")
    complaint.status = S.CLOSED.value
    complaint.closed_at = utcnow()
    complaint.close_reason = reason
    complaint.close_requested = False
    if complaint.nodal_officer_id is None:
        complaint.nodal_officer_id = officer.id
    _add_history(db, complaint, S.CLOSED.value, f"Closed by officer: {reason}", officer)
    notification_service.notify(
        db, user_id=complaint.citizen_id, type=NotificationType.COMPLAINT_CLOSED,
        title="Complaint closed",
        message=f"Complaint {complaint.tracking_id} was closed: {reason}",
        complaint_id=complaint.id,
    )
    audit_service.log(db, action="complaint.close", user_id=officer.id,
                      actor_role=officer.role, entity="complaint",
                      entity_id=complaint.id, detail=reason)
    db.commit()
    db.refresh(complaint)
    return complaint


# --------------------------------------------------------------------------- #
# Worker actions
# --------------------------------------------------------------------------- #
def _require_assigned_worker(complaint: Complaint, worker: User):
    if complaint.assigned_worker_id != worker.id:
        raise _forbidden("This task is not assigned to you")


def worker_accept(db: Session, worker: User, complaint: Complaint) -> Complaint:
    _require_assigned_worker(complaint, worker)
    _require_status(complaint, S.ASSIGNED)
    _add_history(db, complaint, complaint.status, "Task accepted by worker", worker)
    audit_service.log(db, action="complaint.accept", user_id=worker.id,
                      actor_role=worker.role, entity="complaint", entity_id=complaint.id)
    db.commit()
    db.refresh(complaint)
    return complaint


def start_work(db: Session, worker: User, complaint: Complaint, *, before_image: str) -> Complaint:
    _require_assigned_worker(complaint, worker)
    _require_status(complaint, S.ASSIGNED)
    complaint.before_image = before_image
    complaint.status = S.IN_PROGRESS.value
    _add_history(db, complaint, S.IN_PROGRESS.value, "Work started (before image uploaded)", worker)
    notification_service.notify(
        db, user_id=complaint.citizen_id, type=NotificationType.COMPLAINT_IN_PROGRESS,
        title="Work started",
        message=f"Work has started on complaint {complaint.tracking_id}.",
        complaint_id=complaint.id,
    )
    audit_service.log(db, action="complaint.start", user_id=worker.id,
                      actor_role=worker.role, entity="complaint", entity_id=complaint.id)
    db.commit()
    db.refresh(complaint)
    return complaint


def complete_work(db: Session, worker: User, complaint: Complaint, *, after_image: str) -> Complaint:
    _require_assigned_worker(complaint, worker)
    _require_status(complaint, S.IN_PROGRESS)
    complaint.after_image = after_image
    complaint.status = S.RESOLVED.value
    complaint.resolved_at = utcnow()
    _add_history(db, complaint, S.RESOLVED.value, "Work completed (after image uploaded)", worker)

    rewards_service.award_points(db, worker, settings.POINTS_WORKER_COMPLETE)
    if complaint.nodal_officer_id:
        notification_service.notify(
            db, user_id=complaint.nodal_officer_id, type=NotificationType.COMPLAINT_RESOLVED,
            title="Work submitted for verification",
            message=f"Worker submitted proof for {complaint.tracking_id}.",
            complaint_id=complaint.id,
        )
    notification_service.notify(
        db, user_id=complaint.citizen_id, type=NotificationType.COMPLAINT_RESOLVED,
        title="Complaint resolved",
        message=f"Complaint {complaint.tracking_id} marked resolved. Awaiting verification.",
        complaint_id=complaint.id,
    )
    audit_service.log(db, action="complaint.complete", user_id=worker.id,
                      actor_role=worker.role, entity="complaint", entity_id=complaint.id)
    db.commit()
    db.refresh(complaint)
    return complaint


# --------------------------------------------------------------------------- #
# NGO actions
# --------------------------------------------------------------------------- #
def ngo_available(db: Session, ngo: User, skip: int = 0, limit: int = 50) -> list[Complaint]:
    q = db.query(Complaint).filter(
        Complaint.status == S.ESCALATED.value,
        Complaint.escalated_to == EscalationTarget.NGO.value,
        Complaint.assigned_ngo_id.is_(None),
    )
    if ngo.ward:
        q = q.filter(or_(Complaint.ward == ngo.ward, Complaint.ward.is_(None)))
    return q.order_by(Complaint.created_at.desc()).offset(skip).limit(limit).all()


def ngo_adopt(db: Session, ngo: User, complaint: Complaint) -> Complaint:
    if complaint.escalated_to != EscalationTarget.NGO.value:
        raise _conflict("This complaint is not available for NGO adoption")
    _require_status(complaint, S.ESCALATED)
    if complaint.assigned_ngo_id is not None:
        raise _conflict("Complaint already adopted by an NGO")
    complaint.assigned_ngo_id = ngo.id
    complaint.status = S.ASSIGNED.value
    _add_history(db, complaint, S.ASSIGNED.value, f"Adopted by NGO {ngo.organization or ngo.name}", ngo)
    notification_service.notify(
        db, user_id=complaint.citizen_id, type=NotificationType.COMPLAINT_ASSIGNED,
        title="NGO adopted your complaint",
        message=f"An NGO has adopted complaint {complaint.tracking_id}.",
        complaint_id=complaint.id,
    )
    audit_service.log(db, action="complaint.ngo_adopt", user_id=ngo.id,
                      actor_role=ngo.role, entity="complaint", entity_id=complaint.id)
    db.commit()
    db.refresh(complaint)
    return complaint


def ngo_submit_proof(db: Session, ngo: User, complaint: Complaint, *,
                     after_image: str, before_image: str | None = None) -> Complaint:
    if complaint.assigned_ngo_id != ngo.id:
        raise _forbidden("This complaint is not assigned to your NGO")
    _require_status(complaint, S.ASSIGNED, S.IN_PROGRESS)
    if before_image:
        complaint.before_image = before_image
    complaint.after_image = after_image
    complaint.status = S.RESOLVED.value
    complaint.resolved_at = utcnow()
    _add_history(db, complaint, S.RESOLVED.value, "NGO submitted proof of work", ngo)
    if complaint.nodal_officer_id:
        notification_service.notify(
            db, user_id=complaint.nodal_officer_id, type=NotificationType.COMPLAINT_RESOLVED,
            title="NGO work submitted",
            message=f"NGO submitted proof for {complaint.tracking_id}.",
            complaint_id=complaint.id,
        )
    notification_service.notify(
        db, user_id=complaint.citizen_id, type=NotificationType.COMPLAINT_RESOLVED,
        title="Complaint resolved",
        message=f"Complaint {complaint.tracking_id} resolved by NGO. Awaiting verification.",
        complaint_id=complaint.id,
    )
    audit_service.log(db, action="complaint.ngo_proof", user_id=ngo.id,
                      actor_role=ngo.role, entity="complaint", entity_id=complaint.id)
    db.commit()
    db.refresh(complaint)
    return complaint
