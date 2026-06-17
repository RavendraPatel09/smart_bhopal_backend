"""Analytics & reporting for Higher Authority / Nodal dashboards (boxes 6 & 8)."""
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.enums import ComplaintStatus as S
from app.enums import Role
from app.models.complaint import Complaint
from app.models.user import User
from app.utils import utcnow

OPEN_STATUSES = [
    S.SUBMITTED.value, S.VERIFIED.value, S.ASSIGNED.value,
    S.IN_PROGRESS.value, S.ESCALATED.value, S.REOPENED.value,
]


def _count(db: Session, **filters) -> int:
    q = db.query(func.count(Complaint.id))
    for k, v in filters.items():
        q = q.filter(getattr(Complaint, k) == v)
    return q.scalar() or 0


def overview(db: Session) -> dict:
    total = db.query(func.count(Complaint.id)).scalar() or 0

    by_status_rows = (
        db.query(Complaint.status, func.count(Complaint.id))
        .group_by(Complaint.status)
        .all()
    )
    by_status = {status: cnt for status, cnt in by_status_rows}

    active = sum(by_status.get(s, 0) for s in OPEN_STATUSES)
    pending = by_status.get(S.SUBMITTED.value, 0)
    resolved = by_status.get(S.RESOLVED.value, 0)
    closed = by_status.get(S.CLOSED.value, 0)
    escalated = by_status.get(S.ESCALATED.value, 0)

    return {
        "total_complaints": total,
        "active_complaints": active,
        "pending_verification": pending,
        "resolved_complaints": resolved,
        "closed_complaints": closed,
        "escalated_complaints": escalated,
        "rejected_complaints": by_status.get(S.REJECTED.value, 0),
        "by_status": by_status,
        "overdue_complaints": overdue_count(db),
        "total_users": db.query(func.count(User.id)).scalar() or 0,
        "active_workers": db.query(func.count(User.id))
            .filter(User.role == Role.WORKER.value, User.is_active.is_(True)).scalar() or 0,
        "ngos_registered": db.query(func.count(User.id))
            .filter(User.role == Role.NGO.value).scalar() or 0,
    }


def overdue_count(db: Session) -> int:
    now = utcnow()
    return (
        db.query(func.count(Complaint.id))
        .filter(
            Complaint.deadline.isnot(None),
            Complaint.deadline < now,
            Complaint.status.in_(OPEN_STATUSES),
        )
        .scalar()
        or 0
    )


def by_area(db: Session) -> list[dict]:
    rows = (
        db.query(Complaint.ward, func.count(Complaint.id))
        .group_by(Complaint.ward)
        .order_by(func.count(Complaint.id).desc())
        .all()
    )
    return [{"ward": ward or "Unassigned", "count": cnt} for ward, cnt in rows]


def top_issues(db: Session, limit: int = 10) -> list[dict]:
    rows = (
        db.query(Complaint.category, func.count(Complaint.id))
        .group_by(Complaint.category)
        .order_by(func.count(Complaint.id).desc())
        .limit(limit)
        .all()
    )
    return [{"category": cat, "count": cnt} for cat, cnt in rows]


def ward_performance(db: Session) -> list[dict]:
    rows = (
        db.query(
            Complaint.ward,
            func.count(Complaint.id).label("total"),
            func.sum(case((Complaint.status == S.CLOSED.value, 1), else_=0)).label("closed"),
            func.sum(case((Complaint.status.in_(OPEN_STATUSES), 1), else_=0)).label("open"),
        )
        .group_by(Complaint.ward)
        .all()
    )
    result = []
    for ward, total, closed, open_ in rows:
        total = total or 0
        closed = closed or 0
        result.append({
            "ward": ward or "Unassigned",
            "total": total,
            "closed": closed,
            "open": open_ or 0,
            "resolution_rate": round((closed / total) * 100, 1) if total else 0.0,
        })
    result.sort(key=lambda r: r["resolution_rate"], reverse=True)
    return result


def worker_performance(db: Session, limit: int = 20) -> list[dict]:
    rows = (
        db.query(
            User.id, User.name, User.points,
            func.count(Complaint.id).label("assigned"),
            func.sum(case(
                (Complaint.status.in_([S.RESOLVED.value, S.CLOSED.value]), 1), else_=0
            )).label("completed"),
        )
        .outerjoin(Complaint, Complaint.assigned_worker_id == User.id)
        .filter(User.role == Role.WORKER.value)
        .group_by(User.id, User.name, User.points)
        .order_by(func.count(Complaint.id).desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "worker_id": wid,
            "name": name,
            "points": points,
            "assigned": assigned or 0,
            "completed": completed or 0,
        }
        for wid, name, points, assigned, completed in rows
    ]


def ngo_performance(db: Session, limit: int = 20) -> list[dict]:
    rows = (
        db.query(
            User.id, User.name, User.organization,
            func.count(Complaint.id).label("adopted"),
            func.sum(case(
                (Complaint.status.in_([S.RESOLVED.value, S.CLOSED.value]), 1), else_=0
            )).label("resolved"),
        )
        .outerjoin(Complaint, Complaint.assigned_ngo_id == User.id)
        .filter(User.role == Role.NGO.value)
        .group_by(User.id, User.name, User.organization)
        .order_by(func.count(Complaint.id).desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "ngo_id": nid,
            "name": name,
            "organization": org,
            "adopted": adopted or 0,
            "resolved": resolved or 0,
        }
        for nid, name, org, adopted, resolved in rows
    ]


def heatmap(db: Session, limit: int = 500) -> list[dict]:
    rows = (
        db.query(Complaint.latitude, Complaint.longitude, Complaint.category,
                 Complaint.priority, Complaint.status)
        .filter(Complaint.latitude.isnot(None), Complaint.longitude.isnot(None))
        .limit(limit)
        .all()
    )
    return [
        {"lat": lat, "lng": lng, "category": cat, "priority": pri, "status": st}
        for lat, lng, cat, pri, st in rows
    ]


def citizen_engagement(db: Session) -> dict:
    total_citizens = (
        db.query(func.count(User.id)).filter(User.role == Role.CITIZEN.value).scalar() or 0
    )
    avg_points = (
        db.query(func.avg(User.points)).filter(User.role == Role.CITIZEN.value).scalar() or 0
    )
    return {
        "total_citizens": total_citizens,
        "average_points": round(float(avg_points), 1),
        "total_complaints": db.query(func.count(Complaint.id)).scalar() or 0,
    }
