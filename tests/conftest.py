import pytest

from app import create_app


@pytest.fixture
def app(tmp_path):
    return create_app({"TESTING": True, "DATABASE": str(tmp_path / "test.db")})


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def seeded(client):
    """A saved client with height/weight and an active membership."""
    r = client.post("/clients", json={
        "name": "Arun", "age": 28, "height": 175, "weight": 80,
        "program": "Fat Loss (FL)", "membership_expiry": "2999-12-31"})
    assert r.status_code == 201
    return "Arun"
