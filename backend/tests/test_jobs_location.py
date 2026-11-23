# Job search + location resolution, with the network mocked.
import pytest

import config
from services import geo, job_search

ADZUNA_SAMPLE = {"results": [
    {"id": 1, "title": "Software Engineering <strong>Intern</strong>", "company": {"display_name": "Stripe"},
     "location": {"display_name": "San Jose, CA"}, "redirect_url": "https://adzuna.com/1",
     "created": "2026-11-20T10:00:00Z", "salary_min": 40000, "salary_max": 50000, "salary_is_predicted": "1"},
    {"id": 2, "title": "Internal Tools Engineer", "company": {"display_name": "Acme"},     # NOT an internship
     "location": {"display_name": "San Jose, CA"}, "redirect_url": "https://adzuna.com/2"},
    {"id": 3, "title": "International Sales Rep", "company": {"display_name": "Acme"},    # NOT an internship
     "location": {"display_name": "San Jose, CA"}, "redirect_url": "https://adzuna.com/3"},
    {"id": 4, "title": "Data Science Co-op", "company": {"display_name": "Plaid"},
     "location": {"display_name": "San Jose, CA"}, "redirect_url": "https://adzuna.com/4"},
]}


@pytest.fixture
def adzuna(monkeypatch):
    calls = []
    def fake(params):
        calls.append(params)
        return ADZUNA_SAMPLE
    monkeypatch.setattr(job_search, "_fetch_adzuna", fake)
    return calls


def test_search_filters_to_internships(client, make_user, adzuna):
    _, h = make_user()
    r = client.get("/jobs/search", headers=h, params={"q": "software", "location": "San Jose, CA", "radius_km": 25})
    assert r.status_code == 200, r.text
    titles = [j["title"] for j in r.json()["results"]]
    assert titles == ["Software Engineering Intern", "Data Science Co-op"]   # HTML stripped, "Internal" dropped
    assert r.json()["results"][0]["salary"] == "$40,000–$50,000 (est.)"
    assert adzuna[0]["distance"] == 25 and adzuna[0]["where"] == "San Jose, CA"


def test_search_is_cached(client, make_user, adzuna):
    _, h = make_user()
    params = {"q": "software", "location": "San Jose, CA"}
    client.get("/jobs/search", headers=h, params=params)
    client.get("/jobs/search", headers=h, params=params)
    assert len(adzuna) == 1


def test_already_tracked_flag(client, make_user, adzuna):
    _, h = make_user()
    client.post("/applications", headers=h, json={"company_name": "Stripe", "position": "Intern",
                                                  "source": "adzuna", "external_id": "1", "status": "Saved"})
    results = client.get("/jobs/search", headers=h, params={"location": "San Jose, CA"}).json()["results"]
    assert {r["external_id"]: r["already_tracked"] for r in results} == {"1": True, "4": False}


def test_radius_limit(client, make_user, adzuna):
    _, h = make_user()
    assert client.get("/jobs/search", headers=h, params={"location": "X Y", "radius_km": 500}).status_code == 422


def test_not_configured_returns_503(client, make_user, monkeypatch):
    _, h = make_user()
    monkeypatch.setattr(config, "ADZUNA_APP_ID", None)
    r = client.get("/jobs/search", headers=h, params={"location": "San Jose, CA"})
    assert r.status_code == 503


# ---------------- location ----------------

@pytest.fixture
def nominatim(monkeypatch):
    calls = []
    def fake(path, params):
        calls.append((path, params))
        address = {"house_number": "123", "road": "Main St", "postcode": "95112",
                   "city": "San Jose", "state": "California", "ISO3166-2-lvl4": "US-CA"}
        return {"address": address} if path == "/reverse" else [{"address": address}]
    monkeypatch.setattr(geo, "_get_json", fake)
    return calls


def test_reverse_rounds_coordinates_and_returns_city_only(client, make_user, nominatim):
    _, h = make_user()
    r = client.post("/location/resolve", headers=h, json={"lat": 37.335480, "lng": -121.893028})
    assert r.status_code == 200
    assert r.json() == {"label": "San Jose, CA", "city": "San Jose", "state": "CA"}
    path, params = nominatim[0]
    assert params["lat"] == 37.34 and params["lon"] == -121.89      # rounded before leaving our server


def test_typed_address_returns_city_only(client, make_user, nominatim):
    _, h = make_user()
    r = client.post("/location/resolve", headers=h, json={"q": "123 Main St, San Jose CA 95112"})
    body = r.json()
    assert body["label"] == "San Jose, CA"
    assert "Main" not in r.text and "95112" not in r.text and "123" not in r.text


def test_location_requires_input(client, make_user):
    _, h = make_user()
    assert client.post("/location/resolve", headers=h, json={}).status_code == 400
    assert client.post("/location/resolve", headers=h, json={"lat": 999, "lng": 0}).status_code == 422
