def enter(client, plate, **kw):
    return client.post("/parking/entry", json={"vehicle_number": plate, **kw})


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["database"] == "connected"


def test_status_initially_empty(client):
    s = client.get("/parking/status").json()
    assert s["total_slots"] == 5 and s["available_slots"] == 5
    assert s["occupied_slots"] == 0 and s["occupancy_percent"] == 0


def test_slots_list(client):
    slots = client.get("/parking/slots").json()
    assert len(slots) == 5 and all(s["status"] == "available" for s in slots)


def test_entry_assigns_slot_and_updates_status(client):
    r = enter(client, "mh 12 ab 1234")
    assert r.status_code == 201
    body = r.json()
    assert body["vehicle_number"] == "MH12AB1234" and body["slot_number"] == "P01"
    s = client.get("/parking/status").json()
    assert s["occupied_slots"] == 1 and s["occupancy_percent"] == 20.0
    assert client.get("/parking/slots").json()[0]["vehicle_number"] == "MH12AB1234"


def test_duplicate_entry_rejected(client):
    enter(client, "MH12AB1234")
    assert enter(client, "MH12AB1234").status_code == 409


def test_specific_slot_request(client):
    r = enter(client, "MH12AB1111", slot_number="P04")
    assert r.json()["slot_number"] == "P04"
    assert enter(client, "MH12AB2222", slot_number="P04").status_code == 409
    assert enter(client, "MH12AB3333", slot_number="P99").status_code == 404


def test_exit_frees_slot_and_records_duration(client):
    enter(client, "MH12AB1234")
    r = client.post("/parking/exit", json={"vehicle_number": "MH12AB1234"})
    assert r.status_code == 200
    assert r.json()["status"] == "completed" and r.json()["duration_minutes"] >= 0
    assert client.get("/parking/status").json()["available_slots"] == 5


def test_exit_unknown_vehicle(client):
    assert client.post("/parking/exit", json={"vehicle_number": "NOPE1234"}).status_code == 404


def test_lot_full(client):
    for i in range(5):
        assert enter(client, f"MH12AA000{i}").status_code == 201
    r = enter(client, "MH12ZZ9999")
    assert r.status_code == 409 and "full" in r.json()["detail"].lower()
    assert client.get("/parking/status").json()["occupancy_percent"] == 100.0


def test_validation_errors(client):
    assert enter(client, "@@").status_code == 422
    assert enter(client, "MH12AB1234", vehicle_type="spaceship").status_code == 422
    assert client.get("/parking/history?limit=0").status_code == 422


def test_history_and_filters(client):
    enter(client, "MH12AB1234")
    enter(client, "MH12CD5678")
    client.post("/parking/exit", json={"vehicle_number": "MH12AB1234"})
    assert len(client.get("/parking/history").json()) == 2
    assert len(client.get("/parking/history?status=parked").json()) == 1
    assert client.get("/parking/history?vehicle=cd56").json()[0]["vehicle_number"] == "MH12CD5678"
    assert client.get("/parking/history?slot=P01").json()[0]["slot_number"] == "P01"
    assert client.get("/parking/history?min_duration=9999").json() == []


def test_analytics_endpoints(client):
    enter(client, "MH12AB1234")
    client.post("/parking/exit", json={"vehicle_number": "MH12AB1234"})
    s = client.get("/analytics/summary").json()
    assert s["total_sessions"] == 1 and s["entries_today"] == 1 and s["exits_today"] == 1
    assert len(client.get("/analytics/peak-hours").json()["hourly"]) == 24
    assert len(client.get("/analytics/entries-exits?days=3").json()) == 3
    assert client.get("/analytics/daily?days=3").status_code == 200
    assert client.get("/analytics/weekly").status_code == 200
    assert client.get("/analytics/occupancy-trend?days=1").status_code == 200


def test_prediction_endpoints(client):
    enter(client, "MH12AB1234")
    o = client.get("/prediction/occupancy").json()
    assert 0 <= o["next_30_min"] <= 100 and 0 <= o["next_60_min"] <= 100
    assert o["current_occupancy"] == 20.0
    d = client.get("/prediction/demand").json()
    assert d["demand"] in ("Low", "Medium", "High")
    assert abs(sum(d["probabilities"].values()) - 1) < 0.01
    assert "regression" in client.get("/prediction/model-info").json()
    assert len(client.get("/prediction/history").json()) == 2  # saved once (30 + 60 min)
