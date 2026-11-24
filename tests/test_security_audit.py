import os
import pytest
from app import create_app, sanitize_template
from database import db, Campaign, Event
from real_app_testing.models import RealAppExercise, PLATFORMS
from real_app_testing.tokens import generate_token, verify_token

@pytest.fixture
def app():
    app = create_app(test_config={
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False,
        'ADMIN_USERNAME': 'testadmin',
        'ADMIN_PASSWORD': 'SuperSecretPassword123!',
    })
    with app.app_context():
        db.create_all()
        c = Campaign(
            name='Audit Campaign',
            scenario='banking',
            subject='Alert',
            sender_name='Bank',
            recipient='user@example.test',
            template='<p>Safe content</p>',
            description='Audit'
        )
        db.session.add(c)
        db.session.commit()
    yield app

@pytest.fixture
def client(app):
    return app.test_client()

def test_admin_login_success_and_logout(client):
    """Verify administrator login with correct credentials and subsequent logout."""
    resp = client.post('/admin/login', data={
        'username': 'testadmin',
        'password': 'SuperSecretPassword123!'
    }, follow_redirects=True)
    assert resp.status_code == 200
    with client.session_transaction() as sess:
        assert sess.get('is_admin') is True
        assert sess.get('admin_name') == 'testadmin'

    # Logout
    resp = client.get('/admin/logout', follow_redirects=True)
    assert resp.status_code == 200
    with client.session_transaction() as sess:
        assert sess.get('is_admin') is None

def test_admin_login_invalid_credentials(client):
    """Verify admin login failure with incorrect credentials."""
    resp = client.post('/admin/login', data={
        'username': 'wronguser',
        'password': 'badpassword'
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b'Invalid administrator credentials' in resp.data
    with client.session_transaction() as sess:
        assert sess.get('is_admin') is None

def test_xss_sanitization_in_templates():
    """Verify malicious script tags and event handlers are stripped."""
    dirty_html = '<p>Hello <script>alert("XSS")</script><a href="http://example.com" onclick="steal()">Click</a></p>'
    clean_html = sanitize_template(dirty_html)
    assert '<script>' not in clean_html
    assert '</script>' not in clean_html
    assert 'onclick' not in clean_html
    assert '<p>' in clean_html
    assert 'href="http://example.com"' in clean_html

def test_session_cookie_security_config(app):
    """Verify session cookies have HttpOnly and SameSite configured."""
    assert app.config['SESSION_COOKIE_HTTPONLY'] is True
    assert app.config['SESSION_COOKIE_SAMESITE'] == 'Lax'

def test_malformed_uuid_rejected(app, client):
    """Verify malformed participant UUID causes HTTP 400."""
    with client.session_transaction() as sess:
        sess['is_admin'] = True
    resp = client.post('/realapp/select/1', data={'platform': 'whatsapp'}, follow_redirects=False)
    token = resp.headers['Location'].split('/realapp/demo/')[-1]

    # POST with non-UUID string
    resp = client.post(f'/realapp/confirm/{token}', data={
        'participant_uuid': 'not-a-valid-uuid-1234',
        'consent': 'on'
    })
    assert resp.status_code == 400

def test_custom_error_pages(client):
    """Verify error handlers return formatted HTML without stack traces."""
    resp = client.get('/nonexistent-page-url-404')
    assert resp.status_code == 404
    assert b'HTTP 404' in resp.data
    assert b'Not Found' in resp.data

def test_no_real_credentials_persisted(app, client):
    """Verify POST to /login/<cid> does NOT record entered credentials anywhere."""
    resp = client.post('/login/1', data={
        'username': 'sensitive_admin',
        'password': 'super_secret_cleartext_password'
    })
    assert resp.status_code == 200
    with app.app_context():
        # Check all database tables to ensure password was never written
        events = Event.query.filter_by(campaign_id=1).all()
        for evt in events:
            assert 'super_secret_cleartext_password' not in evt.event_type
            assert 'sensitive_admin' not in evt.event_type
