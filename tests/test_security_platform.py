"""Automated test suite for the Real-Time Phishing Security Testing Platform."""

import io
import pytest
from datetime import datetime, timedelta
from app import create_app
from database import db
from security_platform.models import (
    TestingCampaign, TestingParticipant, TestingLink, TestingSession,
    ParticipantConsent, TestingEvent, DemonstrationUpload, SecurityAuditLog,
    utcnow_naive
)
from security_platform.tokens import generate_testing_token, hash_token, verify_token_hash, generate_qr_svg
from security_platform.telemetry import parse_user_agent, anonymize_ip

@pytest.fixture
def app():
    """Create test application with in-memory SQLite database."""
    app = create_app(test_config={
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False,
    })
    with app.app_context():
        db.create_all()
        # Seed an initial authorized campaign
        camp = TestingCampaign(
            name='Q4 Security Assessment',
            scenario_type='security_alert',
            description='Authorized evaluation of credential-free awareness.',
            status='active'
        )
        db.session.add(camp)
        db.session.commit()
    yield app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def admin_client(client):
    with client.session_transaction() as sess:
        sess['is_admin'] = True
        sess['admin_name'] = 'SecurityDirector'
    return client


def test_token_cryptography_and_qr():
    """Verify secrets token generation, SHA-256 hashing, and SVG QR output."""
    raw_token, token_hash = generate_testing_token()
    assert len(raw_token) >= 32
    assert len(token_hash) == 64
    assert hash_token(raw_token) == token_hash
    assert verify_token_hash(raw_token, token_hash) is True
    assert verify_token_hash("tampered_token", token_hash) is False

    # Test pure Python SVG QR generation
    svg = generate_qr_svg("https://example.test/test/abc123")
    assert "<svg" in svg
    assert "</svg>" in svg
    assert "rect" in svg


def test_telemetry_parser():
    """Verify User-Agent telemetry parsing and IP anonymization."""
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    info = parse_user_agent(ua, "192.168.1.100")
    assert info['browser_family'] == 'Google Chrome'
    assert info['os_family'] == 'Windows 10/11'
    assert info['device_category'] == 'Desktop'
    assert len(info['ip_hash']) == 16
    assert info['ip_hash'] != "192.168.1.100"


def test_admin_dashboard_auth(client):
    """Ensure dashboard is restricted to authenticated security administrators."""
    # Unauthenticated should return 403 Forbidden
    resp = client.get('/security/dashboard')
    assert resp.status_code == 403

    # Authenticated access
    with client.session_transaction() as sess:
        sess['is_admin'] = True
        sess['admin_name'] = 'SecurityDirector'
    resp_admin = client.get('/security/dashboard')
    assert resp_admin.status_code == 200
    assert b"Cybersecurity Operations" in resp_admin.data
    assert b"Q4 Security Assessment" in resp_admin.data


def test_campaign_create_and_toggle(admin_client):
    """Test campaign creation and activation status toggling."""
    resp = admin_client.post('/security/campaign/create', data={
        'name': 'Executive Spear Phishing Test',
        'scenario_type': 'recruitment',
        'description': 'Targeting C-level recruitment lures'
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b"Executive Spear Phishing Test" in resp.data

    # Toggle status to paused
    with admin_client.application.app_context():
        camp = TestingCampaign.query.filter_by(name='Executive Spear Phishing Test').first()
        cid = camp.id
    
    resp_toggle = admin_client.post(f'/security/campaign/{cid}/status', data={'status': 'paused'}, follow_redirects=True)
    assert resp_toggle.status_code == 200

    with admin_client.application.app_context():
        camp = db.session.get(TestingCampaign, cid)
        assert camp.status == 'paused'


def test_link_generation_and_landing(admin_client, client):
    """Test generating a functional testing URL, QR, and participant landing."""
    with admin_client.application.app_context():
        camp = TestingCampaign.query.first()
        cid = camp.id

    # Generate link
    resp = admin_client.post('/security/link/generate', data={
        'campaign_id': cid,
        'scenario_key': 'security_alert',
        'participant_name': 'Morgan Freeman',
        'participant_email': 'morgan@example.test',
        'max_usages': '5',
        'ttl_hours': '24'
    })
    assert resp.status_code == 200
    assert b"Security Testing Link Ready" in resp.data
    assert b"<svg" in resp.data

    # Retrieve raw token from DB
    with admin_client.application.app_context():
        link = TestingLink.query.first()
        assert link is not None
        # We can simulate participant accessing with token
        # Generate a known token for participant test
        raw_token, token_hash = generate_testing_token()
        link.token_hash = token_hash
        db.session.commit()

    # Participant accesses /test/<raw_token>
    landing = client.get(f'/test/{raw_token}', headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    assert landing.status_code == 200
    assert b"PhishLab Security Verification" in landing.data
    assert b"Participant Consent Gate" in landing.data
    assert b"Windows 10/11" in landing.data

    # Verify session and telemetry event were recorded
    with admin_client.application.app_context():
        session = TestingSession.query.first()
        assert session is not None
        assert session.browser_family in ['Google Chrome', 'Unknown Browser']
        evt = TestingEvent.query.filter_by(event_type='link_opened').first()
        assert evt is not None


def test_participant_consent_and_completion(admin_client, client):
    """Test participant consent agreement and final completion."""
    raw_token, token_hash = generate_testing_token()
    with admin_client.application.app_context():
        camp = TestingCampaign.query.first()
        part = TestingParticipant(campaign_id=camp.id, name='Taylor Swift', email='taylor@example.test')
        db.session.add(part)
        db.session.flush()
        link = TestingLink(
            campaign_id=camp.id,
            participant_id=part.id,
            token_hash=token_hash,
            scenario_key='security_alert',
            expires_at=utcnow_naive() + timedelta(hours=2)
        )
        db.session.add(link)
        db.session.commit()

    # Open link
    client.get(f'/test/{raw_token}')

    # Submit Consent
    consent_resp = client.post(f'/test/{raw_token}/consent')
    assert consent_resp.status_code == 200
    assert consent_resp.json['status'] == 'success'

    with admin_client.application.app_context():
        consent_record = ParticipantConsent.query.first()
        assert consent_record is not None
        assert consent_record.consented is True

    # Complete Assessment
    complete_resp = client.post(f'/test/{raw_token}/complete')
    assert complete_resp.status_code == 200
    assert complete_resp.json['status'] == 'success'

    with admin_client.application.app_context():
        session = TestingSession.query.first()
        assert session.completed is True


def test_participant_threat_reporting(admin_client, client):
    """Test participant flagging the simulation as a security threat."""
    raw_token, token_hash = generate_testing_token()
    with admin_client.application.app_context():
        camp = TestingCampaign.query.first()
        part = TestingParticipant(campaign_id=camp.id, name='Dana Scully', email='dana@example.test')
        db.session.add(part)
        db.session.flush()
        link = TestingLink(
            campaign_id=camp.id,
            participant_id=part.id,
            token_hash=token_hash,
            scenario_key='security_alert',
            expires_at=utcnow_naive() + timedelta(hours=2)
        )
        db.session.add(link)
        db.session.commit()

    # Open link & report
    client.get(f'/test/{raw_token}')
    rep_resp = client.post(f'/test/{raw_token}/report')
    assert rep_resp.status_code == 200
    assert rep_resp.json['status'] == 'success'

    with admin_client.application.app_context():
        evt = TestingEvent.query.filter_by(event_type='suspicious_reported').first()
        assert evt is not None


def test_safe_file_demonstration(admin_client, client):
    """Test safe sandbox file upload, SHA-256 calculation, and extension validation."""
    raw_token, token_hash = generate_testing_token()
    with admin_client.application.app_context():
        camp = TestingCampaign.query.first()
        part = TestingParticipant(campaign_id=camp.id, name='Fox Mulder', email='mulder@example.test')
        db.session.add(part)
        db.session.flush()
        link = TestingLink(
            campaign_id=camp.id,
            participant_id=part.id,
            token_hash=token_hash,
            scenario_key='document_review',
            expires_at=utcnow_naive() + timedelta(hours=2)
        )
        db.session.add(link)
        db.session.commit()

    client.get(f'/test/{raw_token}')

    # Upload valid text file
    data = {'demo_file': (io.BytesIO(b"Safe test demonstration content"), 'test_doc.txt')}
    resp = client.post(f'/test/{raw_token}/file-demonstration', data=data, content_type='multipart/form-data')
    assert resp.status_code == 200
    assert resp.json['status'] == 'success'
    assert 'file_hash_sha256' in resp.json
    assert resp.json['filename'] == 'test_doc.txt'

    # Reject dangerous executable file
    exe_data = {'demo_file': (io.BytesIO(b"MZ\x90\x00"), 'malware.exe')}
    bad_resp = client.post(f'/test/{raw_token}/file-demonstration', data=exe_data, content_type='multipart/form-data')
    assert bad_resp.status_code == 400
    assert 'Disallowed' in bad_resp.json['message']


def test_link_revocation(admin_client, client):
    """Test administrator revoking a link and verifying 410 Gone."""
    raw_token, token_hash = generate_testing_token()
    with admin_client.application.app_context():
        camp = TestingCampaign.query.first()
        part = TestingParticipant(campaign_id=camp.id, name='Walter Skinner', email='skinner@example.test')
        db.session.add(part)
        db.session.flush()
        link = TestingLink(
            campaign_id=camp.id,
            participant_id=part.id,
            token_hash=token_hash,
            scenario_key='security_alert',
            expires_at=utcnow_naive() + timedelta(hours=2)
        )
        db.session.add(link)
        db.session.commit()
        lid = link.id

    # Revoke link as admin
    resp = admin_client.post(f'/security/link/{lid}/revoke', follow_redirects=True)
    assert resp.status_code == 200

    # Participant visits revoked link
    revoked_resp = client.get(f'/test/{raw_token}')
    assert revoked_resp.status_code == 410
    assert b"Link Revoked" in revoked_resp.data


def test_reports_csv_and_print(admin_client):
    """Test generating CSV telemetry export and printable summary report."""
    with admin_client.application.app_context():
        camp = TestingCampaign.query.first()
        cid = camp.id

    # Test CSV
    csv_resp = admin_client.get('/security/reports/csv')
    assert csv_resp.status_code == 200
    assert csv_resp.headers['Content-Type'].startswith('text/csv')
    assert b"Event ID,Campaign ID,Event Type" in csv_resp.data

    # Test Printable report
    print_resp = admin_client.get(f'/security/reports/print/{cid}')
    assert print_resp.status_code == 200
    assert b"Executive Security Assessment Report" in print_resp.data
