import pytest
from app import create_app
from database import db, Campaign, Event

@pytest.fixture
def app():
    app = create_app(test_config={
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False,
        'ALLOWED_RECIPIENT_DOMAIN': 'example.test',
    })
    with app.app_context():
        db.create_all()
        c = Campaign(
            name='Local Sim Campaign',
            scenario='corporate',
            subject='Urgent Update',
            sender_name='IT Admin',
            recipient='alice@example.test',
            template='<p>Click <a href="/login/1">here</a> to verify.</p>',
            description='Test Local Sim'
        )
        db.session.add(c)
        db.session.commit()
    yield app

@pytest.fixture
def client(app):
    return app.test_client()

def test_dashboard_renders(client):
    resp = client.get('/')
    assert resp.status_code == 200
    assert b'PhishLab' in resp.data

def test_campaign_history_and_detail(client):
    resp = client.get('/campaigns')
    assert resp.status_code == 200
    assert b'Local Sim Campaign' in resp.data

    resp = client.get('/campaign/1')
    assert resp.status_code == 200
    assert b'Urgent Update' in resp.data

def test_email_preview_records_opened(app, client):
    resp = client.get('/campaign/1/preview')
    assert resp.status_code == 200
    with app.app_context():
        opened_event = Event.query.filter_by(campaign_id=1, event_type='email_opened').first()
        assert opened_event is not None

def test_demo_login_click_and_submit(app, client):
    # GET registers click
    resp = client.get('/login/1')
    assert resp.status_code == 200
    with app.app_context():
        click_event = Event.query.filter_by(campaign_id=1, event_type='demo_link_clicked').first()
        assert click_event is not None

    # POST registers form submit without saving credentials
    resp = client.post('/login/1', data={'username': 'victim', 'password': 'secretpassword'})
    assert resp.status_code == 200
    with app.app_context():
        submit_event = Event.query.filter_by(campaign_id=1, event_type='demo_form_submitted').first()
        assert submit_event is not None

def test_campaign_results(client):
    resp = client.get('/campaign/1/results')
    assert resp.status_code == 200
