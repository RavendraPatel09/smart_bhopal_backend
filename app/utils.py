"""Small shared helpers."""
from datetime import datetime, timezone
import uuid


def utcnow() -> datetime:
    """Naive UTC timestamp.

    We deliberately strip tzinfo so all stored datetimes are naive-UTC and
    comparable regardless of backend (SQLite returns naive datetimes).
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def gen_tracking_id(seq: int, year: int | None = None) -> str:
    """Human friendly complaint tracking id, e.g. CMP-2026-0042."""
    year = year or utcnow().year
    return f"CMP-{year}-{seq:04d}"


def gen_code(prefix: str) -> str:
    """Short unique code for certificates etc."""
    return f"{prefix}-{uuid.uuid4().hex[:10].upper()}"
