def test_register_and_login(client):
    resp = client.post("/auth/register", json={
        "name": "Asha Citizen", "phone": "9123450001", "password": "secret123",
        "ward": "Ward 12 - New Market",
    })
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["role"] == "citizen"
    assert body["access_token"]

    # login with same credentials
    login = client.post("/auth/login", json={"phone": "9123450001", "password": "secret123"})
    assert login.status_code == 200
    token = login.json()["access_token"]

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["phone"] == "9123450001"
    assert me.json()["role"] == "citizen"


def test_duplicate_phone_rejected(client):
    payload = {"name": "Dup", "phone": "9123450002", "password": "secret123"}
    assert client.post("/auth/register", json=payload).status_code == 201
    resp = client.post("/auth/register", json=payload)
    assert resp.status_code == 409


def test_login_wrong_password(client):
    client.post("/auth/register", json={"name": "Xena", "phone": "9123450003", "password": "secret123"})
    resp = client.post("/auth/login", json={"phone": "9123450003", "password": "wrong"})
    assert resp.status_code == 401


def test_oauth_token_endpoint(client):
    client.post("/auth/register", json={"name": "Yara", "phone": "9123450004", "password": "secret123"})
    resp = client.post("/auth/token", data={"username": "9123450004", "password": "secret123"})
    assert resp.status_code == 200
    assert resp.json()["token_type"] == "bearer"


def test_me_requires_auth(client):
    assert client.get("/auth/me").status_code == 401


def test_short_password_rejected(client):
    resp = client.post("/auth/register", json={"name": "Zara", "phone": "9123450005", "password": "x"})
    assert resp.status_code == 422
