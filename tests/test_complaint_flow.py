from conftest import make_complaint


def _verify_and_assign(client, officer, worker, complaint_id):
    r = client.post(f"/nodal/complaints/{complaint_id}/verify",
                    json={"approve": True}, headers=officer["headers"])
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "verified"

    r = client.post(f"/nodal/complaints/{complaint_id}/assign",
                    json={"worker_id": worker["id"], "deadline_hours": 36},
                    headers=officer["headers"])
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "assigned"
    assert r.json()["assigned_worker_id"] == worker["id"]
    assert r.json()["deadline"] is not None


def test_full_happy_path(client, citizen, officer, worker):
    c = make_complaint(client, citizen)
    cid = c["id"]
    assert c["status"] == "submitted"
    assert c["tracking_id"].startswith("CMP-")
    assert c["ai_validated"] is True

    _verify_and_assign(client, officer, worker, cid)

    # worker accept -> start -> complete
    assert client.post(f"/worker/tasks/{cid}/accept", headers=worker["headers"]).status_code == 200
    r = client.post(f"/worker/tasks/{cid}/start",
                    json={"image_url": "/media/before.jpg"}, headers=worker["headers"])
    assert r.json()["status"] == "in_progress"
    assert r.json()["before_image"] == "/media/before.jpg"

    r = client.post(f"/worker/tasks/{cid}/complete",
                    json={"image_url": "/media/after.jpg"}, headers=worker["headers"])
    assert r.json()["status"] == "resolved"
    assert r.json()["after_image"] == "/media/after.jpg"
    assert r.json()["resolved_at"] is not None

    # officer verifies work quality
    r = client.post(f"/nodal/complaints/{cid}/verify-work",
                    json={"approve": True}, headers=officer["headers"])
    assert r.json()["work_verified"] is True
    assert r.json()["status"] == "resolved"

    # citizen satisfied -> closed
    r = client.post(f"/complaints/{cid}/feedback",
                    json={"satisfied": True, "rating": 5, "comment": "Great work"},
                    headers=citizen["headers"])
    assert r.status_code == 201, r.text

    detail = client.get(f"/complaints/{cid}", headers=citizen["headers"]).json()
    assert detail["status"] == "closed"
    assert detail["closed_at"] is not None
    # history should contain the full chain
    statuses = [h["status"] for h in detail["history"]]
    for expected in ["submitted", "verified", "assigned", "in_progress", "resolved", "closed"]:
        assert expected in statuses

    # rewards: submit (+10) + closed (+20) = 30
    rewards = client.get("/rewards/me", headers=citizen["headers"]).json()
    assert rewards["points"] == 30
    assert rewards["complaints_closed"] == 1

    # worker earned points for completing
    wr = client.get("/rewards/me", headers=worker["headers"]).json()
    assert wr["points"] == 15


def test_track_by_tracking_id(client, citizen):
    c = make_complaint(client, citizen)
    r = client.get(f"/complaints/track/{c['tracking_id']}", headers=citizen["headers"])
    assert r.status_code == 200
    assert r.json()["id"] == c["id"]


def test_reject_path(client, citizen, officer):
    c = make_complaint(client, citizen)
    r = client.post(f"/nodal/complaints/{c['id']}/verify",
                    json={"approve": False, "note": "Not a valid issue"},
                    headers=officer["headers"])
    assert r.status_code == 200
    assert r.json()["status"] == "rejected"
    assert r.json()["rejection_reason"] == "Not a valid issue"


def test_cannot_assign_before_verify(client, citizen, officer, worker):
    c = make_complaint(client, citizen)
    r = client.post(f"/nodal/complaints/{c['id']}/assign",
                    json={"worker_id": worker["id"]}, headers=officer["headers"])
    assert r.status_code == 409


def test_assign_requires_worker_role(client, citizen, officer):
    c = make_complaint(client, citizen)
    client.post(f"/nodal/complaints/{c['id']}/verify",
                json={"approve": True}, headers=officer["headers"])
    # officer id is not a worker
    r = client.post(f"/nodal/complaints/{c['id']}/assign",
                    json={"worker_id": officer["id"]}, headers=officer["headers"])
    assert r.status_code == 400


def test_worker_cannot_act_on_unassigned_task(client, citizen, officer, worker, make_user):
    from app.enums import Role
    other_worker = make_user(Role.WORKER)
    c = make_complaint(client, citizen)
    _verify_and_assign(client, officer, worker, c["id"])
    # a different worker tries to start
    r = client.post(f"/worker/tasks/{c['id']}/start",
                    json={"image_url": "/media/x.jpg"}, headers=other_worker["headers"])
    assert r.status_code == 403


def test_feedback_only_when_resolved(client, citizen, officer):
    c = make_complaint(client, citizen)
    r = client.post(f"/complaints/{c['id']}/feedback",
                    json={"satisfied": True}, headers=citizen["headers"])
    assert r.status_code == 409


def test_not_satisfied_reopens(client, citizen, officer, worker):
    c = make_complaint(client, citizen)
    cid = c["id"]
    _verify_and_assign(client, officer, worker, cid)
    client.post(f"/worker/tasks/{cid}/start", json={"image_url": "/media/b.jpg"},
                headers=worker["headers"])
    client.post(f"/worker/tasks/{cid}/complete", json={"image_url": "/media/a.jpg"},
                headers=worker["headers"])
    r = client.post(f"/complaints/{cid}/feedback",
                    json={"satisfied": False, "comment": "Still dirty"},
                    headers=citizen["headers"])
    assert r.status_code == 201
    detail = client.get(f"/complaints/{cid}", headers=citizen["headers"]).json()
    assert detail["status"] == "reopened"


def test_escalate_to_ngo_and_adopt(client, citizen, officer, ngo):
    c = make_complaint(client, citizen)
    cid = c["id"]
    client.post(f"/nodal/complaints/{cid}/verify", json={"approve": True},
                headers=officer["headers"])
    r = client.post(f"/nodal/complaints/{cid}/escalate",
                    json={"target": "ngo", "reason": "No workers available"},
                    headers=officer["headers"])
    assert r.json()["status"] == "escalated"
    assert r.json()["escalated_to"] == "ngo"

    # appears in NGO available list
    avail = client.get("/ngo/available", headers=ngo["headers"]).json()
    assert any(x["id"] == cid for x in avail)

    # adopt
    r = client.post(f"/ngo/complaints/{cid}/adopt", headers=ngo["headers"])
    assert r.json()["status"] == "assigned"
    assert r.json()["assigned_ngo_id"] == ngo["id"]

    # submit proof
    r = client.post(f"/ngo/complaints/{cid}/submit-proof",
                    json={"after_image": "/media/done.jpg"}, headers=ngo["headers"])
    assert r.json()["status"] == "resolved"

    # cannot be adopted again
    second = client.post(f"/ngo/complaints/{cid}/adopt", headers=ngo["headers"])
    assert second.status_code == 409


def test_close_request_then_officer_close(client, citizen, officer):
    c = make_complaint(client, citizen)
    cid = c["id"]
    r = client.post(f"/complaints/{cid}/close-request",
                    json={"reason": "Submitted by mistake"}, headers=citizen["headers"])
    assert r.status_code == 200
    assert r.json()["close_requested"] is True

    r = client.post(f"/nodal/complaints/{cid}/close",
                    json={"reason": "Duplicate / mistake confirmed"}, headers=officer["headers"])
    assert r.json()["status"] == "closed"


def test_reopen_after_closed(client, citizen, officer):
    c = make_complaint(client, citizen)
    cid = c["id"]
    client.post(f"/nodal/complaints/{cid}/close",
                json={"reason": "closing"}, headers=officer["headers"])
    r = client.post(f"/complaints/{cid}/reopen",
                    json={"reason": "Issue came back"}, headers=citizen["headers"])
    assert r.status_code == 200
    assert r.json()["status"] == "reopened"


def test_duplicate_detection(client, citizen):
    make_complaint(client, citizen, address="Same Street 1")
    second = make_complaint(client, citizen, address="Same Street 1")
    assert second["is_duplicate"] is True


def test_low_quality_complaint_not_ai_validated(client, citizen):
    c = make_complaint(client, citizen, image_url=None, description="dirty")
    assert c["ai_validated"] is False


def test_view_access_denied_for_other_citizen(client, citizen, make_user):
    from app.enums import Role
    other = make_user(Role.CITIZEN)
    c = make_complaint(client, citizen)
    r = client.get(f"/complaints/{c['id']}", headers=other["headers"])
    assert r.status_code == 403
