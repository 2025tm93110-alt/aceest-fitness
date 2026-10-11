"""Regression tests: malformed input must yield 4xx, never a 500."""
import importlib

import pytest

BODY_ENDPOINTS = [
    ("post", "/clients"),
    ("post", "/clients/Arun/progress"),
    ("post", "/clients/Arun/workouts"),
    ("post", "/clients/Arun/metrics"),
    ("post", "/clients/Arun/generate-program"),
    ("put", "/clients/Arun"),
]


@pytest.mark.parametrize("method,url", BODY_ENDPOINTS)
@pytest.mark.parametrize("payload", [[1, 2], "text", 5, None])
def test_non_object_json_body_is_rejected(client, seeded, method, url, payload):
    r = getattr(client, method)(url, json=payload)
    assert r.status_code == 400
    assert "error" in r.get_json()


@pytest.mark.parametrize("payload", [
    {"weight": "abc"}, {"weight": -5}, {"weight": True}, {"height": 0},
    {"age": True}, {"age": 1.5}, {"age": -3},
    {"target_adherence": "x"}, {"target_adherence": 101}, {"target_adherence": True},
    {"target_weight": "heavy"}, {"membership_expiry": "31/12/2030"},
])
def test_update_rejects_invalid_fields(client, seeded, payload):
    assert client.put(f"/clients/{seeded}", json=payload).status_code == 400


@pytest.mark.parametrize("payload", [
    {"name": "B", "program": "Beginner (BG)", "age": True},
    {"name": "B", "program": "Beginner (BG)", "target_adherence": 500},
    {"name": 123, "program": "Beginner (BG)"},
])
def test_create_rejects_invalid_fields(client, payload):
    assert client.post("/clients", json=payload).status_code == 400


def test_update_valid_fields_still_works(client, seeded):
    r = client.put(f"/clients/{seeded}", json={"age": 30, "target_adherence": 90,
                                               "membership_expiry": "2999-01-01"})
    assert r.status_code == 200
    assert r.get_json()["age"] == 30 and r.get_json()["target_adherence"] == 90


def test_workout_bool_duration_rejected(client, seeded):
    r = client.post(f"/clients/{seeded}/workouts", json={"workout_type": "Mixed", "duration_min": True})
    assert r.status_code == 400


def test_importing_app_has_no_side_effects(tmp_path, monkeypatch):
    """`import app` must expose a WSGI `app` and must not touch the database."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("ACEEST_DB", raising=False)
    import app as app_module
    importlib.reload(app_module)
    assert app_module.app is not None
    assert not list(tmp_path.glob("*.db"))


def test_data_persists_across_app_instances(tmp_path):
    from app import create_app
    cfg = {"TESTING": True, "DATABASE": str(tmp_path / "p.db")}
    create_app(cfg).test_client().post("/clients", json={"name": "Z", "program": "Beginner (BG)"})
    r = create_app(cfg).test_client().get("/clients/Z")
    assert r.status_code == 200
