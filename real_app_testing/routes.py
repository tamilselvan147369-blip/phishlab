"""RealAppTesting Blueprint routes and admin endpoints.

Provides admin UI to create exercises, manage participants, view history,
analytics, CSV export, token revocation, audit logs, and the platform
connector framework.
"""

from functools import wraps
import hashlib
import uuid
import csv
import io
from datetime import datetime, timezone, timedelta
from bleach import clean

from flask import (
    Blueprint, render_template, request, redirect, url_for,
    flash, abort, current_app, session, Response,
)
from flask_wtf import FlaskForm
from wtforms import SelectField, SubmitField, StringField, TextAreaField
from wtforms.validators import DataRequired, Optional

# Shared SQLAlchemy instance
from database import db, Campaign

# Blueprint
from . import realapp_bp

# Models and token utilities
from .models import (
    RealAppExercise, ExerciseParticipant, ManualEventConfirmation,
    AuditLog, PLATFORMS, utcnow_naive,
)
from .tokens import generate_token, verify_token

# Choice class compatibility for WTForms
try:
    from wtforms.fields.choices import SelectChoice
    def make_choice(val, label):
        return SelectChoice(value=val, label=label)
except ImportError:
    def make_choice(val, label):
        return (val, label)

# ---------------------------------------------------------------------------
# Authentication Decorator (from decoupled auth module to prevent circular imports)
# ---------------------------------------------------------------------------
from auth import admin_required

# ---------------------------------------------------------------------------
# Helper to retrieve exercise by raw token (O(1) direct lookup + constant-time verify)
# ---------------------------------------------------------------------------
def get_exercise_by_token(raw_token):
    if not raw_token or not isinstance(raw_token, str):
        return None
    token_hash = hashlib.sha256(raw_token.encode('utf-8')).hexdigest()
    ex = RealAppExercise.query.filter_by(demo_token_hash=token_hash).first()
    if ex and verify_token(raw_token, ex.demo_token_hash):
        return ex
    return None

# ---------------------------------------------------------------------------
# Audit logger
# ---------------------------------------------------------------------------
def log_audit(exercise_id, action, details=None, actor=None):
    """Record an audit log entry."""
    entry = AuditLog(
        exercise_id=exercise_id,
        action=action,
        details=details or '',
        actor=actor or session.get('admin_name', 'admin'),
        timestamp=utcnow_naive(),
    )
    db.session.add(entry)
    db.session.commit()

# ---------------------------------------------------------------------------
# Forms
# ---------------------------------------------------------------------------
class PlatformSelectForm(FlaskForm):
    platform = SelectField(
        "Select Platform",
        choices=[make_choice(p, p.replace('_', ' ').title()) for p in sorted(PLATFORMS)],
        validators=[DataRequired()],
    )
    exercise_name = StringField("Exercise Name (optional)", validators=[Optional()])
    description = TextAreaField("Description (optional)", validators=[Optional()])
    submit = SubmitField("Create Real-App Exercise")


# =====================================================================
# BLUEPRINT ROOT REDIRECT
# =====================================================================

@realapp_bp.route("/")
@realapp_bp.route("")
def index():
    """Redirect blueprint root to exercise history."""
    return redirect(url_for("realapp.exercise_history"))


# =====================================================================
# ADMIN ROUTES
# =====================================================================

@realapp_bp.route("/select/<int:cid>", methods=["GET", "POST"])
@admin_required
def select_platform(cid):
    """Create a RealAppExercise for a campaign."""
    campaign = db.get_or_404(Campaign, cid)
    form = PlatformSelectForm()
    if form.validate_on_submit():
        raw_token, token_hash = generate_token()
        expiry = utcnow_naive().replace(microsecond=0) + current_app.config.get(
            "REALAPP_TOKEN_TTL", timedelta(hours=4)
        )
        exercise = RealAppExercise(
            campaign_id=campaign.id,
            platform=form.platform.data,
            exercise_name=form.exercise_name.data or f"{campaign.name} - {form.platform.data}",
            description=form.description.data or '',
            demo_token_hash=token_hash,
            token_expires_at=expiry,
            created_at=utcnow_naive(),
        )
        db.session.add(exercise)
        db.session.commit()
        log_audit(exercise.id, 'exercise_created',
                  f'Platform: {form.platform.data}, Campaign: {campaign.id}')
        flash(f"Real-App exercise created for platform {form.platform.data}.", "success")
        return redirect(url_for("realapp.demo_page", token=raw_token))
    return render_template(
        "realapp/select_platform.html",
        campaign=campaign,
        form=form,
    )


@realapp_bp.route("/history")
@admin_required
def exercise_history():
    """List all RealAppExercises."""
    exercises = RealAppExercise.query.order_by(RealAppExercise.created_at.desc()).all()
    return render_template("realapp/history.html", exercises=exercises)


@realapp_bp.route("/analytics")
@admin_required
def analytics():
    """Analytics dashboard for RealAppTesting."""
    exercises = RealAppExercise.query.all()
    total_exercises = len(exercises)
    total_participants = ExerciseParticipant.query.count()
    total_confirmations = ManualEventConfirmation.query.count()

    # Per-platform breakdown
    platform_stats = {}
    for p in PLATFORMS:
        exs = [e for e in exercises if e.platform == p]
        participants = sum(len(e.participants) for e in exs)
        platform_stats[p] = {
            'exercises': len(exs),
            'participants': participants,
        }

    # Per-exercise stats
    exercise_stats = []
    for ex in exercises:
        confirmations = ManualEventConfirmation.query.filter_by(exercise_id=ex.id).count()
        exercise_stats.append({
            'id': ex.id,
            'name': ex.exercise_name or f'Exercise {ex.id}',
            'platform': ex.platform,
            'campaign': ex.campaign.name if ex.campaign else 'N/A',
            'participants': len(ex.participants),
            'confirmations': confirmations,
            'status': ex.status,
            'created_at': ex.created_at,
        })

    return render_template(
        "realapp/analytics.html",
        total_exercises=total_exercises,
        total_participants=total_participants,
        total_confirmations=total_confirmations,
        platform_stats=platform_stats,
        exercise_stats=exercise_stats,
    )


@realapp_bp.route("/export/csv")
@admin_required
def export_csv():
    """Export exercise data as CSV."""
    exercises = RealAppExercise.query.order_by(RealAppExercise.created_at.desc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'Exercise ID', 'Exercise Name', 'Campaign', 'Platform',
        'Status', 'Created At', 'Expires At', 'Revoked',
        'Participants', 'Confirmations',
    ])
    for ex in exercises:
        confirmations = ManualEventConfirmation.query.filter_by(exercise_id=ex.id).count()
        writer.writerow([
            ex.id,
            ex.exercise_name or '',
            ex.campaign.name if ex.campaign else '',
            ex.platform,
            ex.status,
            ex.created_at.isoformat() if ex.created_at else '',
            ex.token_expires_at.isoformat() if ex.token_expires_at else '',
            'Yes' if ex.revoked_at else 'No',
            len(ex.participants),
            confirmations,
        ])
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=realapp_exercises.csv'},
    )


@realapp_bp.route("/revoke/<int:exercise_id>", methods=["POST"])
@admin_required
def revoke_exercise(exercise_id):
    """Revoke a RealAppExercise token."""
    exercise = db.get_or_404(RealAppExercise, exercise_id)
    if exercise.revoked_at:
        flash("Exercise already revoked.", "warning")
    else:
        exercise.revoked_at = utcnow_naive()
        exercise.status = 'revoked'
        db.session.commit()
        log_audit(exercise.id, 'exercise_revoked', 'Token revoked by admin')
        flash("Exercise token revoked.", "success")
    return redirect(url_for("realapp.exercise_history"))


@realapp_bp.route("/audit")
@admin_required
def audit_log():
    """View audit log entries."""
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).all()
    return render_template("realapp/audit_log.html", logs=logs)


@realapp_bp.route("/exercise/<int:exercise_id>")
@admin_required
def exercise_detail(exercise_id):
    """View exercise detail with participants and confirmations."""
    exercise = db.get_or_404(RealAppExercise, exercise_id)
    participants = ExerciseParticipant.query.filter_by(exercise_id=exercise_id).all()
    confirmations = ManualEventConfirmation.query.filter_by(exercise_id=exercise_id).all()
    return render_template(
        "realapp/exercise_detail.html",
        exercise=exercise,
        participants=participants,
        confirmations=confirmations,
    )


# =====================================================================
# PARTICIPANT-FACING ROUTES
# =====================================================================

@realapp_bp.route("/demo/<token>")
def demo_page(token):
    """Demo page — accessible with a valid token."""
    exercise = get_exercise_by_token(token)
    if not exercise:
        abort(404)
    if exercise.token_expires_at < utcnow_naive():
        abort(410)
    if exercise.revoked_at is not None:
        abort(403)
    return render_template(
        "realapp/demo_page.html",
        exercise=exercise,
        token=token,
        participant_uuid=str(uuid.uuid4()),
    )


@realapp_bp.route('/confirm/<token>', methods=['POST'])
def confirm_participation(token):
    """Record participant consent and confirmation."""
    exercise = get_exercise_by_token(token)
    if not exercise:
        abort(404)
    if exercise.token_expires_at < utcnow_naive() or exercise.revoked_at:
        abort(403)
    participant_uuid_str = request.form.get('participant_uuid', '').strip()
    if not participant_uuid_str:
        abort(400)
    # Validate UUID format to prevent injection or malformed data
    try:
        validated_uuid = str(uuid.UUID(participant_uuid_str))
    except (ValueError, AttributeError):
        abort(400)

    participant = ExerciseParticipant.query.filter_by(
        participant_uuid=validated_uuid
    ).first()
    if not participant:
        participant = ExerciseParticipant(
            participant_uuid=validated_uuid,
            exercise=exercise,
            created_at=utcnow_naive(),
        )
        db.session.add(participant)
        db.session.flush()

    confirmation = ManualEventConfirmation(
        exercise=exercise,
        participant=participant,
        event_type='demo_viewed',
        timestamp=utcnow_naive(),
    )
    db.session.add(confirmation)
    db.session.commit()
    log_audit(exercise.id, 'participant_confirmed',
              f'Participant {validated_uuid} viewed demo')
    flash('Thank you for your participation.', 'success')
    return redirect(url_for('realapp.completion_page', token=token))


@realapp_bp.route('/completion/<token>')
def completion_page(token):
    """Completion page — static thank-you."""
    exercise = get_exercise_by_token(token)
    if not exercise:
        abort(404)
    return render_template('realapp/completion.html', exercise=exercise)


# =====================================================================
# PLATFORM CONNECTOR FRAMEWORK
# =====================================================================

class PlatformConnector:
    """Abstract base for platform connectors.

    Each connector provides metadata and manual administrative instructions.
    No actual external social network credentials or APIs are called.
    """

    name = ''
    display_name = ''
    icon = ''
    description = ''

    def get_instructions(self, exercise):
        return f"Open {self.display_name} and send the exercise link to participants."

    def validate_exercise(self, exercise):
        return True, ''

    def __repr__(self):
        return f"<PlatformConnector {self.name}>"


class WhatsAppConnector(PlatformConnector):
    name = 'whatsapp'
    display_name = 'WhatsApp'
    icon = 'fab fa-whatsapp'
    description = 'Send exercise link via WhatsApp message.'

    def get_instructions(self, exercise):
        return (
            "1. Open WhatsApp on your authorized device.\n"
            "2. Select the consenting participant or internal testing group.\n"
            "3. Share the approved PhishLab demonstration link.\n"
            "4. Await participant consent confirmation.\n"
            "5. Verify interaction recorded in PhishLab Analytics."
        )


class InstagramConnector(PlatformConnector):
    name = 'instagram'
    display_name = 'Instagram'
    icon = 'fab fa-instagram'
    description = 'Send exercise link via Instagram Direct Message.'

    def get_instructions(self, exercise):
        return (
            "1. Open Instagram on your authorized device.\n"
            "2. Navigate to Direct Messages with the consenting participant.\n"
            "3. Share the approved PhishLab demonstration link.\n"
            "4. Await participant consent confirmation.\n"
            "5. Verify interaction recorded in PhishLab Analytics."
        )


class FacebookMessengerConnector(PlatformConnector):
    name = 'facebook_messenger'
    display_name = 'Facebook Messenger'
    icon = 'fab fa-facebook-messenger'
    description = 'Send exercise link via Facebook Messenger.'

    def get_instructions(self, exercise):
        return (
            "1. Open Facebook Messenger.\n"
            "2. Open chat with consenting participant.\n"
            "3. Share the approved PhishLab demonstration link.\n"
            "4. Await participant consent confirmation.\n"
            "5. Verify interaction recorded in PhishLab Analytics."
        )


class TelegramConnector(PlatformConnector):
    name = 'telegram'
    display_name = 'Telegram'
    icon = 'fab fa-telegram'
    description = 'Send exercise link via Telegram message.'

    def get_instructions(self, exercise):
        return (
            "1. Open Telegram on your authorized device.\n"
            "2. Select the consenting participant or group.\n"
            "3. Share the approved PhishLab demonstration link.\n"
            "4. Await participant consent confirmation.\n"
            "5. Verify interaction recorded in PhishLab Analytics."
        )


class XConnector(PlatformConnector):
    name = 'x'
    display_name = 'X (Twitter)'
    icon = 'fab fa-x-twitter'
    description = 'Send exercise link via X Direct Message.'

    def get_instructions(self, exercise):
        return (
            "1. Open X (Twitter) on your authorized device.\n"
            "2. Open Direct Message with consenting participant.\n"
            "3. Share the approved PhishLab demonstration link.\n"
            "4. Await participant consent confirmation.\n"
            "5. Verify interaction recorded in PhishLab Analytics."
        )


class LinkedInConnector(PlatformConnector):
    name = 'linkedin'
    display_name = 'LinkedIn'
    icon = 'fab fa-linkedin'
    description = 'Send exercise link via LinkedIn message.'

    def get_instructions(self, exercise):
        return (
            "1. Open LinkedIn on your authorized device.\n"
            "2. Open Messaging with consenting colleague/participant.\n"
            "3. Share the approved PhishLab demonstration link.\n"
            "4. Await participant consent confirmation.\n"
            "5. Verify interaction recorded in PhishLab Analytics."
        )


# Registry of available connectors
CONNECTORS = {
    'whatsapp': WhatsAppConnector(),
    'instagram': InstagramConnector(),
    'facebook_messenger': FacebookMessengerConnector(),
    'telegram': TelegramConnector(),
    'x': XConnector(),
    'linkedin': LinkedInConnector(),
}


def get_connector(platform_name):
    """Return the connector for a given platform, or None."""
    return CONNECTORS.get(platform_name)


@realapp_bp.route("/connector/<int:exercise_id>")
@admin_required
def connector_instructions(exercise_id):
    """Show platform-specific sending instructions for an exercise."""
    exercise = db.get_or_404(RealAppExercise, exercise_id)
    connector = get_connector(exercise.platform)
    if not connector:
        flash("No connector available for this platform.", "warning")
        return redirect(url_for("realapp.exercise_history"))
    instructions = connector.get_instructions(exercise)
    return render_template(
        "realapp/connector_instructions.html",
        exercise=exercise,
        connector=connector,
        instructions=instructions,
    )
