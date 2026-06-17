"""Gamification: points, badges, certificates and leaderboard."""
from sqlalchemy.orm import Session

from app.enums import BADGE_LEVELS, NotificationType
from app.models.certificate import Certificate
from app.models.complaint import Complaint
from app.models.user import User
from app.services import notification_service
from app.utils import gen_code


def badge_for_points(points: int) -> str:
    badge = BADGE_LEVELS[0][1]
    for threshold, name in BADGE_LEVELS:
        if points >= threshold:
            badge = name
        else:
            break
    return badge


def next_badge_info(points: int) -> tuple[str | None, int | None]:
    """Return (next_badge_name, points_remaining) or (None, None) at top tier."""
    for threshold, name in BADGE_LEVELS:
        if points < threshold:
            return name, threshold - points
    return None, None


def award_points(db: Session, user: User, amount: int) -> dict:
    """Add points, recompute badge, issue a certificate on badge upgrade.

    Returns a dict describing whether the badge changed.
    """
    previous_badge = user.badge
    user.points = (user.points or 0) + amount
    new_badge = badge_for_points(user.points)
    badge_changed = new_badge != previous_badge
    user.badge = new_badge
    db.flush()

    if badge_changed:
        _issue_badge_certificate(db, user, new_badge)
        notification_service.notify(
            db,
            user_id=user.id,
            type=NotificationType.BADGE_EARNED,
            title="New badge unlocked!",
            message=f"Congratulations! You earned the '{new_badge}' badge.",
        )
    return {"badge_changed": badge_changed, "badge": new_badge, "points": user.points}


def _issue_badge_certificate(db: Session, user: User, badge: str) -> Certificate:
    cert = Certificate(
        user_id=user.id,
        code=gen_code("CERT"),
        title=f"{badge} Certificate",
        badge=badge,
        points_snapshot=user.points,
    )
    db.add(cert)
    db.flush()
    notification_service.notify(
        db,
        user_id=user.id,
        type=NotificationType.CERTIFICATE_EARNED,
        title="Certificate earned",
        message=f"You received a certificate for reaching '{badge}'.",
    )
    return cert


def reward_summary(db: Session, user: User) -> dict:
    next_badge, remaining = next_badge_info(user.points)
    submitted = (
        db.query(Complaint).filter(Complaint.citizen_id == user.id).count()
    )
    closed = (
        db.query(Complaint)
        .filter(Complaint.citizen_id == user.id, Complaint.status == "closed")
        .count()
    )
    return {
        "user_id": user.id,
        "points": user.points,
        "badge": user.badge,
        "next_badge": next_badge,
        "points_to_next_badge": remaining,
        "complaints_submitted": submitted,
        "complaints_closed": closed,
    }


def leaderboard(db: Session, role: str = "citizen", limit: int = 10) -> list[dict]:
    users = (
        db.query(User)
        .filter(User.role == role, User.is_active.is_(True))
        .order_by(User.points.desc(), User.id.asc())
        .limit(limit)
        .all()
    )
    return [
        {
            "rank": idx + 1,
            "user_id": u.id,
            "name": u.name,
            "points": u.points,
            "badge": u.badge,
        }
        for idx, u in enumerate(users)
    ]
