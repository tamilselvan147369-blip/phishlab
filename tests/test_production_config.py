"""Automated tests for production hosting configuration, health checks, and security."""

import os
import pytest
from werkzeug.security import generate_password_hash
from app import create_app
from database import db


def test_health_check_endpoint():
    """Verify production /healthz and /health endpoints return 200 OK and database status."""
    app = create_app(test_config={
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False,
    })
    client = app.test_client()

    for endpoint in ['/healthz', '/health']:
        resp = client.get(endpoint)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['status'] == 'healthy'
        assert data['database'] == 'connected'
        assert 'timestamp' in data


def test_postgres_url_normalization():
    """Verify Render-style postgres:// URLs are converted to postgresql+psycopg2:// for SQLAlchemy."""
    from scripts.migrate_sqlite_to_postgres import normalize_db_url

    raw_render_url = "postgres://phishlab_user:secret_pass@ep-xyz.oregon-postgres.render.com/phishlab_db"
    normalized = normalize_db_url(raw_render_url)
    assert normalized.startswith("postgresql+psycopg2://")
    assert "postgres://" not in normalized

    # Also test postgresql:// without driver prefix
    raw_standard_url = "postgresql://phishlab_user:secret_pass@ep-xyz.oregon-postgres.render.com/phishlab_db"
    norm_standard = normalize_db_url(raw_standard_url)
    assert norm_standard.startswith("postgresql+psycopg2://")


def test_admin_password_hash_authentication():
    """Verify production admin authentication supports secure password hashing."""
    test_password = "ProductionComplexPassword2026!"
    hashed = generate_password_hash(test_password)

    app = create_app(test_config={
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False,
        'ADMIN_USERNAME': 'sec_admin',
        'ADMIN_PASSWORD_HASH': hashed,
    })
    client = app.test_client()

    # Wrong password fails
    resp_fail = client.post('/admin/login', data={'username': 'sec_admin', 'password': 'wrong_password'}, follow_redirects=True)
    assert b"Invalid administrator credentials" in resp_fail.data

    # Correct hashed password succeeds
    resp_ok = client.post('/admin/login', data={'username': 'sec_admin', 'password': test_password}, follow_redirects=True)
    assert b"Logged in successfully as Administrator" in resp_ok.data


def test_gunicorn_conf_parsing():
    """Verify gunicorn.conf.py parses properly and binds to specified port."""
    gconf = {}
    with open('gunicorn.conf.py', 'r', encoding='utf-8') as f:
        exec(f.read(), gconf)

    assert '0.0.0.0' in gconf['bind']
    assert gconf['worker_class'] == 'gthread'
    assert gconf['threads'] >= 4
    assert gconf['timeout'] >= 60


def test_login_rate_limiting():
    """Verify brute-force protection locks out after 5 consecutive failed attempts."""
    from auth import clear_failed_logins

    app = create_app(test_config={
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False,
        'ADMIN_USERNAME': 'admin',
        'ADMIN_PASSWORD': 'SuperSecretPassword!',
    })
    client = app.test_client()
    clear_failed_logins('127.0.0.1')

    # Trigger 5 failed attempts
    for _ in range(5):
        resp = client.post('/admin/login', data={'username': 'admin', 'password': 'wrong'}, environ_base={'REMOTE_ADDR': '127.0.0.1'})
        assert resp.status_code == 200

    # 6th attempt must be rate-limited (429 Too Many Requests)
    resp_blocked = client.post('/admin/login', data={'username': 'admin', 'password': 'SuperSecretPassword!'}, environ_base={'REMOTE_ADDR': '127.0.0.1'})
    assert resp_blocked.status_code == 429
    assert b"Too many failed login attempts" in resp_blocked.data

    # Cleanup
    clear_failed_logins('127.0.0.1')

