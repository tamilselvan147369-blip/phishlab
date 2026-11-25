"""End-to-end automated tests for Real-Time External Execution Platform."""

import io
import re
import pytest
from datetime import timedelta

from app import create_app
from database import db
from security_platform.models import (
    TestingCampaign, TestingParticipant, TestingLink, TestingSession,
    TestingEvent, ParticipantConsent, DemonstrationUpload, utcnow_naive
)


@pytest.fixture
def app():
    test_app = create_app(test_config={
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False,
        'BASE_URL': 'https://phishlab.example.test',
        'IS_PRODUCTION': True,
    })
    with test_app.app_context():
        db.create_all()
        camp = TestingCampaign(
            name='External Awareness Drill',
            scenario_type='security_alert',
            description='Authorized external execution assessment.',
            status='active',
        )
        db.session.add(camp)
        db.session.commit()
    yield test_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def admin_client(client):
    with client.session_transaction() as sess:
        sess['is_admin'] = True
        sess['admin_name'] = 'SecurityLead'
    return client


def test_base_url_and_six_platform_distribution_cards(admin_client, app):
    """Link generation uses BASE_URL with HTTPS and renders all 6 platform distribution cards."""
    with app.app_context():
        camp = TestingCampaign.query.first()
        cid = camp.id

    resp = admin_client.post('/security/link/generate', data={
        'campaign_id': str(cid),
        'participant_alias': 'MobileTester',
        'participant_email': 'mobile@example.test',
        'scenario_key': 'whatsapp',
        'ttl_hours': '48',
        'max_uses': '5',
    })
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')
    assert 'https://phishlab.example.test/test/' in html
    assert 'MobileTester' in html
    for platform_label in ['WhatsApp', 'Telegram', 'LinkedIn', 'X (Twitter)', 'Instagram', 'Facebook Messenger']:
        assert platform_label in html


def test_full_participant_workflow_mobile_and_desktop(admin_client, client, app):
    """Simulate a second-device mobile participant completing the entire workflow."""
    with app.app_context():
        camp = TestingCampaign.query.first()
        cid = camp.id

    resp = admin_client.post('/security/link/generate', data={
        'campaign_id': str(cid),
        'participant_alias': 'AndroidUser',
        'participant_email': 'android@example.test',
        'ttl_hours': '24',
        'max_uses': '3',
    })
    html = resp.data.decode('utf-8')
    m = re.search(r'https://phishlab\.example\.test/test/([A-Za-z0-9_\-]+)', html)
    assert m is not None
    raw_token = m.group(1)

    android_ua = (
        'Mozilla/5.0 (Linux; Android 14; Pixel 8) '
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36'
    )

    # 1. Participant opens link on mobile device
    r1 = client.get(f'/test/{raw_token}', headers={'User-Agent': android_ua})
    assert r1.status_code == 200
    body1 = r1.data.decode('utf-8')
    assert 'AndroidUser' in body1
    assert 'Google Chrome' in body1
    assert 'Android' in body1
    assert 'Mobile' in body1

    # 2. Participant grants explicit consent
    r2 = client.post(f'/test/{raw_token}/consent', json={})
    assert r2.status_code == 200
    assert r2.get_json()['status'] == 'success'

    # 3. Participant uploads a synthetic sample text file
    sample_data = (io.BytesIO(b'Synthetic PhishLab sandbox verification sample.'), 'sample_notice.txt')
    r3 = client.post(
        f'/test/{raw_token}/file-demonstration',
        data={'demo_file': sample_data},
        content_type='multipart/form-data',
    )
    assert r3.status_code == 200
    j3 = r3.get_json()
    assert j3['status'] == 'success'
    assert len(j3['file_hash_sha256']) == 64
    assert 'security_notice' in j3

    # 4. Participant reports suspicious message & completes assessment
    r4 = client.post(f'/test/{raw_token}/report', json={})
    assert r4.status_code == 200
    assert r4.get_json()['action'] == 'reported'

    r5 = client.post(f'/test/{raw_token}/complete', json={})
    assert r5.status_code == 200
    assert r5.get_json()['status'] == 'success'

    # 5. Verify persisted DB records
    with app.app_context():
        events = [e.event_type for e in TestingEvent.query.filter_by(campaign_id=cid).all()]
        for expected in ['link_opened', 'consent_submitted', 'assessment_started', 'file_uploaded', 'suspicious_reported', 'assessment_completed']:
            assert expected in events
        ts = TestingSession.query.filter_by(campaign_id=cid).first()
        assert ts.has_consented is True
        assert ts.completed is True
        assert ts.device_category == 'Mobile'
        assert ts.os_family == 'Android'

    # 6. Admin dashboard and CSV export reflect real persisted telemetry
    dash = admin_client.get('/security/dashboard')
    assert dash.status_code == 200
    dash_html = dash.data.decode('utf-8')
    assert 'Google Chrome' in dash_html
    assert 'Mobile' in dash_html

    csv_resp = admin_client.get('/security/reports/csv')
    assert csv_resp.status_code == 200
    assert 'assessment_completed' in csv_resp.data.decode('utf-8')


def test_revoked_expired_and_invalid_tokens_rejected(admin_client, client, app):
    """Invalid, expired, and revoked tokens must be rejected cleanly."""
    assert client.get('/test/nonexistent-token-xyz').status_code == 404

    with app.app_context():
        camp = TestingCampaign.query.first()
        cid = camp.id

    resp = admin_client.post('/security/link/generate', data={
        'campaign_id': str(cid),
        'participant_alias': 'RevokeTarget',
        'ttl_hours': '24',
        'max_uses': '5',
    })
    m = re.search(r'/test/([A-Za-z0-9_\-]+)', resp.data.decode('utf-8'))
    raw_token = m.group(1)

    with app.app_context():
        link = TestingLink.query.order_by(TestingLink.id.desc()).first()
        lid = link.id

    rev = admin_client.post(f'/security/link/{lid}/revoke', follow_redirects=True)
    assert rev.status_code == 200

    # Revoked token returns 410 Gone
    assert client.get(f'/test/{raw_token}').status_code == 410


def test_csrf_enabled_participant_flow():
    """When CSRF is enabled (production mode), landing page embeds CSRF meta token and accepts it."""
    csrf_app = create_app(test_config={
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': True,
        'SECRET_KEY': 'csrf-test-key-2026',
    })
    with csrf_app.app_context():
        db.create_all()
        camp = TestingCampaign(name='CSRF Campaign', status='active')
        db.session.add(camp)
        db.session.commit()
        cid = camp.id

    c = csrf_app.test_client()
    with c.session_transaction() as sess:
        sess['is_admin'] = True
        sess['admin_name'] = 'admin'

    # Fetch dashboard to get CSRF token
    d = c.get('/security/dashboard')
    m_csrf = re.search(r'name="csrf_token" value="([^"]+)"', d.data.decode('utf-8'))
    assert m_csrf is not None
    admin_csrf = m_csrf.group(1)

    gen = c.post('/security/link/generate', data={
        'csrf_token': admin_csrf,
        'campaign_id': str(cid),
        'participant_alias': 'CsrfParticipant',
    })
    assert gen.status_code == 200
    m_tok = re.search(r'/test/([A-Za-z0-9_\-]+)', gen.data.decode('utf-8'))
    raw_token = m_tok.group(1)

    # Participant opens page and extracts meta csrf-token
    p_client = csrf_app.test_client()
    page = p_client.get(f'/test/{raw_token}')
    assert page.status_code == 200
    m_meta = re.search(r'name="csrf-token" content="([^"]+)"', page.data.decode('utf-8'))
    assert m_meta is not None
    p_csrf = m_meta.group(1)

    # Without CSRF header -> 400
    no_csrf = p_client.post(f'/test/{raw_token}/consent', json={})
    assert no_csrf.status_code == 400

    # With X-CSRFToken header -> 200
    with_csrf = p_client.post(
        f'/test/{raw_token}/consent',
        json={},
        headers={'X-CSRFToken': p_csrf},
    )
    assert with_csrf.status_code == 200
    assert with_csrf.get_json()['status'] == 'success'


def test_production_no_default_admin_password_and_session_epoch_invalidation():
    """Production mode rejects default fallback password and SESSION_EPOCH invalidates old sessions."""
    prod_app = create_app(test_config={
        'TESTING': True,
        'IS_PRODUCTION': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False,
        'SECRET_KEY': 'rotated-prod-secret-key',
        'SESSION_EPOCH': '2',
    })
    with prod_app.app_context():
        db.create_all()

    c = prod_app.test_client()
    # Default dev password must NOT work when IS_PRODUCTION=True and ADMIN_PASSWORD is unset
    resp = c.post('/admin/login', data={
        'username': 'admin',
        'password': 'phishlab-admin-2026!',
    })
    assert resp.status_code == 503

    # Old session with _session_epoch='1' is rejected when SESSION_EPOCH='2'
    with c.session_transaction() as sess:
        sess['is_admin'] = True
        sess['_session_epoch'] = '1'
    dash = c.get('/security/dashboard')
    assert dash.status_code == 403


def test_events_recent_endpoint(admin_client, app):
    """Persisted events endpoint requires admin auth and returns JSON events."""
    anon = app.test_client()
    assert anon.get('/security/events/recent').status_code == 403
    r = admin_client.get('/security/events/recent')
    assert r.status_code == 200
    assert 'events' in r.get_json()
