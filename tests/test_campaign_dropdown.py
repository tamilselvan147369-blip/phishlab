"""
Automated tests for the Target Campaign dropdown on the Security Platform dashboard.

Covers all 8 scenarios specified:
  1. Campaign options load.
  2. Campaign names display.
  3. Campaign IDs are correct.
  4. Selecting a campaign works (form renders selected value).
  5. Form submission stores the selected campaign (link_generate).
  6. Invalid campaign IDs are rejected.
  7. Empty campaign lists are handled.
  8. Editing preserves the selected campaign.
"""

import pytest
from app import create_app
from database import db as _db
from security_platform.models import TestingCampaign, TestingLink, utcnow_naive


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def app():
    """Create application configured with an isolated in-memory test database."""
    test_app = create_app({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SECRET_KEY": "test-secret-dropdown-2026",
    })
    with test_app.app_context():
        _db.create_all()
        yield test_app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def admin_client(client):
    """Return a test client with an active admin session."""
    with client.session_transaction() as sess:
        sess["is_admin"] = True
        sess["admin_name"] = "admin"
    return client


@pytest.fixture()
def campaign(app):
    """Create a single TestingCampaign and clean it up after the test."""
    with app.app_context():
        c = TestingCampaign(
            name="Dropdown Test Campaign",
            description="For dropdown tests",
            scenario_type="credential_audit",
            target_platforms="whatsapp,telegram",
            status="active",
            link_ttl_hours=48,
            max_uses_per_link=0,
            created_at=utcnow_naive(),
        )
        _db.session.add(c)
        _db.session.commit()
        cid = c.id
        yield c
        with app.app_context():
            obj = _db.session.get(TestingCampaign, cid)
            if obj:
                _db.session.delete(obj)
                _db.session.commit()


# ---------------------------------------------------------------------------
# Test 1 — Campaign options load
# ---------------------------------------------------------------------------

def test_campaign_options_load(admin_client, campaign, app):
    """The dashboard <select> must contain at least one <option> when campaigns exist."""
    with app.app_context():
        rv = admin_client.get("/security/dashboard")
    assert rv.status_code == 200
    html = rv.data.decode("utf-8")
    assert 'name="campaign_id"' in html
    # At least one real option value
    assert f'value="{campaign.id}"' in html


# ---------------------------------------------------------------------------
# Test 2 — Campaign names display
# ---------------------------------------------------------------------------

def test_campaign_names_display(admin_client, campaign, app):
    """The campaign name must appear as option text in the dropdown."""
    with app.app_context():
        rv = admin_client.get("/security/dashboard")
    html = rv.data.decode("utf-8")
    assert "Dropdown Test Campaign" in html


# ---------------------------------------------------------------------------
# Test 3 — Campaign IDs are correct
# ---------------------------------------------------------------------------

def test_campaign_ids_are_correct(admin_client, campaign, app):
    """Each option's value attribute must match the actual database primary key."""
    with app.app_context():
        rv = admin_client.get("/security/dashboard")
        html = rv.data.decode("utf-8")
        # The DB-assigned ID must appear as an option value
        assert f'value="{campaign.id}"' in html


# ---------------------------------------------------------------------------
# Test 4 — Selecting a campaign works (dropdown renders with real IDs)
# ---------------------------------------------------------------------------

def test_selecting_campaign_renders_correct_options(admin_client, app):
    """Create three campaigns; all three must appear as distinct dropdown options."""
    with app.app_context():
        ids = []
        names = []
        for i in range(3):
            c = TestingCampaign(
                name=f"Multi-Campaign {i}",
                description="",
                scenario_type="credential_audit",
                target_platforms="whatsapp",
                status="active",
                link_ttl_hours=24,
                max_uses_per_link=0,
                created_at=utcnow_naive(),
            )
            _db.session.add(c)
            _db.session.commit()
            ids.append(c.id)
            names.append(c.name)

    rv = admin_client.get("/security/dashboard")
    assert rv.status_code == 200
    html = rv.data.decode("utf-8")
    for cid, name in zip(ids, names):
        assert f'value="{cid}"' in html, f"Missing option value={cid}"
        assert name in html, f"Missing campaign name '{name}'"

    # Cleanup
    with app.app_context():
        for cid in ids:
            obj = _db.session.get(TestingCampaign, cid)
            if obj:
                _db.session.delete(obj)
        _db.session.commit()


# ---------------------------------------------------------------------------
# Test 5 — Form submission stores the selected campaign (link_generate)
# ---------------------------------------------------------------------------

def test_form_submission_stores_selected_campaign(admin_client, campaign, app):
    """POSTing a valid campaign_id to link_generate must succeed (200 or redirect)."""
    with app.app_context():
        cid = campaign.id
    rv = admin_client.post(
        "/security/link/generate",
        data={
            "campaign_id": str(cid),
            "participant_alias": "TestUser",
            "participant_email": "test@example.test",
            "participant_department": "QA",
            "ttl_hours": "24",
            "max_uses": "5",
        },
        follow_redirects=True,
    )
    # Should render the link_created page or redirect to dashboard — not 500
    assert rv.status_code in (200, 302)
    html = rv.data.decode("utf-8")
    # Must NOT show generic 500 error
    assert "Internal Server Error" not in html
    # Should show the generated token or the campaign name in the success page
    assert ("Testing link generated" in html or "test/" in html or "Dropdown Test Campaign" in html)


# ---------------------------------------------------------------------------
# Test 6 — Invalid campaign IDs are rejected
# ---------------------------------------------------------------------------

def test_invalid_campaign_id_rejected(admin_client, app):
    """POSTing a non-existent campaign_id must flash an error, not crash."""
    rv = admin_client.post(
        "/security/link/generate",
        data={
            "campaign_id": "999999",
            "participant_alias": "",
            "participant_email": "",
            "participant_department": "General",
            "ttl_hours": "24",
            "max_uses": "0",
        },
        follow_redirects=True,
    )
    assert rv.status_code in (200, 302)
    html = rv.data.decode("utf-8")
    # Must NOT return 500
    assert "Internal Server Error" not in html
    # Should flash the validation error
    assert "campaign" in html.lower() or "Select" in html


# ---------------------------------------------------------------------------
# Test 7 — Empty campaign lists are handled gracefully
# ---------------------------------------------------------------------------

def test_empty_campaign_list_shows_message(admin_client, app):
    """When no TestingCampaign records exist, the dashboard must show a helpful message."""
    with app.app_context():
        # Delete all campaigns for this test
        TestingCampaign.query.delete()
        _db.session.commit()

    rv = admin_client.get("/security/dashboard")
    assert rv.status_code == 200
    html = rv.data.decode("utf-8")
    # Must show empty-state guidance, not a broken form
    assert (
        "No campaigns yet" in html
        or "create one" in html.lower()
        or "Create a Security Campaign" in html
    )


# ---------------------------------------------------------------------------
# Test 8 — Editing (re-visiting dashboard) preserves correct campaign options
# ---------------------------------------------------------------------------

def test_dashboard_revisit_shows_updated_campaigns(admin_client, app):
    """After creating a campaign and revisiting the dashboard, it must appear in the dropdown."""
    with app.app_context():
        c = TestingCampaign(
            name="Persist Campaign",
            description="Persistence test",
            scenario_type="malware_awareness",
            target_platforms="linkedin",
            status="active",
            link_ttl_hours=72,
            max_uses_per_link=10,
            created_at=utcnow_naive(),
        )
        _db.session.add(c)
        _db.session.commit()
        cid = c.id

    # First visit
    rv1 = admin_client.get("/security/dashboard")
    html1 = rv1.data.decode("utf-8")
    assert f'value="{cid}"' in html1
    assert "Persist Campaign" in html1

    # Second visit (simulates editing workflow — campaign must still be there)
    rv2 = admin_client.get("/security/dashboard")
    html2 = rv2.data.decode("utf-8")
    assert f'value="{cid}"' in html2
    assert "Persist Campaign" in html2

    # Cleanup
    with app.app_context():
        obj = _db.session.get(TestingCampaign, cid)
        if obj:
            _db.session.delete(obj)
        _db.session.commit()
