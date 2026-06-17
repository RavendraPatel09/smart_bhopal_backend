def test_admin_creates_users_of_each_role(client, admin):
    for i, role in enumerate(["worker", "ngo", "nodal_officer", "higher_authority", "citizen"]):
        r = client.post("/admin/users", json={
            "name": f"User {role}", "phone": f"9222200{i:03d}",
            "password": "secret123", "role": role,
            "organization": "Org" if role == "ngo" else None,
        }, headers=admin["headers"])
        assert r.status_code == 201, r.text
        assert r.json()["role"] == role

    users = client.get("/admin/users", headers=admin["headers"]).json()
    # 5 created + the admin itself
    assert len(users) == 6


def test_admin_filter_users_by_role(client, admin):
    client.post("/admin/users", json={
        "name": "Worker One", "phone": "9333300001", "password": "secret123", "role": "worker",
    }, headers=admin["headers"])
    workers = client.get("/admin/users?role=worker", headers=admin["headers"]).json()
    assert all(u["role"] == "worker" for u in workers)
    assert len(workers) == 1


def test_admin_update_user_deactivate(client, admin):
    created = client.post("/admin/users", json={
        "name": "Worker Two", "phone": "9333300002", "password": "secret123", "role": "worker",
    }, headers=admin["headers"]).json()
    r = client.patch(f"/admin/users/{created['id']}",
                     json={"is_active": False, "ward": "Ward 5 - Green Park"},
                     headers=admin["headers"])
    assert r.status_code == 200
    assert r.json()["is_active"] is False
    assert r.json()["ward"] == "Ward 5 - Green Park"


def test_deactivated_user_cannot_login(client, admin):
    created = client.post("/admin/users", json={
        "name": "Dev Worker", "phone": "9333300003", "password": "secret123", "role": "worker",
    }, headers=admin["headers"]).json()
    client.patch(f"/admin/users/{created['id']}", json={"is_active": False},
                 headers=admin["headers"])
    r = client.post("/auth/login", json={"phone": "9333300003", "password": "secret123"})
    assert r.status_code == 403


def test_admin_wards_and_categories(client, admin):
    r = client.post("/admin/wards", json={"name": "Ward 99", "code": "W99", "zone": "Z9"},
                    headers=admin["headers"])
    assert r.status_code == 201
    # duplicate code rejected
    assert client.post("/admin/wards", json={"name": "Ward 99b", "code": "W99"},
                       headers=admin["headers"]).status_code == 409

    r = client.post("/admin/categories", json={
        "name": "Parks", "default_priority": "low", "sla_hours": 100,
    }, headers=admin["headers"])
    assert r.status_code == 201

    cats = client.get("/admin/categories", headers=admin["headers"]).json()
    assert any(c["name"] == "Parks" for c in cats)


def test_audit_logs_recorded(client, admin):
    client.post("/admin/users", json={
        "name": "Worker Three", "phone": "9333300004", "password": "secret123", "role": "worker",
    }, headers=admin["headers"])
    logs = client.get("/admin/audit-logs", headers=admin["headers"]).json()
    assert any(log["action"] == "user.create" for log in logs)
