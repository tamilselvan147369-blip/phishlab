import os
import tempfile
import pytest
from datetime import datetime, timedelta
from app import create_app
from database import db, Campaign, Event
from real_app_testing.models import (
    RealAppExercise, ExerciseParticipant, ManualEventConfirmation,
    AuditLog, PLATFORMS
)
from real_app_testing.tokens import verify_token
from real_app_testing.routes import CONNECTORS

@pytest.fixture
def app():
    """Create app with an in-memory SQLite database for testing."""
    app = create_app(test_config={
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False,
        'REALAPP_TOKEN_TTL': timedelta(hours=2),
    })
    with app.app_context():
        db.create_all()
        campaign = Campaign(
            name='Test Awareness Campaign',
            scenario='social',
            subject='Security Notice',
            sender_name='Security Team',
            recipient='user@example.test',
            template='<p>Please review your security settings.</p>',
            description='Test Campaign Description'
        )
        db.session.add(campaign)
        db.session.commit()
    yield app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def admin_client(client):
    with client.session_transaction() as sess:
        sess['is_admin'] = True
        sess['admin_name'] = 'SecAdmin'
    return client


def test_create_app_returns_flask_instance():
    """Verify create_app() returns a valid Flask application with blueprint registered."""
    app = create_app(test_config={'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:', 'TESTING': True})
    from flask import Flask
    assert isinstance(app, Flask)
    assert 'realapp' in [bp.name for bp in app.iter_blueprints()]


def test_all_six_platforms_selection(app, admin_client):
    """Test that all 6 supported platforms can be used to create exercises."""
    with app.app_context():
        cid = Campaign.query.first().id

    for platform_name in PLATFORMS:
        resp = admin_client.post(
            f'/realapp/select/{cid}',
            data={'platform': platform_name, 'exercise_name': f'Test {platform_name}'},
            follow_redirects=False
        )
        assert resp.status_code == 302
        assert '/realapp/demo/' in resp.headers['Location']


def test_create_exercise_and_consent_flow(app, admin_client, client):
    """Full lifecycle: create exercise, access demo, confirm consent, check completion."""
    with app.app_context():
        cid = Campaign.query.first().id

    # 1. Admin creates exercise
    resp = admin_client.post(
        f'/realapp/select/{cid}',
        data={'platform': 'whatsapp', 'exercise_name': 'WhatsApp PhishLab Demo'},
        follow_redirects=False
    )
    assert resp.status_code == 302
    token = resp.headers['Location'].split('/realapp/demo/')[-1]

    # Verify exercise stored and hashed
    with app.app_context():
        ex = RealAppExercise.query.filter_by(platform='whatsapp').first()
        assert ex is not None
        assert ex.exercise_name == 'WhatsApp PhishLab Demo'
        assert verify_token(token, ex.demo_token_hash)

    # 2. Participant visits demo page (unauthenticated link)
    resp = client.get(f'/realapp/demo/{token}')
    assert resp.status_code == 200
    assert b'whatsapp' in resp.data.lower()

    # 3. Participant submits consent
    part_uuid = '99999999-9999-9999-9999-999999999999'
    resp = client.post(
        f'/realapp/confirm/{token}',
        data={'participant_uuid': part_uuid, 'consent': 'on'},
        follow_redirects=False
    )
    assert resp.status_code == 302
    assert f'/realapp/completion/{token}' in resp.headers['Location']

    # 4. Verify participant, confirmation and audit log stored
    with app.app_context():
        p = ExerciseParticipant.query.filter_by(participant_uuid=part_uuid).first()
        assert p is not None
        conf = ManualEventConfirmation.query.filter_by(exercise_id=ex.id, participant_id=p.id).first()
        assert conf is not None
        assert conf.event_type == 'demo_viewed'
        audit = AuditLog.query.filter_by(exercise_id=ex.id, action='participant_confirmed').first()
        assert audit is not None

    # 5. Access completion page
    resp = client.get(f'/realapp/completion/{token}')
    assert resp.status_code == 200
    assert b'Thank you for participating' in resp.data


def test_token_expiration(app, admin_client, client):
    """Expired token returns HTTP 410."""
    with app.app_context():
        cid = Campaign.query.first().id
    resp = admin_client.post(f'/realapp/select/{cid}', data={'platform': 'telegram'}, follow_redirects=False)
    token = resp.headers['Location'].split('/realapp/demo/')[-1]

    with app.app_context():
        ex = RealAppExercise.query.filter_by(platform='telegram').first()
        ex.token_expires_at = datetime(2020, 1, 1)
        db.session.commit()

    resp = client.get(f'/realapp/demo/{token}')
    assert resp.status_code == 410


def test_token_revocation(app, admin_client, client):
    """Admin can revoke an exercise token, causing HTTP 403 on demo access."""
    with app.app_context():
        cid = Campaign.query.first().id
    resp = admin_client.post(f'/realapp/select/{cid}', data={'platform': 'linkedin'}, follow_redirects=False)
    token = resp.headers['Location'].split('/realapp/demo/')[-1]

    with app.app_context():
        ex = RealAppExercise.query.filter_by(platform='linkedin').first()
        ex_id = ex.id

    # Revoke exercise
    resp = admin_client.post(f'/realapp/revoke/{ex_id}', follow_redirects=True)
    assert resp.status_code == 200

    # Demo link should now return 403 Forbidden
    resp = client.get(f'/realapp/demo/{token}')
    assert resp.status_code == 403


def test_exercise_history_and_analytics(app, admin_client):
    """Admin can view history and analytics."""
    with app.app_context():
        cid = Campaign.query.first().id
    admin_client.post(f'/realapp/select/{cid}', data={'platform': 'x'}, follow_redirects=False)

    # History
    resp = admin_client.get('/realapp/history')
    assert resp.status_code == 200
    assert b'Real' in resp.data

    # Analytics
    resp = admin_client.get('/realapp/analytics')
    assert resp.status_code == 200
    assert b'Analytics' in resp.data


def test_csv_export(app, admin_client):
    """Admin can export exercises as CSV."""
    with app.app_context():
        cid = Campaign.query.first().id
    admin_client.post(f'/realapp/select/{cid}', data={'platform': 'facebook_messenger'}, follow_redirects=False)

    resp = admin_client.get('/realapp/export/csv')
    assert resp.status_code == 200
    assert resp.mimetype == 'text/csv'
    assert 'attachment; filename=realapp_exercises.csv' in resp.headers.get('Content-Disposition', '')
    assert b'Exercise ID,Exercise Name,Campaign,Platform' in resp.data


def test_audit_log_and_exercise_detail(app, admin_client):
    """Admin can view audit log and exercise details."""
    with app.app_context():
        cid = Campaign.query.first().id
    resp = admin_client.post(f'/realapp/select/{cid}', data={'platform': 'whatsapp'}, follow_redirects=False)

    with app.app_context():
        ex = RealAppExercise.query.first()
        ex_id = ex.id

    # Audit log
    resp = admin_client.get('/realapp/audit')
    assert resp.status_code == 200
    assert b'Audit Log' in resp.data
    assert b'exercise_created' in resp.data

    # Exercise detail
    resp = admin_client.get(f'/realapp/exercise/{ex_id}')
    assert resp.status_code == 200
    assert b'Exercise:' in resp.data


def test_connector_instructions(app, admin_client):
    """Verify platform connector instructions view."""
    with app.app_context():
        cid = Campaign.query.first().id
    admin_client.post(f'/realapp/select/{cid}', data={'platform': 'telegram'}, follow_redirects=False)

    with app.app_context():
        ex = RealAppExercise.query.filter_by(platform='telegram').first()
        ex_id = ex.id

    resp = admin_client.get(f'/realapp/connector/{ex_id}')
    assert resp.status_code == 200
    assert b'Telegram' in resp.data
    assert b'Manual Steps' in resp.data


def test_unauthorized_access_blocked(client):
    """Unauthenticated users cannot access admin endpoints."""
    assert client.get('/realapp/select/1').status_code == 403
    assert client.get('/realapp/history').status_code == 403
    assert client.get('/realapp/analytics').status_code == 403
    assert client.get('/realapp/export/csv').status_code == 403
    assert client.get('/realapp/audit').status_code == 403
    assert client.get('/realapp/exercise/1').status_code == 403
    assert client.get('/realapp/connector/1').status_code == 403
    assert client.post('/realapp/revoke/1').status_code == 403
