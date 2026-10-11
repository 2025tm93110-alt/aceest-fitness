def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.get_json()["status"] == "ok"


def test_index(client):
    assert client.get("/").status_code == 200


def test_list_and_get_programs(client):
    progs = client.get("/programs").get_json()
    assert set(progs) == {"Fat Loss (FL)", "Muscle Gain (MG)", "Beginner (BG)"}
    r = client.get("/programs/Fat Loss (FL)")
    assert r.status_code == 200 and r.get_json()["factor"] == 22
    assert client.get("/programs/Unknown").status_code == 404


def test_create_client_computes_calories(client):
    r = client.post("/clients", json={"name": "Meena", "weight": 60, "program": "Beginner (BG)"})
    assert r.status_code == 201
    assert r.get_json()["calories"] == 1560


def test_create_client_validation(client):
    assert client.post("/clients", json={"program": "Beginner (BG)"}).status_code == 400
    assert client.post("/clients", json={"name": "X", "program": "Bad"}).status_code == 400
    assert client.post("/clients", json={"name": "X", "program": "Beginner (BG)",
                                         "weight": -5}).status_code == 400
    assert client.post("/clients", json={"name": "X", "program": "Beginner (BG)",
                                         "membership_expiry": "bad"}).status_code == 400
    assert client.post("/clients", data="notjson").status_code == 400


def test_duplicate_client_conflict(client, seeded):
    r = client.post("/clients", json={"name": seeded, "program": "Beginner (BG)"})
    assert r.status_code == 409


def test_list_and_get_client(client, seeded):
    assert [c["name"] for c in client.get("/clients").get_json()] == [seeded]
    assert client.get(f"/clients/{seeded}").get_json()["age"] == 28
    assert client.get("/clients/ghost").status_code == 404


def test_update_client_recalculates_calories(client, seeded):
    r = client.put(f"/clients/{seeded}", json={"program": "Muscle Gain (MG)", "weight": 70})
    assert r.status_code == 200 and r.get_json()["calories"] == 2450
    assert client.put("/clients/ghost", json={}).status_code == 404
    assert client.put(f"/clients/{seeded}", json={"program": "Bad"}).status_code == 400


def test_delete_client_cascades(client, seeded):
    client.post(f"/clients/{seeded}/progress", json={"adherence": 80})
    assert client.delete(f"/clients/{seeded}").status_code == 204
    assert client.get(f"/clients/{seeded}").status_code == 404
    assert client.delete(f"/clients/{seeded}").status_code == 404


def test_progress_flow(client, seeded):
    assert client.post(f"/clients/{seeded}/progress", json={"adherence": 75}).status_code == 201
    client.post(f"/clients/{seeded}/progress", json={"adherence": 90})
    data = client.get(f"/clients/{seeded}/progress").get_json()
    assert [d["adherence"] for d in data] == [75, 90]


def test_progress_validation(client, seeded):
    for bad in (101, -1, "x", None, True):
        assert client.post(f"/clients/{seeded}/progress", json={"adherence": bad}).status_code == 400
    assert client.post("/clients/ghost/progress", json={"adherence": 5}).status_code == 404
    assert client.get("/clients/ghost/progress").status_code == 404


def test_workout_flow(client, seeded):
    r = client.post(f"/clients/{seeded}/workouts",
                    json={"date": "2026-01-02", "workout_type": "Strength", "duration_min": 45})
    assert r.status_code == 201
    client.post(f"/clients/{seeded}/workouts",
                json={"date": "2026-01-05", "workout_type": "Mobility"})
    rows = client.get(f"/clients/{seeded}/workouts").get_json()
    assert [w["date"] for w in rows] == ["2026-01-05", "2026-01-02"]


def test_workout_validation(client, seeded):
    url = f"/clients/{seeded}/workouts"
    assert client.post(url, json={"workout_type": "Yoga"}).status_code == 400
    assert client.post(url, json={"workout_type": "Mixed", "date": "nope"}).status_code == 400
    assert client.post(url, json={"workout_type": "Mixed", "duration_min": 0}).status_code == 400
    assert client.post("/clients/ghost/workouts", json={}).status_code == 404
    assert client.get("/clients/ghost/workouts").status_code == 404


def test_metrics_flow(client, seeded):
    url = f"/clients/{seeded}/metrics"
    assert client.post(url, json={"date": "2026-01-01", "weight": 80, "waist": 90}).status_code == 201
    client.post(url, json={"date": "2026-02-01", "weight": 78})
    assert [m["weight"] for m in client.get(url).get_json()] == [80, 78]


def test_metrics_validation(client, seeded):
    url = f"/clients/{seeded}/metrics"
    assert client.post(url, json={"weight": 0}).status_code == 400
    assert client.post(url, json={"weight": 70, "date": "bad"}).status_code == 400
    assert client.post("/clients/ghost/metrics", json={}).status_code == 404
    assert client.get("/clients/ghost/metrics").status_code == 404


def test_bmi_endpoint(client, seeded):
    body = client.get(f"/clients/{seeded}/bmi").get_json()
    assert body["bmi"] == 26.1 and body["category"] == "Overweight"
    client.post("/clients", json={"name": "NoData", "program": "Beginner (BG)"})
    assert client.get("/clients/NoData/bmi").status_code == 400
    assert client.get("/clients/ghost/bmi").status_code == 404


def test_membership_endpoint(client, seeded):
    assert client.get(f"/clients/{seeded}/membership").get_json()["status"] == "Active"
    client.post("/clients", json={"name": "Old", "program": "Beginner (BG)",
                                  "membership_expiry": "2000-01-01"})
    assert client.get("/clients/Old/membership").get_json()["status"] == "Expired"
    assert client.get("/clients/ghost/membership").status_code == 404


def test_summary_aggregates(client, seeded):
    client.post(f"/clients/{seeded}/progress", json={"adherence": 60})
    client.post(f"/clients/{seeded}/progress", json={"adherence": 80})
    client.post(f"/clients/{seeded}/metrics", json={"date": "2026-01-01", "weight": 79})
    s = client.get(f"/clients/{seeded}/summary").get_json()
    assert s["weeks_logged"] == 2 and s["average_adherence"] == 70.0
    assert s["last_metrics"]["weight"] == 79
    assert client.get("/clients/ghost/summary").status_code == 404


def test_summary_empty_history(client, seeded):
    s = client.get(f"/clients/{seeded}/summary").get_json()
    assert s["average_adherence"] == 0 and s["last_metrics"] is None


def test_generate_program_endpoint(client, seeded):
    r = client.post(f"/clients/{seeded}/generate-program", json={"experience": "beginner"})
    assert r.status_code == 200 and len(r.get_json()["plan"]) == 9
    assert client.post(f"/clients/{seeded}/generate-program", json={"experience": "x"}).status_code == 400
    assert client.post("/clients/ghost/generate-program", json={}).status_code == 404
