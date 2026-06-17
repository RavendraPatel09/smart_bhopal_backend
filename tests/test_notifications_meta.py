from app.models.reference import Category, Ward
from conftest import make_complaint


def test_citizen_gets_notification_on_submit(client, citizen):
    make_complaint(client, citizen)
    notes = client.get("/notifications", headers=citizen["headers"]).json()
    assert len(notes) >= 1
    assert any(n["type"] == "complaint_submitted" for n in notes)


def test_mark_notification_read(client, citizen):
    make_complaint(client, citizen)
    notes = client.get("/notifications", headers=citizen["headers"]).json()
    nid = notes[0]["id"]
    r = client.post(f"/notifications/{nid}/read", headers=citizen["headers"])
    assert r.status_code == 200
    assert r.json()["is_read"] is True

    unread = client.get("/notifications?unread_only=true", headers=citizen["headers"]).json()
    assert all(n["id"] != nid for n in unread)


def test_mark_all_read(client, citizen):
    make_complaint(client, citizen)
    make_complaint(client, citizen, address="Another place")
    r = client.post("/notifications/read-all", headers=citizen["headers"])
    assert r.status_code == 200
    assert r.json()["marked_read"] >= 2
    unread = client.get("/notifications?unread_only=true", headers=citizen["headers"]).json()
    assert unread == []


def test_officer_notified_of_new_complaint(client, citizen, officer):
    make_complaint(client, citizen)
    notes = client.get("/notifications", headers=officer["headers"]).json()
    assert any(n["type"] == "complaint_submitted" for n in notes)


def test_meta_endpoints(client, db, citizen):
    db.add(Category(name="TestCat", default_priority="medium", sla_hours=36))
    db.add(Ward(name="TestWard", code="TW1", zone="Z1"))
    db.commit()

    cats = client.get("/meta/categories", headers=citizen["headers"]).json()
    assert any(c["name"] == "TestCat" for c in cats)

    wards = client.get("/meta/wards", headers=citizen["headers"]).json()
    assert any(w["code"] == "TW1" for w in wards)

    enums = client.get("/meta/enums", headers=citizen["headers"]).json()
    assert "citizen" in enums["roles"]
    assert "submitted" in enums["statuses"]
