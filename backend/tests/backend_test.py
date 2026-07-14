"""AeroPulse backend regression tests."""
import os
import time
import io
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8000").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@aqi.io"
ADMIN_PASSWORD = "admin123"


@pytest.fixture(scope="session")
def admin_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=30)
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    data = r.json()
    assert data["email"] == ADMIN_EMAIL
    assert data["role"] == "admin"
    return s


@pytest.fixture(scope="session")
def user_session():
    s = requests.Session()
    email = f"TEST_user_{int(time.time())}@aqi.io"
    r = s.post(f"{API}/auth/register", json={"email": email, "password": "testpass123", "name": "Test User"}, timeout=30)
    assert r.status_code == 200, f"Register failed: {r.status_code} {r.text}"
    s.email = email
    return s


class TestHealth:
    def test_root(self):
        r = requests.get(f"{API}/")
        assert r.status_code == 200
        assert r.json().get("status") == "ok"

    def test_aqi_categories(self):
        r = requests.get(f"{API}/aqi/categories")
        assert r.status_code == 200
        assert isinstance(r.json(), list)


class TestAuth:
    def test_me_admin(self, admin_session):
        r = admin_session.get(f"{API}/auth/me")
        assert r.status_code == 200
        assert r.json()["email"] == ADMIN_EMAIL

    def test_invalid_login(self):
        r = requests.post(f"{API}/auth/login", json={"email": "nope@aqi.io", "password": "wrong"})
        assert r.status_code == 401

    def test_unauthorized(self):
        r = requests.get(f"{API}/auth/me")
        assert r.status_code == 401

    def test_register_duplicate(self, admin_session):
        r = requests.post(f"{API}/auth/register", json={"email": ADMIN_EMAIL, "password": "abc123", "name": "x"})
        assert r.status_code == 409


class TestDatasetsAndML:
    def test_seed_and_flow(self, user_session):
        # seed
        r = user_session.post(f"{API}/datasets/seed-sample")
        assert r.status_code == 200, r.text
        dsid = r.json()["id"]
        assert r.json()["rows"] > 0

        # list
        r = user_session.get(f"{API}/datasets")
        assert r.status_code == 200
        assert any(d["id"] == dsid for d in r.json())

        # get with preview
        r = user_session.get(f"{API}/datasets/{dsid}")
        assert r.status_code == 200
        j = r.json()
        assert "schema" in j

        # EDA
        r = user_session.get(f"{API}/datasets/{dsid}/eda")
        assert r.status_code == 200
        j = r.json()
        assert "correlation" in j and "aqi_distribution" in j

        # clean & feature-eng
        r = user_session.post(f"{API}/datasets/{dsid}/clean")
        assert r.status_code == 200
        r = user_session.post(f"{API}/datasets/{dsid}/feature-engineering")
        assert r.status_code == 200

        # train
        r = user_session.post(f"{API}/datasets/{dsid}/train", timeout=180)
        assert r.status_code == 200, r.text
        j = r.json()
        assert "results" in j and len(j["results"]) >= 3
        assert j.get("best_model")

        # models get
        r = user_session.get(f"{API}/datasets/{dsid}/models")
        assert r.status_code == 200
        assert r.json()["trained"] is True

        # predict
        features = {"pm25": 55, "pm10": 100, "no2": 30, "so2": 10, "co": 1.0, "o3": 40,
                    "temperature": 25, "humidity": 60, "wind_speed": 3, "pressure": 1013}
        r = user_session.post(f"{API}/predict", json={"dataset_id": dsid, "features": features, "location": "TEST_City"})
        assert r.status_code == 200, r.text
        pj = r.json()
        assert "aqi" in pj and "category" in pj
        pred_id = pj["id"]

        # history
        r = user_session.get(f"{API}/history")
        assert r.status_code == 200
        assert any(p["id"] == pred_id for p in r.json())

        # forecast
        r = user_session.post(f"{API}/forecast/{dsid}?days=7", timeout=60)
        assert r.status_code == 200, r.text
        assert len(r.json()) == 7

        # reports
        r = user_session.get(f"{API}/reports/prediction/{pred_id}")
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("application/pdf")

        r = user_session.get(f"{API}/reports/model/{dsid}")
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("application/pdf")

        # AI insight (may be slow)
        r = user_session.post(f"{API}/datasets/{dsid}/insights", timeout=120)
        assert r.status_code == 200, r.text
        assert len(r.json().get("insight", "")) > 50

        # save id for cleanup test
        user_session.dsid = dsid

    def test_delete_dataset(self, user_session):
        dsid = getattr(user_session, "dsid", None)
        if not dsid:
            pytest.skip("No dataset id")
        r = user_session.delete(f"{API}/datasets/{dsid}")
        assert r.status_code == 200
        r = user_session.get(f"{API}/datasets/{dsid}")
        assert r.status_code == 404


class TestAdmin:
    def test_admin_endpoints(self, admin_session):
        r = admin_session.get(f"{API}/admin/analytics")
        assert r.status_code == 200
        j = r.json()
        assert "users" in j and "datasets" in j

        r = admin_session.get(f"{API}/admin/users")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

        r = admin_session.get(f"{API}/admin/datasets")
        assert r.status_code == 200

        r = admin_session.get(f"{API}/admin/predictions")
        assert r.status_code == 200

    def test_admin_forbidden_for_user(self, user_session):
        r = user_session.get(f"{API}/admin/analytics")
        assert r.status_code == 403


class TestBruteForce:
    def test_lockout(self):
        s = requests.Session()
        email = f"TEST_bf_{int(time.time())}@aqi.io"
        # Register then attempt bad logins
        s.post(f"{API}/auth/register", json={"email": email, "password": "correct123", "name": "bf"})
        s.post(f"{API}/auth/logout")
        codes = []
        for _ in range(6):
            r = requests.post(f"{API}/auth/login", json={"email": email, "password": "wrong"})
            codes.append(r.status_code)
        assert 429 in codes, f"Expected 429 lockout, got {codes}"
