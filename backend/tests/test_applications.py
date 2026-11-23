# Auth + application CRUD, including the security rule that users
# can never touch each other's data.


def test_register_login_me(client, make_user):
    _, headers = make_user()
    me = client.get("/me", headers=headers).json()
    assert me["email"] == "ada@example.com"
    assert me["gmail"]["connected"] is False
    assert me["gmail"]["configured"] is True
    assert me["jobs_configured"] is True


def test_register_rejects_short_password(client):
    r = client.post("/register", json={"email": "x@example.com", "username": "xyz", "password": "short"})
    assert r.status_code == 422


def test_protected_routes_require_token(client):
    assert client.get("/applications").status_code == 401
    assert client.get("/applications", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_crud_happy_path(client, make_user):
    _, h = make_user()
    created = client.post("/applications", headers=h, json={
        "company_name": "Stripe", "position": "SWE Intern",
        "company_domain": "https://www.Stripe.com/jobs", "job_url": "https://stripe.com/jobs/1",
    })
    assert created.status_code == 200, created.text
    app = created.json()
    assert app["status"] == "Applied"
    assert app["company_domain"] == "stripe.com"      # cleaned up
    assert app["applied_at"] is not None
    assert app["track_email"] is False                 # consent is opt-in

    upd = client.put(f"/applications/{app['id']}", headers=h, json={"status": "Interview"}).json()
    assert upd["status"] == "Interview"
    assert upd["position"] == "SWE Intern"             # untouched fields stay

    assert len(client.get("/applications", headers=h).json()) == 1
    assert client.delete(f"/applications/{app['id']}", headers=h).status_code == 200
    assert client.get("/applications", headers=h).json() == []


def test_validation(client, make_user):
    _, h = make_user()
    base = {"company_name": "Acme", "position": "Intern"}
    assert client.post("/applications", headers=h, json={**base, "status": "Banana"}).status_code == 422
    # javascript: links would be an XSS hole when rendered as <a href>
    assert client.post("/applications", headers=h, json={**base, "job_url": "javascript:alert(1)"}).status_code == 422
    assert client.post("/applications", headers=h, json={**base, "company_domain": "not a domain"}).status_code == 422


def test_users_cannot_touch_each_others_applications(client, make_user):
    _, alice = make_user("alice@example.com")
    _, bob = make_user("bob@example.com")
    app_id = client.post("/applications", headers=alice, json={"company_name": "A", "position": "B"}).json()["id"]

    assert client.get("/applications", headers=bob).json() == []
    assert client.get(f"/applications/{app_id}", headers=bob).status_code == 404
    assert client.put(f"/applications/{app_id}", headers=bob, json={"status": "Offer"}).status_code == 404
    assert client.delete(f"/applications/{app_id}", headers=bob).status_code == 404
    assert client.get(f"/applications/{app_id}", headers=alice).json()["status"] == "Applied"


def test_saved_then_applied_sets_applied_at(client, make_user):
    _, h = make_user()
    app = client.post("/applications", headers=h, json={"company_name": "A", "position": "B", "status": "Saved"}).json()
    assert app["applied_at"] is None
    app = client.put(f"/applications/{app['id']}", headers=h, json={"status": "Applied"}).json()
    assert app["applied_at"] is not None


def test_duplicate_saved_posting_conflicts(client, make_user):
    _, h = make_user()
    body = {"company_name": "A", "position": "B", "source": "adzuna", "external_id": "123", "status": "Saved"}
    assert client.post("/applications", headers=h, json=body).status_code == 200
    assert client.post("/applications", headers=h, json=body).status_code == 409


def test_save_location(client, make_user):
    _, h = make_user()
    r = client.put("/me/location", headers=h, json={"location_label": "San Jose, CA"})
    assert r.json()["location_label"] == "San Jose, CA"
    r = client.put("/me/location", headers=h, json={"location_label": None})
    assert r.json()["location_label"] is None


def test_explicit_null_is_rejected_not_stored(client, make_user):
    # Regression (review round 2): {"status": null} used to be stored,
    # and every later GET /applications crashed with a 500.
    _, h = make_user()
    app_id = client.post("/applications", headers=h, json={"company_name": "A", "position": "B"}).json()["id"]
    for field in ("status", "company_name", "position", "track_email"):
        r = client.put(f"/applications/{app_id}", headers=h, json={field: None})
        assert r.status_code == 422, field
    assert client.get("/applications", headers=h).status_code == 200
    # Optional-but-nullable fields can still be cleared
    assert client.put(f"/applications/{app_id}", headers=h, json={"notes": None}).status_code == 200
