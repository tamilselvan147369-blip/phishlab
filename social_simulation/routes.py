"""Routes for the Multi-Platform Social Media Simulation Engine.

Provides administrative controls, simulation campaign management,
cross-platform comparison analytics, CSV exports, and 6 distinct
platform-specific simulation environments.
"""

from functools import wraps
import os
import csv
import io
import uuid
from bleach import clean

from flask import (
    render_template, request, redirect, url_for, flash,
    abort, current_app, session, jsonify, Response
)
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, SelectMultipleField, SubmitField
from wtforms.validators import DataRequired, Optional

from database import db
from . import social_sim_bp
from .models import (
    SocialSimulation, SocialMessageTemplate, SimulatedConversation,
    SimulatedMessage, SimulationParticipant, SimulationEvent,
    AwarenessResponse, GeneratedScenario, GeneratedMessage,
    SimulationConfiguration, SOCIAL_PLATFORMS, utcnow_naive
)
from .scenarios import seed_default_simulation, AWARENESS_QUIZZES, DEFAULT_SCENARIOS
from .generator import (
    UnifiedSimulationEngine, SCENARIO_CATEGORIES, get_ai_provider,
    get_platform_adapter, PLATFORM_ADAPTERS
)

# Authentication helper (from decoupled auth module to prevent circular imports)
from auth import admin_required

# ---------------------------------------------------------------------------
# Forms
# ---------------------------------------------------------------------------
class SimulationCampaignForm(FlaskForm):
    name = StringField('Campaign Name', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[Optional()])
    platforms = SelectMultipleField(
        'Target Platforms',
        choices=[(k, v) for k, v in SOCIAL_PLATFORMS.items()],
        default=list(SOCIAL_PLATFORMS.keys()),
        validators=[DataRequired()]
    )
    status = SelectField(
        'Initial Status',
        choices=[('active', 'Active'), ('paused', 'Paused')],
        default='active'
    )
    submit = SubmitField('Create Simulation')


class MessageTemplateForm(FlaskForm):
    platform = SelectField(
        'Platform',
        choices=[(k, v) for k, v in SOCIAL_PLATFORMS.items()],
        validators=[DataRequired()]
    )
    scenario_type = StringField('Scenario Type (e.g., urgent_security, job_offer)', validators=[DataRequired()])
    sender_name = StringField('Sender Name', validators=[DataRequired()])
    sender_handle = StringField('Sender Handle (@username)', validators=[Optional()])
    content = TextAreaField('Message Content', validators=[DataRequired()])
    simulated_link = StringField('Simulated Link URL', validators=[Optional()])
    attachment_name = StringField('Simulated Attachment Name', validators=[Optional()])
    attachment_type = SelectField('Attachment Type', choices=[('', 'None'), ('pdf', 'PDF Document'), ('image', 'Image'), ('doc', 'Word Document')])
    red_flags = TextAreaField('Educational Red Flags & Indicators', validators=[Optional()])
    submit = SubmitField('Save Template')


# =====================================================================
# ADMIN ROUTES
# =====================================================================

@social_sim_bp.route('/')
@social_sim_bp.route('/dashboard')
@admin_required
def dashboard():
    """Main Social Simulation Central Dashboard with 6 platform cards."""
    # Ensure default simulation is seeded
    seed_default_simulation(db.session)

    simulations = SocialSimulation.query.order_by(SocialSimulation.created_at.desc()).all()
    total_simulations = len(simulations)
    total_participants = SimulationParticipant.query.count()
    total_events = SimulationEvent.query.count()

    # Per-platform metrics
    platform_cards = {}
    for code, name in SOCIAL_PLATFORMS.items():
        conv_count = SimulatedConversation.query.filter_by(platform=code).count()
        event_count = SimulationEvent.query.filter_by(platform=code).count()
        reported_count = SimulationEvent.query.filter_by(platform=code, event_type='suspicious_reported').count()
        link_clicked = SimulationEvent.query.filter_by(platform=code, event_type='link_clicked').count()
        platform_cards[code] = {
            'name': name,
            'conversations': conv_count,
            'events': event_count,
            'reported': reported_count,
            'link_clicked': link_clicked,
        }

    return render_template(
        'social_sim/dashboard.html',
        simulations=simulations,
        total_simulations=total_simulations,
        total_participants=total_participants,
        total_events=total_events,
        platform_cards=platform_cards,
    )


@social_sim_bp.route('/simulation/create', methods=['GET', 'POST'])
@admin_required
def create_simulation():
    """Create a new multi-platform simulation exercise."""
    form = SimulationCampaignForm()
    if form.validate_on_submit():
        platform_str = ','.join(form.platforms.data)
        sim = SocialSimulation(
            name=form.name.data,
            description=form.description.data or '',
            platforms=platform_str,
            status=form.status.data,
            created_at=utcnow_naive(),
        )
        db.session.add(sim)
        db.session.commit()

        # Clone default scenarios for selected platforms
        for p in form.platforms.data:
            conv_templates = DEFAULT_SCENARIOS.get(p, [])
            for c_data in conv_templates:
                conv = SimulatedConversation(
                    simulation_id=sim.id,
                    platform=p,
                    conversation_type=c_data.get('type', 'one_to_one'),
                    title=c_data['title'],
                    sender_avatar=c_data.get('avatar', '💬'),
                    subtitle=c_data.get('subtitle', ''),
                    is_request=c_data.get('is_request', False),
                    created_at=utcnow_naive(),
                )
                db.session.add(conv)
                db.session.flush()

                for m_data in c_data.get('messages', []):
                    msg = SimulatedMessage(
                        conversation_id=conv.id,
                        sender_name=m_data['sender'],
                        sender_handle=m_data.get('handle', ''),
                        sender_avatar=c_data.get('avatar', '💬'),
                        is_from_user=m_data.get('is_user', False),
                        content=m_data['content'],
                        simulated_link=m_data.get('link', ''),
                        attachment_name=m_data.get('attachment', ''),
                        attachment_type=m_data.get('att_type', ''),
                        read_status=m_data.get('status', 'read'),
                        is_suspicious=m_data.get('is_suspicious', False),
                        educational_notes=m_data.get('notes', ''),
                        timestamp=utcnow_naive(),
                    )
                    db.session.add(msg)

        db.session.commit()
        flash(f'Simulation "{sim.name}" created successfully.', 'success')
        return redirect(url_for('social_sim.manage_simulation', sim_id=sim.id))

    return render_template('social_sim/create_simulation.html', form=form)


@social_sim_bp.route('/simulation/<int:sim_id>/manage')
@admin_required
def manage_simulation(sim_id):
    """Manage conversations and participant links for a specific simulation."""
    sim = db.get_or_404(SocialSimulation, sim_id)
    conversations = SimulatedConversation.query.filter_by(simulation_id=sim.id).all()
    participants = SimulationParticipant.query.filter_by(simulation_id=sim.id).all()
    return render_template(
        'social_sim/manage_simulation.html',
        simulation=sim,
        conversations=conversations,
        participants=participants,
        platforms=SOCIAL_PLATFORMS,
    )


@social_sim_bp.route('/simulation/<int:sim_id>/toggle-status', methods=['POST'])
@admin_required
def toggle_status(sim_id):
    """Toggle simulation between active and paused."""
    sim = db.get_or_404(SocialSimulation, sim_id)
    sim.status = 'paused' if sim.status == 'active' else 'active'
    db.session.commit()
    flash(f'Simulation status updated to {sim.status}.', 'info')
    return redirect(url_for('social_sim.manage_simulation', sim_id=sim.id))


@social_sim_bp.route('/analytics')
@admin_required
def analytics():
    """Cross-platform comparison analytics."""
    simulations = SocialSimulation.query.all()
    total_participants = SimulationParticipant.query.count()
    total_events = SimulationEvent.query.count()
    total_responses = AwarenessResponse.query.count()
    correct_responses = AwarenessResponse.query.filter_by(is_correct=True).count()

    overall_accuracy = round((correct_responses / total_responses * 100), 1) if total_responses > 0 else 0

    platform_stats = {}
    for code, name in SOCIAL_PLATFORMS.items():
        views = SimulationEvent.query.filter_by(platform=code, event_type='message_viewed').count()
        clicks = SimulationEvent.query.filter_by(platform=code, event_type='link_clicked').count()
        attachments = SimulationEvent.query.filter_by(platform=code, event_type='attachment_previewed').count()
        reports = SimulationEvent.query.filter_by(platform=code, event_type='suspicious_reported').count()
        completions = SimulationEvent.query.filter_by(platform=code, event_type='exercise_completed').count()
        total_p_responses = AwarenessResponse.query.filter_by(platform=code).count()
        correct_p = AwarenessResponse.query.filter_by(platform=code, is_correct=True).count()
        acc = round((correct_p / total_p_responses * 100), 1) if total_p_responses > 0 else 0

        platform_stats[code] = {
            'name': name,
            'views': views,
            'clicks': clicks,
            'attachments': attachments,
            'reports': reports,
            'completions': completions,
            'accuracy': acc,
            'total_quizzes': total_p_responses,
        }

    return render_template(
        'social_sim/analytics.html',
        simulations=simulations,
        total_participants=total_participants,
        total_events=total_events,
        overall_accuracy=overall_accuracy,
        platform_stats=platform_stats,
    )


@social_sim_bp.route('/timeline')
@admin_required
def timeline():
    """Real-time event stream across all platforms."""
    events = SimulationEvent.query.order_by(SimulationEvent.timestamp.desc()).limit(100).all()
    return render_template('social_sim/timeline.html', events=events)


@social_sim_bp.route('/export/csv')
@admin_required
def export_csv():
    """Export all simulation events and awareness metrics to CSV."""
    events = SimulationEvent.query.order_by(SimulationEvent.timestamp.desc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'Event ID', 'Simulation ID', 'Participant ID', 'Platform',
        'Conversation ID', 'Message ID', 'Event Type', 'Details', 'Timestamp'
    ])
    for e in events:
        writer.writerow([
            e.id, e.simulation_id, e.participant_id or '',
            e.platform, e.conversation_id or '', e.message_id or '',
            e.event_type, e.details or '',
            e.timestamp.isoformat() if e.timestamp else ''
        ])
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=phishlab_social_simulation_events.csv'}
    )


# =====================================================================
# PARTICIPANT SIMULATION ROUTES (All 6 Platforms)
# =====================================================================

@social_sim_bp.route('/consent/<platform>/<int:sim_id>', methods=['GET', 'POST'])
def consent_gate(platform, sim_id):
    """Explicit consent and participant onboarding for a training platform."""
    if platform not in SOCIAL_PLATFORMS:
        abort(404)
    sim = db.get_or_404(SocialSimulation, sim_id)
    if sim.status != 'active':
        return render_template('social_sim/inactive.html', simulation=sim)

    if request.method == 'POST':
        alias = request.form.get('alias', 'Participant').strip() or 'Participant'
        participant = SimulationParticipant(
            simulation_id=sim.id,
            participant_uuid=str(uuid.uuid4()),
            alias=alias,
            consent_given=True,
            consent_timestamp=utcnow_naive(),
            created_at=utcnow_naive(),
        )
        db.session.add(participant)
        db.session.commit()

        # Save participant uuid in session
        session[f'sim_participant_{sim.id}'] = participant.participant_uuid

        # Record exercise start event
        evt = SimulationEvent(
            simulation_id=sim.id,
            participant_id=participant.id,
            platform=platform,
            event_type='exercise_started',
            details=f'Participant {alias} accepted consent for {SOCIAL_PLATFORMS[platform]} simulation',
            timestamp=utcnow_naive(),
        )
        db.session.add(evt)
        db.session.commit()

        return redirect(url_for('social_sim.simulate_platform', platform=platform, sim_id=sim.id))

    return render_template(
        'social_sim/consent.html',
        platform=platform,
        platform_name=SOCIAL_PLATFORMS[platform],
        simulation=sim,
    )


@social_sim_bp.route('/platform/<platform>/<int:sim_id>')
def simulate_platform(platform, sim_id):
    """Main simulation environment for the selected social platform."""
    if platform not in SOCIAL_PLATFORMS:
        abort(404)
    sim = db.get_or_404(SocialSimulation, sim_id)

    # Participant resolution
    part_uuid = session.get(f'sim_participant_{sim.id}')
    participant = None
    if part_uuid:
        participant = SimulationParticipant.query.filter_by(
            simulation_id=sim.id,
            participant_uuid=part_uuid
        ).first()

    # Load conversations for this platform
    conversations = SimulatedConversation.query.filter_by(
        simulation_id=sim.id,
        platform=platform
    ).all()

    # Fallback to default conversations if none generated
    if not conversations:
        seed_default_simulation(db.session)
        conversations = SimulatedConversation.query.filter_by(
            simulation_id=sim.id,
            platform=platform
        ).all()

    active_conv = conversations[0] if conversations else None
    active_conv_id = request.args.get('conv_id', type=int)
    if active_conv_id:
        selected = next((c for c in conversations if c.id == active_conv_id), None)
        if selected:
            active_conv = selected

    # Record conversation and message viewed event
    if participant and active_conv:
        evt = SimulationEvent(
            simulation_id=sim.id,
            participant_id=participant.id,
            platform=platform,
            conversation_id=active_conv.id,
            event_type='message_viewed',
            details=f'Viewed conversation: {active_conv.title} ({len(active_conv.messages)} messages)',
            timestamp=utcnow_naive(),
        )
        db.session.add(evt)
        db.session.commit()

    quiz_data = AWARENESS_QUIZZES.get(platform, {})

    template_map = {
        'whatsapp': 'social_sim/platforms/whatsapp.html',
        'instagram': 'social_sim/platforms/instagram.html',
        'facebook_messenger': 'social_sim/platforms/messenger.html',
        'telegram': 'social_sim/platforms/telegram.html',
        'x': 'social_sim/platforms/x.html',
        'linkedin': 'social_sim/platforms/linkedin.html',
    }

    return render_template(
        template_map[platform],
        platform=platform,
        platform_name=SOCIAL_PLATFORMS[platform],
        simulation=sim,
        conversations=conversations,
        active_conv=active_conv,
        participant=participant,
        quiz=quiz_data,
    )


def _parse_int(val):
    """Safely convert a value to int or return None."""
    if val is None or val == '':
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


# =====================================================================
# INTERACTION API ENDPOINTS
# =====================================================================

@social_sim_bp.route('/api/track-event', methods=['POST'])
def track_event():
    """Track clicks on links, attachment previews, and suspicious message reports."""
    data = request.get_json(silent=True) or request.form
    sim_id = _parse_int(data.get('simulation_id'))
    platform = data.get('platform')
    event_type = data.get('event_type')
    conv_id = _parse_int(data.get('conversation_id'))
    msg_id = _parse_int(data.get('message_id'))
    details = data.get('details', '')

    if not sim_id or not platform or not event_type:
        return jsonify({'status': 'error', 'message': 'Missing parameters'}), 400

    part_uuid = session.get(f'sim_participant_{sim_id}')
    participant = SimulationParticipant.query.filter_by(
        simulation_id=sim_id,
        participant_uuid=part_uuid
    ).first() if part_uuid else None

    evt = SimulationEvent(
        simulation_id=sim_id,
        participant_id=participant.id if participant else None,
        platform=platform,
        conversation_id=conv_id,
        message_id=msg_id,
        event_type=event_type,
        details=details,
        timestamp=utcnow_naive(),
    )
    db.session.add(evt)
    db.session.commit()

    feedback = {}
    if event_type == 'link_clicked':
        feedback = {
            'title': '⚠️ Simulated Phishing Link Detected!',
            'type': 'warning',
            'message': 'You clicked a simulated phishing link. In a real cyber attack, this could lead to credential harvesting or malware download.',
            'indicators': 'Red flags: Unsolicited link, urgency tactic, external unverified domain.'
        }
    elif event_type == 'attachment_previewed':
        feedback = {
            'title': '📎 Simulated Document Inspection',
            'type': 'info',
            'message': 'This is a simulated safe attachment demonstration. In social engineering attacks, weaponized PDFs or executables are frequently used.',
            'indicators': 'Best practice: Verify sender identity via secondary channel before opening attachments.'
        }
    elif event_type == 'suspicious_reported':
        feedback = {
            'title': '🛡️ Excellent Vigilance!',
            'type': 'success',
            'message': 'You successfully identified and reported this suspicious communication! Your security team has been notified in this simulation.',
            'indicators': 'Reporting suspicious messages stops phishing campaigns in their tracks.'
        }

    return jsonify({'status': 'success', 'event_id': evt.id, 'feedback': feedback})


@social_sim_bp.route('/api/submit-quiz', methods=['POST'])
def submit_quiz():
    """Record participant response to awareness question and provide educational feedback."""
    data = request.get_json(silent=True) or request.form
    sim_id = _parse_int(data.get('simulation_id'))
    platform = data.get('platform')
    selected_option = str(data.get('selected_option', '')).strip()

    if not sim_id or not platform or not selected_option:
        return jsonify({'status': 'error', 'message': 'Missing parameters'}), 400

    quiz = AWARENESS_QUIZZES.get(platform)
    if not quiz:
        return jsonify({'status': 'error', 'message': 'Quiz not found'}), 404

    is_correct = (selected_option == quiz['correct'])

    part_uuid = session.get(f'sim_participant_{sim_id}')
    participant = SimulationParticipant.query.filter_by(
        simulation_id=sim_id,
        participant_uuid=part_uuid
    ).first() if part_uuid else None

    resp = AwarenessResponse(
        simulation_id=sim_id,
        participant_id=participant.id if participant else None,
        platform=platform,
        question_text=quiz['question'],
        selected_option=selected_option,
        is_correct=is_correct,
        explanation=quiz['explanation'],
        timestamp=utcnow_naive(),
    )
    db.session.add(resp)

    # Record event
    evt = SimulationEvent(
        simulation_id=sim_id,
        participant_id=participant.id if participant else None,
        platform=platform,
        event_type='awareness_answered',
        details=f'Result: {"CORRECT" if is_correct else "INCORRECT"} | Answer: {selected_option[:60]}',
        timestamp=utcnow_naive(),
    )
    db.session.add(evt)

    # Record exercise completion
    evt_comp = SimulationEvent(
        simulation_id=sim_id,
        participant_id=participant.id if participant else None,
        platform=platform,
        event_type='exercise_completed',
        details=f'Completed {platform} simulation exercise and awareness checkpoint',
        timestamp=utcnow_naive(),
    )
    db.session.add(evt_comp)
    db.session.commit()

    return jsonify({
        'status': 'success',
        'is_correct': is_correct,
        'correct_answer': quiz['correct'],
        'explanation': quiz['explanation']
    })


# =====================================================================
# UNIFIED SOCIAL MEDIA GENERATOR ROUTES
# =====================================================================

@social_sim_bp.route('/generator')
@admin_required
def generator_dashboard():
    """Central Unified Social Media Phishing Awareness Simulation Generator."""
    simulations = SocialSimulation.query.order_by(SocialSimulation.id.desc()).all()
    scenarios = GeneratedScenario.query.order_by(GeneratedScenario.id.desc()).limit(20).all()
    participants = SimulationParticipant.query.order_by(SimulationParticipant.id.desc()).limit(25).all()

    total_campaigns = len(simulations)
    total_scenarios = GeneratedScenario.query.count()
    total_participants = SimulationParticipant.query.count()
    total_events = SimulationEvent.query.count()

    provider_name = os.getenv('AI_PROVIDER', 'local').upper()
    has_api_key = bool(os.getenv('GEMINI_API_KEY') or os.getenv('OPENAI_API_KEY') or os.getenv('PHISHLAB_AI_API_KEY'))

    return render_template(
        'social_sim/generator.html',
        categories=SCENARIO_CATEGORIES,
        platforms=SOCIAL_PLATFORMS,
        simulations=simulations,
        scenarios=scenarios,
        participants=participants,
        total_campaigns=total_campaigns,
        total_scenarios=total_scenarios,
        total_participants=total_participants,
        total_events=total_events,
        provider_name=provider_name,
        has_api_key=has_api_key,
    )


@social_sim_bp.route('/generator/api/generate', methods=['POST'])
@admin_required
def api_generate_scenario():
    """Generate a simulated social engineering scenario."""
    data = request.get_json(silent=True) or request.form
    category = data.get('category', 'account_security')
    platform = data.get('platform', 'whatsapp')
    sender_name = data.get('sender_name', '')
    tone = data.get('tone', 'Urgent')
    language = data.get('language', 'en')
    complexity = data.get('complexity', 'Intermediate')
    custom_instructions = data.get('custom_instructions', '')
    provider_type = data.get('provider', 'local')

    try:
        scenario = UnifiedSimulationEngine.generate_scenario(
            category=category,
            platform=platform,
            sender_name=sender_name,
            tone=tone,
            language=language,
            complexity=complexity,
            custom_instructions=custom_instructions,
            provider_type=provider_type
        )
        return jsonify({'status': 'success', 'scenario': scenario})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@social_sim_bp.route('/generator/api/preview-all', methods=['POST'])
@admin_required
def api_preview_all():
    """Format a scenario across all six social platforms."""
    data = request.get_json(silent=True) or {}
    previews = UnifiedSimulationEngine.format_for_all_platforms(data)
    return jsonify({'status': 'success', 'previews': previews})


@social_sim_bp.route('/generator/api/save-scenario', methods=['POST'])
@admin_required
def api_save_scenario():
    """Persist generated or edited scenario to database."""
    data = request.get_json(silent=True) or request.form
    is_template = (data.get('is_template') in [True, 'true', '1'])
    scenario = UnifiedSimulationEngine.save_scenario(data, is_template=is_template)
    return jsonify({
        'status': 'success',
        'scenario_id': scenario.id,
        'message': f"Scenario '{scenario.title}' successfully saved."
    })


@social_sim_bp.route('/generator/api/create-campaign', methods=['POST'])
@admin_required
def api_create_campaign():
    """Turn a generated scenario directly into an active SocialSimulation."""
    data = request.get_json(silent=True) or request.form
    scenario_id = _parse_int(data.get('scenario_id'))
    campaign_name = data.get('campaign_name', '')
    platforms = data.get('platforms')

    if isinstance(platforms, str):
        platforms = [p.strip() for p in platforms.split(',') if p.strip()]
    if not platforms:
        platforms = list(SOCIAL_PLATFORMS.keys())

    if not scenario_id:
        scenario = UnifiedSimulationEngine.save_scenario(data)
        scenario_id = scenario.id

    try:
        sim = UnifiedSimulationEngine.create_campaign_from_scenario(
            scenario_id=scenario_id,
            campaign_name=campaign_name,
            platforms=platforms
        )
        return jsonify({
            'status': 'success',
            'simulation_id': sim.id,
            'manage_url': url_for('social_sim.manage_simulation', sim_id=sim.id),
            'message': f"Simulation campaign '{sim.name}' created with {len(platforms)} platforms."
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@social_sim_bp.route('/generator/export/<int:scenario_id>')
@admin_required
def export_scenario_json(scenario_id):
    """Export a scenario configuration as JSON."""
    scenario = db.session.get(GeneratedScenario, scenario_id)
    if not scenario:
        abort(404)
    data = scenario.to_dict()
    resp = jsonify(data)
    resp.headers['Content-Disposition'] = f'attachment; filename=phishlab_scenario_{scenario.id}.json'
    return resp
