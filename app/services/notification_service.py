"""Notification creation. In production this would also fan out to the
SMS / Push / Email / WhatsApp notification service (architecture box 7);
here we persist an in-app notification record."""
from sqlalchemy.orm import Session

from app.enums import NotificationType
from app.models.notification import Notification


def notify(
    db: Session,
    *,
    user_id: int,
    type: NotificationType,
    title: str,
    message: str,
    complaint_id: int | None = None,
) -> Notification:
    n = Notification(
        user_id=user_id,
        type=type.value if isinstance(type, NotificationType) else str(type),
        title=title,
        message=message,
        complaint_id=complaint_id,
    )
    db.add(n)
    db.flush()
    return n


def list_for_user(db: Session, user_id: int, unread_only: bool = False) -> list[Notification]:
    q = db.query(Notification).filter(Notification.user_id == user_id)
    if unread_only:
        q = q.filter(Notification.is_read.is_(False))
    return q.order_by(Notification.created_at.desc(), Notification.id.desc()).all()


def mark_read(db: Session, user_id: int, notification_id: int) -> Notification | None:
    n = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == user_id)
        .first()
    )
    if n and not n.is_read:
        n.is_read = True
        db.flush()
    return n


def mark_all_read(db: Session, user_id: int) -> int:
    count = (
        db.query(Notification)
        .filter(Notification.user_id == user_id, Notification.is_read.is_(False))
        .update({Notification.is_read: True})
    )
    db.flush()
    return count
