import pytest

from conftest import make_complaint


def test_citizen_cannot_access_nodal_queue(client, citizen):
    r = client.get("/nodal/complaints", headers=citizen["headers"])
    assert r.status_code == 403


def test_worker_cannot_verify(client, citizen, officer, worker):
    c = make_complaint(client, citizen)
    r = client.post(f"/nodal/complaints/{c['id']}/verify",
                    json={"approve": True}, headers=worker["headers"])
    assert r.status_code == 403


def test_citizen_cannot_view_authority_dashboard(client, citizen):
    assert client.get("/authority/dashboard", headers=citizen["headers"]).status_code == 403


def test_non_admin_cannot_create_users(client, officer):
    r = client.post("/admin/users", json={
        "name": "X", "phone": "9111111111", "password": "secret123", "role": "worker",
    }, headers=officer["headers"])
    assert r.status_code == 403


def test_unauthenticated_blocked(client):
    assert client.get("/nodal/complaints").status_code == 401
    assert client.post("/complaints", json={}).status_code == 401


def test_invalid_token_rejected(client):
    r = client.get("/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert r.status_code == 401


def test_worker_cannot_create_complaint(client, worker):
    r = client.post("/complaints", json={
        "category": "Garbage / Waste Management",
        "description": "Some description here that is long enough",
    }, headers=worker["headers"])
    assert r.status_code == 403


@pytest.mark.parametrize("path", [
    "/nodal/complaints",
    "/authority/dashboard",
    "/admin/users",
])
def test_protected_paths_need_auth(client, path):
    assert client.get(path).status_code == 401
