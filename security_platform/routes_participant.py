"""Participant routes for the Real-Time Phishing Security Testing Platform.

Serves the real testing URL /test/<token>, consent workflow, telemetry collection,
threat reporting, awareness checkpoint, and controlled file-access demonstration.
"""

import os
import hashlib
import uuid
from werkzeug.utils import secure_filename
from flask import (
    render_template, request, jsonify, abort, current_app, session as flask_session
)

from database import db
from .models import (
    TestingCampaign, TestingParticipant, TestingLink, TestingSession,
    TestingEvent, ParticipantConsent, DemonstrationUpload, utcnow_naive
)
from .tokens import get_link_by_raw_token
from .telemetry import parse_user_agent, anonymize_ip, sanitize_referrer
from .events import broadcast_event

# Upload configuration
UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER')
if not UPLOAD_FOLDER:
    if os.getenv('VERCEL') == '1' or 'VERCEL' in os.environ:
        UPLOAD_FOLDER = os.path.join('/tmp', 'demonstration_uploads')
    else:
        UPLOAD_FOLDER = os.path.join('database', 'demonstration_uploads')

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'docx'}
MAX_FILE_SIZE_BYTES = 2 * 1024 * 1024  # 2 Megabytes limit for safe demonstration


def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def init_participant_routes(bp):
    """Register participant-facing endpoints onto the blueprint."""

    @bp.route('/test/<raw_token>')
    def testing_landing(raw_token):
        """Real participant testing landing page."""
        link = get_link_by_raw_token(raw_token)
        if not link:
            return render_template('security_platform/landing_error.html', error_title='Invalid Security Token', error_msg='This assessment link does not exist or is malformed.'), 404

        if link.is_revoked:
            return render_template('security_platform/landing_error.html', error_title='Link Revoked', error_msg='This security assessment link has been revoked by the security administrator.'), 410

        if link.is_expired:
            return render_template('security_platform/landing_error.html', error_title='Link Expired', error_msg=f'This security testing link expired on {link.expires_at.strftime("%Y-%m-%d %H:%M UTC")}.'), 410

        if link.max_uses > 0 and link.use_count >= link.max_uses:
            return render_template('security_platform/landing_error.html', error_title='Usage Limit Exceeded', error_msg='This assessment link has exceeded its configured maximum number of interactions.'), 429

        campaign = link.campaign
        if campaign.status != 'active':
            return render_template('security_platform/landing_error.html', error_title='Campaign Not Active', error_msg=f'The security campaign "{campaign.name}" is currently {campaign.status}.'), 403

        # Parse browser telemetry
        ua_info = parse_user_agent(request.headers.get('User-Agent', ''))
        ip_hash = anonymize_ip(request.remote_addr or '')
        ref = sanitize_referrer(request.referrer or '')

        # Create or retrieve testing session
        sess_uuid = flask_session.get(f'sess_{link.id}')
        ts = TestingSession.query.filter_by(session_uuid=sess_uuid).first() if sess_uuid else None

        if not ts:
            ts = TestingSession(
                campaign_id=campaign.id,
                link_id=link.id,
                participant_id=link.participant_id,
                ip_hash=ip_hash,
                user_agent=ua_info['raw_user_agent'],
                browser_family=ua_info['browser_family'],
                browser_version=ua_info['browser_version'],
                os_family=ua_info['os_family'],
                device_category=ua_info['device_category'],
                referrer=ref,
                has_consented=False,
                completed=False,
                created_at=utcnow_naive()
            )
            db.session.add(ts)
            link.use_count += 1
            db.session.commit()
            flask_session[f'sess_{link.id}'] = ts.session_uuid

            # Record and broadcast link opened event
            evt = TestingEvent(
                campaign_id=campaign.id,
                session_id=ts.id,
                participant_id=link.participant_id,
                link_id=link.id,
                event_type='link_opened',
                browser_family=ua_info['browser_family'],
                os_family=ua_info['os_family'],
                device_category=ua_info['device_category'],
                details=f"Link opened via {ua_info['browser_family']} on {ua_info['os_family']} ({ua_info['device_category']})",
                timestamp=utcnow_naive()
            )
            db.session.add(evt)
            db.session.commit()
            broadcast_event('link_opened', campaign.id, evt.details, ua_info['browser_family'], ua_info['os_family'], ua_info['device_category'])

        return render_template(
            'security_platform/landing_page.html',
            link=link,
            campaign=campaign,
            participant=link.participant,
            session=ts,
            ua_info=ua_info,
            raw_token=raw_token
        )

    @bp.route('/test/<raw_token>/consent', methods=['POST'])
    def submit_consent(raw_token):
        """Record explicit participant consent."""
        link = get_link_by_raw_token(raw_token)
        if not link or not link.is_usable:
            return jsonify({'status': 'error', 'message': 'Invalid or expired link'}), 400

        sess_uuid = flask_session.get(f'sess_{link.id}')
        ts = TestingSession.query.filter_by(session_uuid=sess_uuid).first() if sess_uuid else None
        if not ts:
            return jsonify({'status': 'error', 'message': 'No active testing session'}), 400

        ts.has_consented = True
        consent_record = ParticipantConsent(
            session_id=ts.id,
            participant_id=link.participant_id,
            campaign_id=link.campaign_id,
            consent_text="Participant gave explicit consent to authorized security assessment.",
            consented=True,
            timestamp=utcnow_naive()
        )
        db.session.add(consent_record)

        # Record consent event
        evt = TestingEvent(
            campaign_id=link.campaign_id,
            session_id=ts.id,
            participant_id=link.participant_id,
            link_id=link.id,
            event_type='consent_submitted',
            browser_family=ts.browser_family,
            os_family=ts.os_family,
            device_category=ts.device_category,
            details=f"Participant {link.participant.alias if link.participant else 'Authorized Trainee'} provided explicit assessment consent.",
            timestamp=utcnow_naive()
        )
        db.session.add(evt)

        # Record assessment started event as assessment modules unlock upon consent
        start_evt = TestingEvent(
            campaign_id=link.campaign_id,
            session_id=ts.id,
            participant_id=link.participant_id,
            link_id=link.id,
            event_type='assessment_started',
            browser_family=ts.browser_family,
            os_family=ts.os_family,
            device_category=ts.device_category,
            details=f"Security awareness assessment started by {link.participant.alias if link.participant else 'Authorized Trainee'}.",
            timestamp=utcnow_naive()
        )
        db.session.add(start_evt)
        db.session.commit()
        broadcast_event('consent_submitted', link.campaign_id, evt.details, ts.browser_family, ts.os_family, ts.device_category)
        broadcast_event('assessment_started', link.campaign_id, start_evt.details, ts.browser_family, ts.os_family, ts.device_category)

        return jsonify({'status': 'success', 'message': 'Consent successfully recorded.'})

    @bp.route('/test/<raw_token>/report', methods=['POST'])
    def report_suspicious(raw_token):
        """Record participant threat reporting action."""
        link = get_link_by_raw_token(raw_token)
        if not link:
            return jsonify({'status': 'error', 'message': 'Invalid link'}), 400

        sess_uuid = flask_session.get(f'sess_{link.id}')
        ts = TestingSession.query.filter_by(session_uuid=sess_uuid).first() if sess_uuid else None

        evt = TestingEvent(
            campaign_id=link.campaign_id,
            session_id=ts.id if ts else None,
            participant_id=link.participant_id,
            link_id=link.id,
            event_type='suspicious_reported',
            browser_family=ts.browser_family if ts else 'Unknown',
            os_family=ts.os_family if ts else 'Unknown',
            device_category=ts.device_category if ts else 'Desktop',
            details="Participant recognized indicators and reported message to SOC.",
            timestamp=utcnow_naive()
        )
        db.session.add(evt)
        db.session.commit()
        broadcast_event('suspicious_reported', link.campaign_id, evt.details, evt.browser_family, evt.os_family, evt.device_category)

        return jsonify({
            'status': 'success',
            'action': 'reported',
            'feedback': {
                'title': '🛡️ Excellent Vigilance!',
                'message': 'You successfully recognized the indicators of a social engineering lure and reported it.',
                'action_taken': 'An alert has been dispatched to the Security Operations Center dashboard in real time.'
            }
        })

    @bp.route('/test/<raw_token>/file-demonstration', methods=['POST'])
    def upload_file_demonstration(raw_token):
        """Safe browser file-access demonstration.
        
        Demonstrates that modern browsers strictly enforce a sandboxed file boundary:
        websites CANNOT silently read arbitrary photos or documents; files are ONLY
        accessible when a human participant explicitly selects them via the OS file dialog.
        """
        link = get_link_by_raw_token(raw_token)
        if not link or not link.is_usable:
            return jsonify({'status': 'error', 'message': 'Invalid link'}), 400

        sess_uuid = flask_session.get(f'sess_{link.id}')
        ts = TestingSession.query.filter_by(session_uuid=sess_uuid).first() if sess_uuid else None
        if not ts:
            return jsonify({'status': 'error', 'message': 'Session expired'}), 400

        if 'demo_file' not in request.files:
            return jsonify({'status': 'error', 'message': 'No file was selected in file picker'}), 400

        file = request.files['demo_file']
        if file.filename == '':
            return jsonify({'status': 'error', 'message': 'Empty file selected'}), 400

        if not allowed_file(file.filename):
            return jsonify({
                'status': 'error',
                'message': f"Disallowed file format. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
            }), 400

        file_bytes = file.read()
        file_size = len(file_bytes)

        if file_size > MAX_FILE_SIZE_BYTES:
            return jsonify({'status': 'error', 'message': 'File exceeds safe demonstration limit of 2MB'}), 400

        # Compute SHA-256 hash of file content
        sha256 = hashlib.sha256(file_bytes).hexdigest()

        # Secure storage in isolated directory with UUID prefix
        safe_orig_name = secure_filename(file.filename)
        stored_name = f"{uuid.uuid4().hex}_{safe_orig_name}"
        try:
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        except OSError:
            pass
        dest_path = os.path.join(UPLOAD_FOLDER, stored_name)

        with open(dest_path, 'wb') as f:
            f.write(file_bytes)

        upload_entry = DemonstrationUpload(
            campaign_id=link.campaign_id,
            session_id=ts.id,
            participant_id=link.participant_id,
            original_filename=safe_orig_name,
            stored_filename=stored_name,
            file_size_bytes=file_size,
            mime_type=file.content_type or 'application/octet-stream',
            sha256_hash=sha256,
            consent_acknowledged=True,
            uploaded_at=utcnow_naive()
        )
        db.session.add(upload_entry)

        # Record event
        evt = TestingEvent(
            campaign_id=link.campaign_id,
            session_id=ts.id,
            participant_id=link.participant_id,
            link_id=link.id,
            event_type='file_uploaded',
            browser_family=ts.browser_family,
            os_family=ts.os_family,
            device_category=ts.device_category,
            details=f"Demonstration file selected: {safe_orig_name} ({round(file_size/1024, 1)} KB). SHA-256: {sha256[:12]}...",
            timestamp=utcnow_naive()
        )
        db.session.add(evt)
        db.session.commit()
        broadcast_event('file_uploaded', link.campaign_id, evt.details, ts.browser_family, ts.os_family, ts.device_category)

        notice = (
            "Technical Finding: This demonstration proves that browser security sandboxes strictly "
            "prohibit web pages from silently reading device files. A website can NEVER inspect your photos or "
            "documents unless you explicitly open an OS file dialog, choose a file, and click upload."
        )
        return jsonify({
            'status': 'success',
            'upload_id': upload_entry.id,
            'filename': safe_orig_name,
            'size_kb': round(file_size / 1024, 1),
            'sha256': sha256,
            'file_hash_sha256': sha256,
            'file_size_bytes': file_size,
            'security_notice': notice,
            'technical_explanation': notice
        })

    @bp.route('/test/<raw_token>/complete', methods=['POST'])
    def complete_assessment(raw_token):
        """Mark assessment as finished."""
        link = get_link_by_raw_token(raw_token)
        if not link:
            return jsonify({'status': 'error', 'message': 'Invalid link'}), 400

        sess_uuid = flask_session.get(f'sess_{link.id}')
        ts = TestingSession.query.filter_by(session_uuid=sess_uuid).first() if sess_uuid else None
        if ts:
            ts.completed = True

        evt = TestingEvent(
            campaign_id=link.campaign_id,
            session_id=ts.id if ts else None,
            participant_id=link.participant_id,
            link_id=link.id,
            event_type='assessment_completed',
            browser_family=ts.browser_family if ts else 'Unknown',
            os_family=ts.os_family if ts else 'Unknown',
            device_category=ts.device_category if ts else 'Desktop',
            details=f"Participant finished security assessment workflow.",
            timestamp=utcnow_naive()
        )
        db.session.add(evt)
        db.session.commit()
        if ts:
            broadcast_event('assessment_completed', link.campaign_id, evt.details, ts.browser_family, ts.os_family, ts.device_category)

        return jsonify({'status': 'success', 'message': 'Assessment marked as completed.'})
