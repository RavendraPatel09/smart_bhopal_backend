"""Audit logging helper."""
from sqlalchemy.orm import Session

from app.models.audit import AuditLog


def log(
    db: Session,
    *,
    action: str,
    user_id: int | None = None,
    actor_role: str | None = None,
    entity: str | None = None,
    entity_id: int | None = None,
    detail: str | None = None,
) -> AuditLog:
    entry = AuditLog(
        user_id=user_id,
        actor_role=actor_role,
        action=action,
        entity=entity,
        entity_id=entity_id,
        detail=detail,
    )
    db.add(entry)
    # Flush (not commit) so it participates in the caller's transaction.
    db.flush()
    return entry
