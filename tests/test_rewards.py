from app.enums import Role
from app.models.certificate import Certificate
from app.services import rewards_service


def test_badge_for_points():
    assert rewards_service.badge_for_points(0) == "Green Starter"
    assert rewards_service.badge_for_points(50) == "Green Starter"
    assert rewards_service.badge_for_points(51) == "Active Citizen"
    assert rewards_service.badge_for_points(151) == "Cleanliness Champion"
    assert rewards_service.badge_for_points(301) == "Swachh Hero"
    assert rewards_service.badge_for_points(501) == "Smart Bhopal Ambassador"
    assert rewards_service.badge_for_points(10000) == "Smart Bhopal Ambassador"


def test_next_badge_info():
    name, remaining = rewards_service.next_badge_info(0)
    assert name == "Active Citizen" and remaining == 51
    name, remaining = rewards_service.next_badge_info(501)
    assert name is None and remaining is None


def test_award_points_upgrades_badge_and_issues_certificate(db, make_user):
    info = make_user(Role.CITIZEN)
    from app.models.user import User
    user = db.query(User).filter(User.id == info["id"]).first()

    result = rewards_service.award_points(db, user, 60)
    db.commit()
    assert result["badge_changed"] is True
    assert user.badge == "Active Citizen"

    certs = db.query(Certificate).filter(Certificate.user_id == user.id).count()
    assert certs == 1

    # cross another threshold
    rewards_service.award_points(db, user, 100)  # 160 total
    db.commit()
    assert user.badge == "Cleanliness Champion"
    assert db.query(Certificate).filter(Certificate.user_id == user.id).count() == 2


def test_leaderboard(client, db, make_user):
    from app.models.user import User
    viewer = make_user(Role.CITIZEN)
    for pts in (300, 100, 200):
        info = make_user(Role.CITIZEN)
        u = db.query(User).filter(User.id == info["id"]).first()
        u.points = pts
        db.commit()

    resp = client.get("/rewards/leaderboard?role=citizen&limit=10", headers=viewer["headers"])
    assert resp.status_code == 200
    board = resp.json()
    points = [e["points"] for e in board]
    assert points == sorted(points, reverse=True)
    assert board[0]["rank"] == 1
