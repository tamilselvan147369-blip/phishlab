import os
import pytest
from app import create_app
from database import db, Campaign
from social_simulation.models import (
    SocialSimulation, SimulatedConversation, SimulatedMessage,
    SimulationParticipant, SimulationEvent, AwarenessResponse,
    SOCIAL_PLATFORMS
)
from social_simulation.scenarios import seed_default_simulation, AWARENESS_QUIZZES

@pytest.fixture
def app():
    app = create_app(test_config={
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False,
        'ADMIN_USERNAME': 'admin',
        'ADMIN_PASSWORD': 'admin_test_password',
    })
    with app.app_context():
        db.create_all()
        # Seed default social simulation
        seed_default_simulation(db.session)
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


def test_social_blueprint_registered(app):
    """Verify social_sim blueprint is registered with /social prefix."""
    blueprint_names = [bp.name for bp in app.iter_blueprints()]
    assert 'social_sim' in blueprint_names


def test_social_dashboard_renders(app, admin_client):
    """Verify central social media dashboard renders with all 6 platform cards."""
    resp = admin_client.get('/social/dashboard')
    assert resp.status_code == 200
    assert b'WhatsApp' in resp.data
    assert b'Instagram' in resp.data
    assert b'Facebook Messenger' in resp.data
    assert b'Telegram' in resp.data
    assert b'X (Twitter)' in resp.data
    assert b'LinkedIn' in resp.data


def test_all_six_platforms_consent_and_render(app, client):
    """Test full participant onboarding and rendering across all 6 platforms."""
    with app.app_context():
        sim = SocialSimulation.query.first()
        sim_id = sim.id

    for platform_code in SOCIAL_PLATFORMS.keys():
        # 1. Access consent gate
        resp = client.get(f'/social/consent/{platform_code}/{sim_id}')
        assert resp.status_code == 200
        assert b'PhishLab Security Awareness Training' in resp.data

        # 2. Submit consent
        resp = client.post(f'/social/consent/{platform_code}/{sim_id}', data={
            'alias': f'Participant_{platform_code}',
            'consent': 'on'
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b'PHISHLAB TRAINING LAB' in resp.data

        # Verify participant stored with consent
        with app.app_context():
            p = SimulationParticipant.query.filter_by(
                simulation_id=sim_id,
                alias=f'Participant_{platform_code}'
            ).first()
            assert p is not None
            assert p.consent_given is True


def test_interactive_link_click_tracking(app, client):
    """Test simulated link click records event and returns educational feedback."""
    with app.app_context():
        sim = SocialSimulation.query.first()
        conv = SimulatedConversation.query.filter_by(simulation_id=sim.id, platform='whatsapp').first()
        msg = SimulatedMessage.query.filter_by(conversation_id=conv.id).first()
        sim_id = sim.id
        conv_id = conv.id
        msg_id = msg.id

    # Consent first
    client.post(f'/social/consent/whatsapp/{sim_id}', data={'alias': 'LinkTester', 'consent': 'on'})

    resp = client.post('/social/api/track-event', json={
        'simulation_id': sim_id,
        'platform': 'whatsapp',
        'conversation_id': conv_id,
        'message_id': msg_id,
        'event_type': 'link_clicked',
        'details': 'Clicked simulated auth link'
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['status'] == 'success'
    assert 'Simulated Phishing Link' in data['feedback']['title']

    with app.app_context():
        evt = SimulationEvent.query.filter_by(event_type='link_clicked').first()
        assert evt is not None
        assert evt.platform == 'whatsapp'


def test_attachment_preview_tracking(app, client):
    """Test simulated document inspection records event and safe preview feedback."""
    with app.app_context():
        sim = SocialSimulation.query.first()
        sim_id = sim.id

    client.post(f'/social/consent/linkedin/{sim_id}', data={'alias': 'DocTester', 'consent': 'on'})

    resp = client.post('/social/api/track-event', json={
        'simulation_id': sim_id,
        'platform': 'linkedin',
        'event_type': 'attachment_previewed',
        'details': 'Previewed Executive_Job_Description_NDA.pdf'
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['status'] == 'success'
    assert 'Simulated Document' in data['feedback']['title']

    with app.app_context():
        evt = SimulationEvent.query.filter_by(event_type='attachment_previewed').first()
        assert evt is not None


def test_suspicious_message_reporting(app, client):
    """Test reporting a suspicious message triggers positive reinforcement feedback."""
    with app.app_context():
        sim = SocialSimulation.query.first()
        sim_id = sim.id

    client.post(f'/social/consent/telegram/{sim_id}', data={'alias': 'VigilantUser', 'consent': 'on'})

    resp = client.post('/social/api/track-event', json={
        'simulation_id': sim_id,
        'platform': 'telegram',
        'event_type': 'suspicious_reported',
        'details': 'Reported fake verification bot'
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['status'] == 'success'
    assert 'Vigilance' in data['feedback']['title']

    with app.app_context():
        evt = SimulationEvent.query.filter_by(event_type='suspicious_reported').first()
        assert evt is not None


def test_awareness_quiz_correct_and_incorrect(app, client):
    """Test awareness quiz submission, answer evaluation, and explanation recording."""
    with app.app_context():
        sim = SocialSimulation.query.first()
        sim_id = sim.id
        quiz = AWARENESS_QUIZZES['instagram']
        correct_opt = quiz['correct']
        wrong_opt = [o for o in quiz['options'] if o != correct_opt][0]

    client.post(f'/social/consent/instagram/{sim_id}', data={'alias': 'QuizUser', 'consent': 'on'})

    # 1. Submit Correct Answer
    resp = client.post('/social/api/submit-quiz', json={
        'simulation_id': sim_id,
        'platform': 'instagram',
        'selected_option': correct_opt
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['is_correct'] is True
    assert quiz['explanation'] in data['explanation']

    # 2. Submit Incorrect Answer
    resp2 = client.post('/social/api/submit-quiz', json={
        'simulation_id': sim_id,
        'platform': 'instagram',
        'selected_option': wrong_opt
    })
    assert resp2.status_code == 200
    data2 = resp2.get_json()
    assert data2['is_correct'] is False

    with app.app_context():
        responses = AwarenessResponse.query.filter_by(platform='instagram').all()
        assert len(responses) == 2


def test_create_custom_simulation_campaign(app, admin_client):
    """Test admin creating a new simulation campaign with selected platforms."""
    resp = admin_client.post('/social/simulation/create', data={
        'name': 'Corporate Financial Team Drill',
        'description': 'Targeting finance department on Telegram and LinkedIn',
        'platforms': ['telegram', 'linkedin'],
        'status': 'active'
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b'Corporate Financial Team Drill' in resp.data

    with app.app_context():
        new_sim = SocialSimulation.query.filter_by(name='Corporate Financial Team Drill').first()
        assert new_sim is not None
        assert 'telegram' in new_sim.get_platform_list()
        assert 'linkedin' in new_sim.get_platform_list()


def test_toggle_simulation_status(app, admin_client):
    """Test pausing and resuming simulation."""
    with app.app_context():
        sim = SocialSimulation.query.first()
        sim_id = sim.id

    # Pause
    resp = admin_client.post(f'/social/simulation/{sim_id}/toggle-status', follow_redirects=True)
    assert resp.status_code == 200
    with app.app_context():
        s = db.session.get(SocialSimulation, sim_id)
        assert s.status == 'paused'

    # Resume
    resp = admin_client.post(f'/social/simulation/{sim_id}/toggle-status', follow_redirects=True)
    assert resp.status_code == 200
    with app.app_context():
        s = db.session.get(SocialSimulation, sim_id)
        assert s.status == 'active'


def test_analytics_and_csv_export(app, admin_client):
    """Test cross-platform analytics and CSV data export."""
    resp = admin_client.get('/social/analytics')
    assert resp.status_code == 200
    assert b'Platform Resilience Comparison' in resp.data

    resp_csv = admin_client.get('/social/export/csv')
    assert resp_csv.status_code == 200
    assert resp_csv.mimetype == 'text/csv'
    assert b'Event ID,Simulation ID,Participant ID,Platform' in resp_csv.data


def test_admin_authorization_enforced(client):
    """Verify unauthorized users cannot access admin management routes."""
    assert client.get('/social/dashboard').status_code == 403
    assert client.get('/social/simulation/create').status_code == 403
    assert client.get('/social/analytics').status_code == 403
    assert client.get('/social/timeline').status_code == 403
    assert client.get('/social/export/csv').status_code == 403
    assert client.post('/social/simulation/1/toggle-status').status_code == 403


def test_paused_simulation_shows_inactive_screen(app, client):
    """Verify participant receives inactive notice when simulation is paused."""
    with app.app_context():
        sim = SocialSimulation.query.first()
        sim.status = 'paused'
        db.session.commit()
        sim_id = sim.id

    resp = client.get(f'/social/consent/whatsapp/{sim_id}')
    assert resp.status_code == 200
    assert b'Exercise Paused or Completed' in resp.data


def test_viewing_conversation_records_message_viewed_event(app, client):
    """Verify participant viewing a platform conversation records message_viewed event."""
    with app.app_context():
        sim = SocialSimulation.query.first()
        sim_id = sim.id
        conv = SimulatedConversation.query.filter_by(simulation_id=sim_id, platform='facebook_messenger').first()
        conv_id = conv.id

    # Consent
    client.post(f'/social/consent/facebook_messenger/{sim_id}', data={'alias': 'FbUser', 'consent': 'on'})

    # View conversation
    resp = client.get(f'/social/platform/facebook_messenger/{sim_id}?conv_id={conv_id}')
    assert resp.status_code == 200
    assert b'Messenger Security System' in resp.data or b'Q4 Project Alpha Team' in resp.data

    with app.app_context():
        evt = SimulationEvent.query.filter_by(platform='facebook_messenger', event_type='message_viewed').first()
        assert evt is not None
        assert 'Viewed conversation' in evt.details


def test_quiz_completion_records_exercise_completed(app, client):
    """Verify submitting awareness quiz records exercise_completed event."""
    with app.app_context():
        sim = SocialSimulation.query.first()
        sim_id = sim.id
        quiz = AWARENESS_QUIZZES['x']
        correct_opt = quiz['correct']

    client.post(f'/social/consent/x/{sim_id}', data={'alias': 'XUser', 'consent': 'on'})

    resp = client.post('/social/api/submit-quiz', json={
        'simulation_id': sim_id,
        'platform': 'x',
        'selected_option': correct_opt
    })
    assert resp.status_code == 200

    with app.app_context():
        evt_complete = SimulationEvent.query.filter_by(platform='x', event_type='exercise_completed').first()
        assert evt_complete is not None
        assert 'Completed x simulation' in evt_complete.details


def test_timeline_and_manage_routes(app, admin_client):
    """Verify timeline stream and simulation management views render properly."""
    with app.app_context():
        sim = SocialSimulation.query.first()
        sim_id = sim.id

    # Manage simulation
    resp_manage = admin_client.get(f'/social/simulation/{sim_id}/manage')
    assert resp_manage.status_code == 200
    assert b'Participant Simulation Portals' in resp_manage.data
    assert b'Configured Conversations' in resp_manage.data

    # Event timeline
    resp_timeline = admin_client.get('/social/timeline')
    assert resp_timeline.status_code == 200
    assert b'Live Simulation Event Timeline' in resp_timeline.data


def test_unified_generator_dashboard_renders(app, admin_client):
    """Verify unified generator dashboard renders with 11 sections and 6 platforms."""
    resp = admin_client.get('/social/generator')
    assert resp.status_code == 200
    assert b'UNIFIED SOCIAL MEDIA GENERATOR' in resp.data
    assert b'1. Overview' in resp.data
    assert b'2. AI Scenario Generator' in resp.data
    assert b'5. Message Editor' in resp.data
    assert b'6. Simulation Preview' in resp.data
    assert b'WhatsApp' in resp.data
    assert b'Instagram' in resp.data
    assert b'LinkedIn' in resp.data


def test_ai_scenario_generation_api(app, admin_client):
    """Test AI scenario generator API across educational categories and languages (EN & Tamil)."""
    # 1. English generation
    resp_en = admin_client.post('/social/generator/api/generate', json={
        'category': 'account_security',
        'platform': 'whatsapp',
        'tone': 'Urgent',
        'language': 'en',
        'complexity': 'Intermediate',
        'provider': 'local'
    })
    assert resp_en.status_code == 200
    data_en = resp_en.get_json()
    assert data_en['status'] == 'success'
    assert 'Account Security' in data_en['scenario']['title']
    assert 'whatsapp' in data_en['scenario']['platform']

    # 2. Tamil generation (multilingual)
    resp_ta = admin_client.post('/social/generator/api/generate', json={
        'category': 'account_security',
        'platform': 'telegram',
        'tone': 'Urgent',
        'language': 'ta',
        'complexity': 'Intermediate',
        'provider': 'local'
    })
    assert resp_ta.status_code == 200
    data_ta = resp_ta.get_json()
    assert data_ta['status'] == 'success'
    assert 'கணக்கு' in data_ta['scenario']['message_content']


def test_platform_adapters_preview_all(app, admin_client):
    """Test platform rendering adapters for all 6 platforms."""
    resp = admin_client.post('/social/generator/api/preview-all', json={
        'title': 'Test Multi-Platform Lure',
        'fictional_sender': 'Security Auditor',
        'message_content': 'Please verify your profile credentials immediately.',
        'simulated_link': 'https://verify-test.test/sso',
        'simulated_attachment': 'Security_Check.pdf'
    })
    assert resp.status_code == 200
    previews = resp.get_json()['previews']
    assert 'whatsapp' in previews
    assert 'instagram' in previews
    assert 'facebook_messenger' in previews
    assert 'telegram' in previews
    assert 'x' in previews
    assert 'linkedin' in previews


def test_save_and_export_scenario(app, admin_client):
    """Test persisting scenario and exporting JSON simulation configuration."""
    resp_save = admin_client.post('/social/generator/api/save-scenario', json={
        'title': 'Exportable Corporate Phish Drill',
        'category': 'fake_recruitment',
        'platform': 'linkedin',
        'fictional_sender': 'Elena Vance',
        'message_content': 'Executive recruitment offer attached.',
        'is_template': True
    })
    assert resp_save.status_code == 200
    scenario_id = resp_save.get_json()['scenario_id']

    # Export scenario JSON
    resp_export = admin_client.get(f'/social/generator/export/{scenario_id}')
    assert resp_export.status_code == 200
    assert resp_export.is_json
    assert resp_export.get_json()['title'] == 'Exportable Corporate Phish Drill'


def test_create_campaign_from_generator(app, admin_client):
    """Test directly launching an active SocialSimulation campaign from the generator."""
    resp = admin_client.post('/social/generator/api/create-campaign', json={
        'campaign_name': 'Live Drill From Generator',
        'title': 'Emergency 2FA Alert',
        'category': 'account_security',
        'platform': 'whatsapp',
        'fictional_sender': 'Security Ops',
        'message_content': 'Urgent token reset required.',
        'platforms': ['whatsapp', 'telegram']
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['status'] == 'success'
    sim_id = data['simulation_id']

    with app.app_context():
        sim = db.session.get(SocialSimulation, sim_id)
        assert sim is not None
        assert 'whatsapp' in sim.get_platform_list()
        assert 'telegram' in sim.get_platform_list()


def test_generator_access_control(client):
    """Verify unauthorized users cannot access generator or its generation endpoints."""
    assert client.get('/social/generator').status_code == 403
    assert client.post('/social/generator/api/generate').status_code == 403
    assert client.post('/social/generator/api/preview-all').status_code == 403
    assert client.post('/social/generator/api/save-scenario').status_code == 403
    assert client.post('/social/generator/api/create-campaign').status_code == 403


