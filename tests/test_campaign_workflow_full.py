"""Comprehensive regression tests for Security Campaign creation, dropdown population, and link generation."""

import re
from datetime import timedelta
import pytest

from app import create_app
from database import db
from security_platform.models import (
    TestingCampaign, TestingLink, TestingSession, TestingEvent, utcnow_naive
)


@pytest.fixture
def app():
    test_app = create_app(test_config={
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
        "BASE_URL": "https://phishlab.example.test",
        "IS_PRODUCTION": True,
    })
    with test_app.app_context():
        db.create_all()
    yield test_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def admin_client(app):
    c = app.test_client()
    with c.session_transaction() as sess:
        sess["is_admin"] = True
        sess["admin_name"] = "admin"
    return c


# 1. Creating a campaign
def test_create_campaign_with_full_fields(admin_client, app):
    resp = admin_client.post(
        "/security/campaign/create",
        data={
            "name": "Q4 MFA Awareness",
            "objective": "Measure phishing reporting rate",
            "scenario_type": "security_alert",
            "status": "active",
            "start_date": "2026-11-01",
            "end_date": "2026-11-30",
            "description": "Authorized employee drill",
        },
        headers={"Accept": "application/json", "X-Requested-With": "XMLHttpRequest"},
    )
    assert resp.status_code == 201
    payload = resp.get_json()
    assert payload["status"] == "success"
    assert payload["campaign"]["name"] == "Q4 MFA Awareness"
    assert payload["campaign"]["objective"] == "Measure phishing reporting rate"
    assert payload["campaign"]["start_date"] == "2026-11-01"
    assert payload["campaign"]["end_date"] == "2026-11-30"


# 2. Listing existing campaigns
def test_list_existing_campaigns_endpoint(admin_client, app):
    with app.app_context():
        db.session.add(TestingCampaign(name="List Check Campaign", status="active"))
        db.session.commit()
    resp = admin_client.get("/security/campaigns")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"
    assert any(c["name"] == "List Check Campaign" for c in data["campaigns"])


# 3. Selecting a campaign & 4. Campaign dropdown population
def test_campaign_dropdown_population_and_selection(admin_client, app):
    with app.app_context():
        c = TestingCampaign(name="Dropdown Active Drill", scenario_type="security_alert", status="active")
        db.session.add(c)
        db.session.commit()
        cid = c.id

    dash = admin_client.get("/security/dashboard")
    assert dash.status_code == 200
    html = dash.data.decode("utf-8")
    assert 'id="target-campaign-select"' in html
    assert f'<option value="{cid}">Dropdown Active Drill' in html
    assert "No Security Campaigns Available" not in html or 'id="empty-campaigns-box" class="is-hidden"' in html


# 5. Empty campaign state
def test_empty_campaign_state_displays_guidance(admin_client, app):
    with app.app_context():
        TestingCampaign.query.delete()
        db.session.commit()

    dash = admin_client.get("/security/dashboard")
    assert dash.status_code == 200
    html = dash.data.decode("utf-8")
    assert "No Security Campaigns Available" in html
    assert "Create your first campaign below to generate a real testing link." in html
    assert "Create Security Campaign" in html


# 6. Campaign creation failure (validation)
def test_campaign_creation_validation_failures(admin_client):
    # Missing name
    r1 = admin_client.post(
        "/security/campaign/create",
        data={"name": "   ", "scenario_type": "security_alert"},
        headers={"Accept": "application/json"},
    )
    assert r1.status_code == 400
    assert r1.get_json()["status"] == "error"

    # End date before start date
    r2 = admin_client.post(
        "/security/campaign/create",
        data={
            "name": "Invalid Dates",
            "start_date": "2026-12-10",
            "end_date": "2026-12-01",
        },
        headers={"Accept": "application/json"},
    )
    assert r2.status_code == 400
    assert "earlier than start date" in r2.get_json()["message"]


# 7. Campaign status filtering
def test_paused_and_closed_campaigns_excluded_from_dropdown_and_link_generation(admin_client, app):
    with app.app_context():
        active_c = TestingCampaign(name="Active Filter Camp", status="active")
        paused_c = TestingCampaign(name="Paused Filter Camp", status="paused")
        closed_c = TestingCampaign(name="Closed Filter Camp", status="closed")
        db.session.add_all([active_c, paused_c, closed_c])
        db.session.commit()
        paused_id = paused_c.id

    listing = admin_client.get("/security/campaigns").get_json()
    active_names = [c["name"] for c in listing["active_campaigns"]]
    assert "Active Filter Camp" in active_names
    assert "Paused Filter Camp" not in active_names
    assert "Closed Filter Camp" not in active_names

    # Link generation must reject inactive campaign
    gen = admin_client.post(
        "/security/link/generate",
        data={"campaign_id": str(paused_id), "scenario_key": "whatsapp"},
        follow_redirects=True,
    )
    assert gen.status_code == 200
    assert "currently paused" in gen.data.decode("utf-8")


# 8. Testing-link generation & 9. Campaign-to-link-to-session-to-event relationship
def test_link_generation_and_full_relationships(admin_client, client, app):
    with app.app_context():
        c = TestingCampaign(name="Relationship Drill", status="active")
        db.session.add(c)
        db.session.commit()
        cid = c.id

    gen = admin_client.post(
        "/security/link/generate",
        data={
            "campaign_id": str(cid),
            "scenario_key": "telegram",
            "participant_alias": "RelTester",
            "participant_email": "rel@example.test",
            "max_uses": "5",
            "ttl_hours": "24",
        },
    )
    assert gen.status_code == 200
    html = gen.data.decode("utf-8")
    assert "<svg" in html
    m = re.search(r"https://phishlab\.example\.test/test/([A-Za-z0-9_\-]+)", html)
    assert m is not None
    raw_token = m.group(1)

    # Open link as participant -> creates TestingSession & TestingEvent linked to campaign
    r_open = client.get(f"/test/{raw_token}")
    assert r_open.status_code == 200
    r_con = client.post(f"/test/{raw_token}/consent", json={})
    assert r_con.status_code == 200

    with app.app_context():
        lnk = TestingLink.query.filter_by(campaign_id=cid).first()
        assert lnk is not None
        sess = TestingSession.query.filter_by(link_id=lnk.id, campaign_id=cid).first()
        assert sess is not None
        evts = TestingEvent.query.filter_by(campaign_id=cid, session_id=sess.id).all()
        assert len(evts) >= 2


# 10. Unique token generation
def test_unique_token_generation(admin_client, app):
    with app.app_context():
        c = TestingCampaign(name="Unique Token Camp", status="active")
        db.session.add(c)
        db.session.commit()
        cid = c.id

    tokens = []
    for _ in range(2):
        r = admin_client.post(
            "/security/link/generate",
            data={"campaign_id": str(cid), "scenario_key": "whatsapp"},
        )
        m = re.search(r"/test/([A-Za-z0-9_\-]+)", r.data.decode("utf-8"))
        assert m is not None
        tokens.append(m.group(1))
    assert tokens[0] != tokens[1]


# 11. Expiration handling
def test_expired_testing_link_rejected(admin_client, client, app):
    with app.app_context():
        c = TestingCampaign(name="Expiry Camp", status="active")
        db.session.add(c)
        db.session.commit()
        cid = c.id

    r = admin_client.post(
        "/security/link/generate",
        data={"campaign_id": str(cid), "scenario_key": "whatsapp", "ttl_hours": "1"},
    )
    m = re.search(r"/test/([A-Za-z0-9_\-]+)", r.data.decode("utf-8"))
    raw_token = m.group(1)

    with app.app_context():
        lnk = TestingLink.query.order_by(TestingLink.id.desc()).first()
        lnk.expires_at = utcnow_naive() - timedelta(hours=2)
        db.session.commit()

    res = client.get(f"/test/{raw_token}")
    assert res.status_code == 410


# 12. Unauthorized campaign creation
def test_unauthorized_campaign_creation_blocked(client):
    resp = client.post(
        "/security/campaign/create",
        data={"name": "Unauthorized", "scenario_type": "security_alert"},
    )
    assert resp.status_code == 403
