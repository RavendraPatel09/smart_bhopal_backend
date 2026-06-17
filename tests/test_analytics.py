from conftest import make_complaint


def test_dashboard_counts(client, citizen, officer, authority):
    make_complaint(client, citizen)
    c2 = make_complaint(client, citizen, category="Water Supply / Leakage",
                        address="Other Street")
    # reject one
    client.post(f"/nodal/complaints/{c2['id']}/verify",
                json={"approve": False, "note": "invalid"}, headers=officer["headers"])

    dash = client.get("/authority/dashboard", headers=authority["headers"]).json()
    assert dash["total_complaints"] == 2
    assert dash["pending_verification"] == 1   # the un-verified one
    assert dash["rejected_complaints"] == 1
    assert "by_status" in dash


def test_areas_and_top_issues(client, citizen, authority):
    make_complaint(client, citizen, category="Garbage / Waste Management", address="A1")
    make_complaint(client, citizen, category="Garbage / Waste Management", address="A2")
    make_complaint(client, citizen, category="Street Light", address="A3")

    areas = client.get("/authority/analytics/areas", headers=authority["headers"]).json()
    assert any(a["ward"] == "Ward 45 - Koh-e-Fiza" for a in areas)

    issues = client.get("/authority/analytics/top-issues", headers=authority["headers"]).json()
    top = issues[0]
    assert top["category"] == "Garbage / Waste Management"
    assert top["count"] == 2


def test_ward_and_worker_performance(client, citizen, officer, worker, authority):
    c = make_complaint(client, citizen)
    client.post(f"/nodal/complaints/{c['id']}/verify", json={"approve": True},
                headers=officer["headers"])
    client.post(f"/nodal/complaints/{c['id']}/assign",
                json={"worker_id": worker["id"]}, headers=officer["headers"])

    wp = client.get("/authority/analytics/ward-performance", headers=authority["headers"]).json()
    assert isinstance(wp, list) and len(wp) >= 1

    workers = client.get("/authority/analytics/worker-performance",
                         headers=authority["headers"]).json()
    assert any(w["worker_id"] == worker["id"] and w["assigned"] >= 1 for w in workers)


def test_heatmap_and_engagement(client, citizen, authority):
    make_complaint(client, citizen)
    hm = client.get("/authority/analytics/heatmap", headers=authority["headers"]).json()
    assert len(hm) >= 1
    assert "lat" in hm[0] and "lng" in hm[0]

    eng = client.get("/authority/analytics/engagement", headers=authority["headers"]).json()
    assert eng["total_complaints"] >= 1
