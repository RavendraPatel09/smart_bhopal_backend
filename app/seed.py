"""Idempotent seeding of reference data and demo accounts.

Run standalone:  python -m app.seed
Also invoked on app startup (unless SEED_ON_STARTUP=0).
"""
import logging

from app.config import settings
from app.database import SessionLocal, init_db
from app.enums import Role
from app.models.reference import Category, Ward
from app.models.user import User
from app.security import hash_password

logger = logging.getLogger("smart_bhopal.seed")

DEMO_PASSWORD = "Passw0rd!"

CATEGORIES = [
    ("Garbage / Waste Management", "Uncollected garbage, illegal dumping", "high", 24),
    ("Water Supply / Leakage", "Leakage, contamination, no supply", "high", 24),
    ("Street Light", "Non-functional or damaged street lights", "medium", 48),
    ("Road & Infrastructure", "Potholes, broken roads, footpaths", "medium", 72),
    ("Drainage / Sewage", "Blocked or overflowing drains", "high", 36),
    ("Noise Pollution", "Excessive noise complaints", "low", 72),
    ("Others", "Any other civic issue", "medium", 48),
]

WARDS = [
    ("Ward 45 - Koh-e-Fiza", "W45", "Zone 1"),
    ("Ward 32 - Shanti Nagar", "W32", "Zone 2"),
    ("Ward 12 - New Market", "W12", "Zone 1"),
    ("Ward 5 - Green Park", "W05", "Zone 3"),
]

# (attr_key, name, phone, role, ward, organization)
DEMO_USERS = [
    ("admin", "Super Admin", settings.SEED_ADMIN_PHONE, Role.SUPER_ADMIN, None, None),
    ("officer", "Nodal Officer", "9000000001", Role.NODAL_OFFICER, "Ward 45 - Koh-e-Fiza", "BMC"),
    ("worker", "Field Worker", "9000000002", Role.WORKER, "Ward 45 - Koh-e-Fiza", None),
    ("worker2", "Field Worker 2", "9000000003", Role.WORKER, "Ward 32 - Shanti Nagar", None),
    ("ngo", "Helping Hands NGO", "9000000004", Role.NGO, "Ward 45 - Koh-e-Fiza", "Helping Hands"),
    ("authority", "Higher Authority", "9000000005", Role.HIGHER_AUTHORITY, None, "Municipal Corp"),
    ("citizen", "Demo Citizen", "9000000006", Role.CITIZEN, "Ward 45 - Koh-e-Fiza", None),
]


def ensure_seed() -> dict:
    init_db()
    db = SessionLocal()
    created = {"users": 0, "categories": 0, "wards": 0}
    try:
        for name, desc, prio, sla in CATEGORIES:
            if not db.query(Category).filter(Category.name == name).first():
                db.add(Category(name=name, description=desc, default_priority=prio, sla_hours=sla))
                created["categories"] += 1

        for name, code, zone in WARDS:
            if not db.query(Ward).filter(Ward.code == code).first():
                db.add(Ward(name=name, code=code, zone=zone))
                created["wards"] += 1

        for _key, name, phone, role, ward, org in DEMO_USERS:
            if not db.query(User).filter(User.phone == phone).first():
                pwd = (settings.SEED_ADMIN_PASSWORD if role == Role.SUPER_ADMIN
                       else DEMO_PASSWORD)
                db.add(User(
                    name=name, phone=phone, password=hash_password(pwd),
                    role=role.value, ward=ward, organization=org,
                ))
                created["users"] += 1
        db.commit()
        logger.info("Seed complete: %s", created)
        return created
    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = ensure_seed()
    print("Seeded:", result)
    print(f"Super admin login -> phone: {settings.SEED_ADMIN_PHONE} "
          f"password: {settings.SEED_ADMIN_PASSWORD}")
    print(f"Demo users (officer/worker/ngo/authority/citizen) password: {DEMO_PASSWORD}")
