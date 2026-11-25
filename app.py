"""Main Flask application for PhishLab.

Provides attacker dashboard, campaign creation, email preview, simulated login page,
and results view, alongside the RealAppTesting subsystem.
"""

import os
import smtplib
import hmac
from functools import wraps
from datetime import datetime, timezone, timedelta
from email.message import EmailMessage
from dotenv import load_dotenv
import bleach

from flask import (
    Flask, render_template, request, redirect, url_for, flash,
    jsonify, current_app, session, abort
)
from flask_wtf import FlaskForm, CSRFProtect
from wtforms import StringField, SelectField, TextAreaField, SubmitField, PasswordField
from wtforms.validators import DataRequired, ValidationError
from sqlalchemy import func

from database import db, Campaign, Event, init_db, utcnow_naive

from auth import (
    admin_required, is_login_rate_limited, record_failed_login, clear_failed_logins
)
try:
    from wtforms.fields.choices import SelectChoice
    def make_choice(val, label):
        return SelectChoice(value=val, label=label)
except ImportError:
    def make_choice(val, label):
        return (val, label)

# Load environment variables from .env if present
load_dotenv()

csrf = CSRFProtect()

# Allowed HTML tags for email templates
SAFE_EMAIL_TAGS = [
    'a', 'b', 'blockquote', 'br', 'code', 'div', 'em', 'h1', 'h2', 'h3',
    'h4', 'h5', 'h6', 'hr', 'i', 'img', 'li', 'ol', 'p', 'pre', 'span',
    'strong', 'table', 'tbody', 'td', 'th', 'thead', 'tr', 'ul'
]
SAFE_EMAIL_ATTRS = {
    '*': ['class', 'id', 'align'],
    'a': ['href', 'title', 'target'],
    'img': ['src', 'alt', 'width', 'height'],
}

def sanitize_template(raw_html: str) -> str:
    """Sanitize email HTML templates to prevent Stored XSS."""
    if not raw_html:
        return ''
    return bleach.clean(
        raw_html,
        tags=SAFE_EMAIL_TAGS,
        attributes=SAFE_EMAIL_ATTRS,
        strip=True
    )


# ---------------------------------------------------------------------------
# Authentication Decorator
# ---------------------------------------------------------------------------
from auth import admin_required


# ---------------------------------------------------------------------------
# Forms
# ---------------------------------------------------------------------------
def validate_recipient_email_field(form, field):
    """Validate recipient email format allowing academic simulation test domains (.test)."""
    email_val = (field.data or '').strip()
    if not email_val:
        raise ValidationError('Recipient email is required.')
    try:
        import email_validator
        email_validator.validate_email(email_val, test_environment=True, check_deliverability=False)
    except Exception:
        import re
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email_val):
            raise ValidationError('Invalid email address.')

class CampaignForm(FlaskForm):
    name = StringField('Campaign Name', validators=[DataRequired()])
    scenario = SelectField('Scenario Type', choices=[
        make_choice('university', 'Fictional University Portal'),
        make_choice('corporate', 'Fictional Corporate Email'),
        make_choice('social', 'Fictional Social Media Login'),
        make_choice('banking', 'Fictional Banking Notification')
    ], validators=[DataRequired()])
    subject = StringField('Email Subject', validators=[DataRequired()])
    sender_name = StringField('Sender Display Name', validators=[DataRequired()])
    recipient = StringField('Test Recipient Email', validators=[DataRequired(), validate_recipient_email_field])
    template = TextAreaField('Email Template (HTML)', validators=[DataRequired()])
    description = TextAreaField('Simulation Description')
    submit = SubmitField('Create Campaign')


class EditCampaignForm(FlaskForm):
    name = StringField('Campaign Name', validators=[DataRequired()])
    description = TextAreaField('Simulation Description')
    submit = SubmitField('Update Campaign')


class AdminLoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Log In')


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
def record_event(campaign_id, event_type):
    """Record a tracking event for the given campaign."""
    evt = Event(campaign_id=campaign_id, event_type=event_type, timestamp=utcnow_naive())
    db.session.add(evt)
    db.session.commit()


def validate_smtp_config():
    """Ensure SMTP settings point to the local Mailpit instance."""
    host = current_app.config.get('MAIL_SERVER', '127.0.0.1')
    port = current_app.config.get('MAIL_PORT', 1025)
    if host != '127.0.0.1' or port != 1025:
        return False, f"SMTP must be 127.0.0.1:1025 (found {host}:{port})"
    return True, "SMTP configuration valid"


def validate_recipient(email: str):
    """Validate that the recipient is a single address on the allowed domain."""
    if not email:
        return False, "Recipient address is required"
    import re
    if not re.fullmatch(r"[^@\s]+@[^@\s]+", email):
        return False, "Invalid email format"
    if ',' in email:
        return False, "Multiple recipients are not allowed"
    allowed = os.getenv('ALLOWED_RECIPIENT_DOMAIN', current_app.config.get('ALLOWED_RECIPIENT_DOMAIN', 'example.test'))
    domain = email.split('@')[-1].lower()
    if domain != allowed.lower():
        return False, f"Recipient domain must be {allowed}"
    return True, "Recipient valid"


def send_email(campaign):
    """Send the campaign email via local SMTP (Mailpit)."""
    smtp_ok, msg = validate_smtp_config()
    if not smtp_ok:
        current_app.logger.error(msg)
        flash(msg, 'danger')
        return False

    rec_ok, rec_msg = validate_recipient(campaign.recipient)
    if not rec_ok:
        current_app.logger.error(rec_msg)
        flash(rec_msg, 'danger')
        return False

    msg = EmailMessage()
    msg['Subject'] = campaign.subject
    msg['From'] = f"{campaign.sender_name} <{current_app.config['MAIL_SENDER']}>"
    msg['To'] = campaign.recipient
    msg.set_content('This is a multipart alternative email.', subtype='plain')
    msg.add_alternative(campaign.template, subtype='html')
    try:
        with smtplib.SMTP(current_app.config['MAIL_SERVER'], current_app.config['MAIL_PORT']) as smtp:
            smtp.send_message(msg)
        record_event(campaign.id, 'email_sent')
        return True
    except Exception as exc:
        current_app.logger.error(f"Failed to send email: {exc}")
        flash('Failed to send email. Ensure Mailpit is running.', 'danger')
        return False


# ---------------------------------------------------------------------------
# Core View Handlers
# ---------------------------------------------------------------------------
def campaign_history():
    campaigns = Campaign.query.order_by(Campaign.created_at.desc()).all()
    return render_template('campaign_history.html', campaigns=campaigns)


def campaign_detail(cid):
    campaign = db.get_or_404(Campaign, cid)
    return render_template('campaign_detail.html', campaign=campaign)


def edit_campaign(cid):
    campaign = db.get_or_404(Campaign, cid)
    form = EditCampaignForm(obj=campaign)
    if form.validate_on_submit():
        campaign.name = form.name.data
        campaign.description = form.description.data
        db.session.commit()
        record_event(campaign.id, 'campaign_edited')
        flash('Campaign updated.', 'success')
        return redirect(url_for('campaign_detail', cid=campaign.id))
    return render_template('campaign_edit.html', form=form, campaign=campaign)


def delete_campaign(cid):
    campaign = db.get_or_404(Campaign, cid)
    if request.method == 'POST':
        db.session.delete(campaign)
        db.session.commit()
        flash('Campaign deleted.', 'danger')
        return redirect(url_for('campaign_history'))
    return render_template('campaign_delete.html', campaign=campaign)


def dashboard():
    stats_rows = db.session.query(
        Campaign.id,
        Campaign.name,
        func.count(Event.id).filter(Event.event_type == 'email_sent').label('emails_sent'),
        func.count(Event.id).filter(Event.event_type == 'email_opened').label('opens'),
        func.count(Event.id).filter(Event.event_type == 'demo_link_clicked').label('clicks'),
        func.count(Event.id).filter(Event.event_type == 'demo_form_submitted').label('submits')
    ).join(Event, isouter=True).group_by(Campaign.id).all()
    stats = [
        {
            'id': row.id,
            'name': row.name,
            'emails_sent': row.emails_sent,
            'opens': row.opens,
            'clicks': row.clicks,
            'submits': row.submits,
        }
        for row in stats_rows
    ]
    total_campaigns = len(stats)
    return render_template('dashboard.html', stats=stats, total_campaigns=total_campaigns)


def create_campaign():
    form = CampaignForm()
    if form.validate_on_submit():
        allowed_domain = os.getenv('ALLOWED_RECIPIENT_DOMAIN', current_app.config.get('ALLOWED_RECIPIENT_DOMAIN', 'example.test'))
        recipient_domain = form.recipient.data.split('@')[-1]
        if recipient_domain.lower() != allowed_domain.lower():
            flash(f'Recipient must be an address at the allowed domain "{allowed_domain}".', 'danger')
            return render_template('campaign.html', form=form)
        sanitized_html = sanitize_template(form.template.data)
        campaign = Campaign(
            name=form.name.data,
            scenario=form.scenario.data,
            subject=form.subject.data,
            sender_name=form.sender_name.data,
            recipient=form.recipient.data,
            template=sanitized_html,
            description=form.description.data,
            created_at=utcnow_naive(),
        )
        db.session.add(campaign)
        db.session.commit()
        record_event(campaign.id, 'campaign_created')
        send_email(campaign)
        flash('Campaign created and email sent.', 'success')
        return redirect(url_for('dashboard'))
    return render_template('campaign.html', form=form)


def email_preview(cid):
    campaign = db.get_or_404(Campaign, cid)
    record_event(cid, 'email_opened')
    return render_template('email_preview.html', campaign=campaign)


def demo_login(cid):
    campaign = db.get_or_404(Campaign, cid)
    if request.method == 'POST':
        record_event(cid, 'demo_form_submitted')
        return render_template('demo_login.html', campaign=campaign, submitted=True)
    record_event(cid, 'demo_link_clicked')
    return render_template('demo_login.html', campaign=campaign, submitted=False)


def campaign_results(cid):
    campaign = db.get_or_404(Campaign, cid)
    counts = db.session.query(
        Event.event_type,
        func.count(Event.id)
    ).filter(Event.campaign_id == cid).group_by(Event.event_type).all()
    count_dict = {etype: cnt for etype, cnt in counts}
    return render_template('results.html', campaign=campaign, counts=count_dict)


def admin_login():
    """Administrator authentication route with constant-time verification and rate limiting."""
    client_ip = request.remote_addr or '127.0.0.1'
    if is_login_rate_limited(client_ip):
        flash('Too many failed login attempts. Login temporarily locked for 15 minutes.', 'danger')
        return render_template('admin_login.html', form=AdminLoginForm()), 429

    form = AdminLoginForm()
    if form.validate_on_submit():
        expected_user = current_app.config.get('ADMIN_USERNAME', os.getenv('ADMIN_USERNAME', 'admin'))
        expected_pass = current_app.config.get('ADMIN_PASSWORD', os.getenv('ADMIN_PASSWORD'))
        expected_hash = current_app.config.get('ADMIN_PASSWORD_HASH', os.getenv('ADMIN_PASSWORD_HASH'))

        # Only allow dev fallback credentials if not in production
        if not expected_pass and not expected_hash:
            if not current_app.config.get('IS_PRODUCTION', False):
                expected_pass = 'phishlab-admin-2026!'

        user_ok = hmac.compare_digest(form.username.data, expected_user)
        pass_ok = False
        if expected_hash:
            from werkzeug.security import check_password_hash
            pass_ok = check_password_hash(expected_hash, form.password.data)
        elif expected_pass:
            pass_ok = hmac.compare_digest(form.password.data, expected_pass)

        if user_ok and pass_ok:
            clear_failed_logins(client_ip)
            session['is_admin'] = True
            session['admin_name'] = form.username.data
            flash('Logged in successfully as Administrator.', 'success')
            next_url = request.args.get('next') or url_for('security_platform.operations_dashboard')
            return redirect(next_url)

        record_failed_login(client_ip)
        flash('Invalid administrator credentials.', 'danger')
    return render_template('admin_login.html', form=form)


def admin_logout():
    """Administrator logout route."""
    session.pop('is_admin', None)
    session.pop('admin_name', None)
    flash('Logged out successfully.', 'info')
    return redirect(url_for('dashboard'))


def register_core_routes(app):
    """Register all core local simulation routes onto the application instance."""
    app.add_url_rule('/campaigns', 'campaign_history', campaign_history)
    app.add_url_rule('/campaign/<int:cid>', 'campaign_detail', campaign_detail)
    app.add_url_rule('/campaign/<int:cid>/edit', 'edit_campaign', edit_campaign, methods=['GET', 'POST'])
    app.add_url_rule('/campaign/<int:cid>/delete', 'delete_campaign', delete_campaign, methods=['GET', 'POST'])
    app.add_url_rule('/', 'dashboard', dashboard)
    app.add_url_rule('/campaign/create', 'create_campaign', create_campaign, methods=['GET', 'POST'])
    app.add_url_rule('/campaign/<int:cid>/preview', 'email_preview', email_preview)
    app.add_url_rule('/login/<int:cid>', 'demo_login', demo_login, methods=['GET', 'POST'])
    app.add_url_rule('/campaign/<int:cid>/results', 'campaign_results', campaign_results)
    app.add_url_rule('/admin/login', 'admin_login', admin_login, methods=['GET', 'POST'])
    app.add_url_rule('/admin/logout', 'admin_logout', admin_logout)

    def health_check():
        db_status = "connected"
        try:
            db.session.execute(func.now())
        except Exception:
            db_status = "disconnected"
        status_code = 200 if db_status == "connected" else 503
        return jsonify({
            'status': 'healthy' if db_status == 'connected' else 'unhealthy',
            'timestamp': utcnow_naive().isoformat() + 'Z',
            'database': db_status
        }), status_code

    app.add_url_rule('/healthz', 'healthz', health_check)
    app.add_url_rule('/health', 'health', health_check)


def register_error_handlers(app):
    """Register uniform error handlers preventing sensitive stack leaks."""
    @app.errorhandler(400)
    def bad_request(e):
        return render_template('error.html', code=400, message='Bad Request: The request was invalid or missing required parameters.'), 400

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('error.html', code=403, message='Forbidden: You do not have permission to access this resource.'), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template('error.html', code=404, message='Not Found: The requested URL was not found on this server.'), 404

    @app.errorhandler(410)
    def gone(e):
        return render_template('error.html', code=410, message='Gone: This demonstration link has expired.'), 410

    @app.errorhandler(500)
    def internal_error(e):
        return render_template('error.html', code=500, message='Internal Server Error: An unexpected error occurred. Please contact the administrator.'), 500


# ---------------------------------------------------------------------------
# Application Factory
# ---------------------------------------------------------------------------
def create_app(test_config=None):
    """Factory to create a Flask app with configurable database URI.
    Reads optional env var ``DATABASE_URL`` or ``PHISHLAB_DATABASE_URI``; defaults to SQLite file
    ``database/phishlab.db``. Allows tests to inject a temporary/in-memory DB.
    """
    app = Flask(__name__)

    is_prod = (
        os.getenv('RENDER') == 'true'
        or os.getenv('FLASK_ENV') == 'production'
        or os.getenv('PRODUCTION') == 'true'
    )
    is_vercel = os.getenv('VERCEL') == '1' or 'VERCEL' in os.environ
    app.config['IS_PRODUCTION'] = is_prod

    # Secret Key configuration
    secret_key = os.getenv('SECRET_KEY') or os.getenv('FLASK_SECRET_KEY')
    if not secret_key:
        if is_prod and not is_vercel:
            raise RuntimeError("CRITICAL SECURITY ERROR: SECRET_KEY environment variable is required in production.")
        secret_key = 'dev-secret-key-change-in-production-2026'
    app.config['SECRET_KEY'] = secret_key

    # Database URI (supports Render postgres://, Vercel POSTGRES_URL, or tempfile sqlite on serverless)
    raw_db_url = (
        os.getenv('DATABASE_URL')
        or os.getenv('POSTGRES_URL')
        or os.getenv('PHISHLAB_DATABASE_URI')
    )
    if not raw_db_url:
        if is_vercel:
            import tempfile
            t_dir = tempfile.gettempdir()
            db_path = os.path.join(t_dir, 'phishlab.db').replace('\\', '/')
            raw_db_url = f"sqlite:///{db_path}"
        else:
            raw_db_url = f"sqlite:///{os.path.abspath('database/phishlab.db')}"

    if raw_db_url.startswith("postgres://"):
        raw_db_url = raw_db_url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif raw_db_url.startswith("postgresql://") and "+psycopg2" not in raw_db_url:
        raw_db_url = raw_db_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = raw_db_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    if "sqlite" not in raw_db_url:
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_pre_ping': True,
            'pool_recycle': 300,
        }

    app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', '127.0.0.1')
    app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', '1025'))
    app.config['MAIL_SENDER'] = os.getenv('MAIL_SENDER', 'phishlab@example.test')
    app.config['ALLOWED_RECIPIENT_DOMAIN'] = os.getenv('ALLOWED_RECIPIENT_DOMAIN', 'example.test')

    # Session cookie hardening
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SESSION_COOKIE_SECURE'] = os.getenv('SESSION_COOKIE_SECURE', 'True' if is_prod else 'False').lower() == 'true'
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=8)

    if test_config:
        app.config.update(test_config)

    # Apply ProxyFix when running behind reverse proxies (Render, Cloudflare, etc.)
    if is_prod or os.getenv('BEHIND_PROXY') == 'true':
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    # Initialise extensions
    csrf.init_app(app)

    # Initialise database
    init_db(app)

    # Register core routes & error handlers
    register_core_routes(app)
    register_error_handlers(app)

    # Register RealAppTesting blueprint inside factory
    from real_app_testing import realapp_bp
    app.register_blueprint(realapp_bp, url_prefix='/realapp')

    # Register Social Simulation Engine blueprint inside factory
    from social_simulation import social_sim_bp
    app.register_blueprint(social_sim_bp, url_prefix='/social')

    # Register Real-Time Phishing Security Testing Platform blueprint
    from security_platform import security_platform_bp
    app.register_blueprint(security_platform_bp)

    # CLI command
    @app.cli.command('init-db')
    def init_db_cli():
        from database import init_db as init_db_helper
        init_db_helper(app)
        print('Database initialised.')

    return app


# Ensure Werkzeug has __version__ attribute for Flask test client compatibility
import werkzeug
if not hasattr(werkzeug, '__version__'):
    werkzeug.__version__ = '3.0.0'

# Global app instance for direct execution / WSGI servers
app = create_app()

if __name__ == '__main__':
    os.makedirs('database', exist_ok=True)
    with app.app_context():
        db.create_all()
        # Seed default simulation campaign if database has no social simulations
        from social_simulation.models import SocialSimulation
        from social_simulation.scenarios import seed_default_simulation
        if SocialSimulation.query.count() == 0:
            seed_default_simulation(db.session)
    # Bound to localhost strictly
    app.run(host='127.0.0.1', port=5000, debug=False)
