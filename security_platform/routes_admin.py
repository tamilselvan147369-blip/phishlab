"""Administrative routes and operations dashboard for the Real-Time Phishing Security Testing Platform."""

import os
import csv
import io
import json
import time
from datetime import datetime, timedelta
from flask import (
    render_template, request, redirect, url_for, flash, jsonify,
    Response, abort, current_app, session as flask_session
)
from sqlalchemy import func

from database import db
from auth import admin_required
from .models import (
    TestingCampaign, TestingParticipant, TestingLink, TestingSession,
    TestingEvent, ParticipantConsent, DemonstrationUpload,
    PlatformMessageTemplate, MessageDistribution, SecurityAuditLog, utcnow_naive
)
from .tokens import create_testing_link, generate_qr_svg
from .events import broadcaster
from .distribution import DEFAULT_SCENARIO_TEMPLATES, build_distribution_payload


def init_admin_routes(bp):
    """Register admin operations routes onto the blueprint."""

    @bp.route('/security/dashboard')
    @admin_required
    def operations_dashboard():
        """Central Cybersecurity Operations Dashboard."""
        try:
            campaigns = TestingCampaign.query.order_by(TestingCampaign.id.desc()).all()
            total_campaigns = len(campaigns)
            active_campaigns = sum(1 for c in campaigns if c.status == 'active')
            total_links = TestingLink.query.count()
            total_sessions = TestingSession.query.count()
            consents_count = ParticipantConsent.query.count()
            completed_count = TestingSession.query.filter_by(completed=True).count()
            reported_count = TestingEvent.query.filter_by(event_type='suspicious_reported').count()
            file_demo_count = DemonstrationUpload.query.count()
            browser_stats = dict(
                db.session.query(TestingSession.browser_family, func.count(TestingSession.id))
                .group_by(TestingSession.browser_family)
                .all()
            )
            device_stats = dict(
                db.session.query(TestingSession.device_category, func.count(TestingSession.id))
                .group_by(TestingSession.device_category)
                .all()
            )
            recent_events = TestingEvent.query.order_by(TestingEvent.id.desc()).limit(20).all()
            recent_uploads = DemonstrationUpload.query.filter_by(deleted_at=None).order_by(DemonstrationUpload.id.desc()).limit(10).all()
            recent_links = TestingLink.query.order_by(TestingLink.id.desc()).limit(20).all()
            session_counts = dict(
                db.session.query(TestingSession.campaign_id, func.count(TestingSession.id))
                .group_by(TestingSession.campaign_id)
                .all()
            )
        except Exception:
            # Tables may not exist yet on a fresh serverless cold-start — auto-create and retry
            db.create_all()
            campaigns = TestingCampaign.query.order_by(TestingCampaign.id.desc()).all()
            total_campaigns = len(campaigns)
            active_campaigns = sum(1 for c in campaigns if c.status == 'active')
            try:
                total_links = TestingLink.query.count()
                total_sessions = TestingSession.query.count()
                consents_count = ParticipantConsent.query.count()
                completed_count = TestingSession.query.filter_by(completed=True).count()
                reported_count = TestingEvent.query.filter_by(event_type='suspicious_reported').count()
                file_demo_count = DemonstrationUpload.query.count()
                browser_stats = dict(
                    db.session.query(TestingSession.browser_family, func.count(TestingSession.id))
                    .group_by(TestingSession.browser_family)
                    .all()
                )
                device_stats = dict(
                    db.session.query(TestingSession.device_category, func.count(TestingSession.id))
                    .group_by(TestingSession.device_category)
                    .all()
                )
                recent_events = TestingEvent.query.order_by(TestingEvent.id.desc()).limit(20).all()
                recent_uploads = DemonstrationUpload.query.filter_by(deleted_at=None).order_by(DemonstrationUpload.id.desc()).limit(10).all()
                recent_links = TestingLink.query.order_by(TestingLink.id.desc()).limit(20).all()
                session_counts = dict(
                    db.session.query(TestingSession.campaign_id, func.count(TestingSession.id))
                    .group_by(TestingSession.campaign_id)
                    .all()
                )
            except Exception:
                total_links = total_sessions = consents_count = completed_count = 0
                reported_count = file_demo_count = 0
                browser_stats = device_stats = {}
                recent_events = recent_uploads = recent_links = []
                session_counts = {}

        return render_template(
            'security_platform/dashboard.html',
            campaigns=campaigns,
            total_campaigns=total_campaigns,
            active_campaigns=active_campaigns,
            total_links=total_links,
            total_sessions=total_sessions,
            consents_count=consents_count,
            completed_count=completed_count,
            reported_count=reported_count,
            file_demo_count=file_demo_count,
            browser_stats=browser_stats,
            device_stats=device_stats,
            recent_events=recent_events,
            recent_uploads=recent_uploads,
            recent_links=recent_links,
            session_counts=session_counts,
            templates=DEFAULT_SCENARIO_TEMPLATES
        )

    # -----------------------------------------------------------------------
    # Campaign Management
    # -----------------------------------------------------------------------
    @bp.route('/security/campaign/create', methods=['POST'])
    @admin_required
    def campaign_create():
        name = request.form.get('name', '').strip()
        desc = request.form.get('description', '').strip()
        scenario = request.form.get('scenario_type', 'credential_audit')
        platforms = request.form.getlist('target_platforms') or ['whatsapp', 'telegram', 'linkedin']
        ttl_hours = int(request.form.get('link_ttl_hours', 48))
        max_uses = int(request.form.get('max_uses_per_link', 0))

        if not name:
            flash('Campaign name is required.', 'danger')
            return redirect(url_for('security_platform.operations_dashboard'))

        c = TestingCampaign(
            name=name,
            description=desc,
            scenario_type=scenario,
            target_platforms=','.join(platforms),
            status='active',
            link_ttl_hours=ttl_hours,
            max_uses_per_link=max_uses,
            created_at=utcnow_naive()
        )
        db.session.add(c)
        db.session.commit()

        # Audit log
        db.session.add(SecurityAuditLog(action='campaign_created', target=f"Campaign #{c.id}: {c.name}", details=f"Platforms: {c.target_platforms}"))
        db.session.commit()

        flash(f'Security testing campaign "{c.name}" created successfully.', 'success')
        return redirect(url_for('security_platform.operations_dashboard'))

    @bp.route('/security/campaign/<int:cid>/status', methods=['POST'])
    @admin_required
    def campaign_status(cid):
        c = db.session.get(TestingCampaign, cid)
        if not c:
            abort(404)
        new_status = request.form.get('status')
        if new_status in ['active', 'paused', 'closed']:
            c.status = new_status
            db.session.commit()
            db.session.add(SecurityAuditLog(action='campaign_status_updated', target=f"Campaign #{c.id}", details=f"Status changed to {new_status}"))
            db.session.commit()
            flash(f'Campaign status set to {new_status}.', 'info')
        return redirect(url_for('security_platform.operations_dashboard'))

    # -----------------------------------------------------------------------
    # Link Generator
    # -----------------------------------------------------------------------
    @bp.route('/security/link/generate', methods=['POST'])
    @admin_required
    def link_generate():
        cid = request.form.get('campaign_id', type=int)
        alias = (request.form.get('participant_alias') or request.form.get('participant_name') or '').strip()
        email = request.form.get('participant_email', '').strip()
        dept = request.form.get('participant_department', 'General').strip()
        scenario_key = request.form.get('scenario_key', 'whatsapp').strip()
        ttl_hours = request.form.get('ttl_hours', type=int) or 48
        max_uses = request.form.get('max_uses', type=int)
        if max_uses is None:
            max_uses = request.form.get('max_usages', type=int) or 0

        camp = db.session.get(TestingCampaign, cid)
        if not camp:
            flash('Select an active campaign.', 'danger')
            return redirect(url_for('security_platform.operations_dashboard'))

        participant = None
        if alias:
            participant = TestingParticipant(
                campaign_id=camp.id,
                alias=alias,
                email=email,
                department=dept,
                created_at=utcnow_naive()
            )
            db.session.add(participant)
            db.session.flush()

        raw_token, link = create_testing_link(
            campaign_id=camp.id,
            participant_id=participant.id if participant else None,
            ttl_hours=ttl_hours,
            max_uses=max_uses
        )
        db.session.add(link)
        db.session.commit()

        configured_base = (current_app.config.get('BASE_URL') or os.getenv('BASE_URL', '')).strip().rstrip('/')
        base_url = configured_base or request.host_url.rstrip('/')
        if current_app.config.get('IS_PRODUCTION') and base_url.startswith('http://'):
            base_url = 'https://' + base_url[len('http://'):]

        testing_url = f"{base_url}/test/{raw_token}"
        qr_svg = generate_qr_svg(testing_url)

        platforms_order = ['whatsapp', 'telegram', 'linkedin', 'x', 'instagram', 'facebook_messenger']
        distributions = {
            plat: build_distribution_payload(plat, alias or 'Authorized Participant', testing_url)
            for plat in platforms_order
        }

        db.session.add(SecurityAuditLog(action='link_generated', target=f"Link #{link.id}", details=f"Campaign #{camp.id}, Token: {raw_token[:8]}..."))
        db.session.commit()

        flash(f'Testing link generated successfully: {testing_url}', 'success')
        return render_template(
            'security_platform/link_created.html',
            campaign=camp,
            participant=participant,
            link=link,
            raw_token=raw_token,
            testing_url=testing_url,
            qr_svg=qr_svg,
            distributions=distributions,
            scenario_key=scenario_key
        )

    @bp.route('/security/link/<int:lid>/revoke', methods=['POST'])
    @admin_required
    def link_revoke(lid):
        link = db.session.get(TestingLink, lid)
        if not link:
            abort(404)
        link.is_revoked = True
        link.revoked_at = utcnow_naive()
        db.session.commit()
        db.session.add(SecurityAuditLog(action='link_revoked', target=f"Link #{link.id}", details=f"Revoked token {link.token_hash[:8]}..."))
        db.session.commit()
        flash('Link revoked. Further attempts to access this URL will be blocked with HTTP 410.', 'warning')
        return redirect(url_for('security_platform.operations_dashboard'))

    # -----------------------------------------------------------------------
    # Message Generator & Distribution
    # -----------------------------------------------------------------------
    @bp.route('/security/message/preview', methods=['POST'])
    @admin_required
    def message_preview():
        platform = request.form.get('platform', 'whatsapp')
        alias = request.form.get('participant_alias', 'Employee_Alpha')
        token = request.form.get('token', 'sample-token-12345')
        base_url = request.host_url.rstrip('/')
        testing_url = f"{base_url}/test/{token}"

        payload = build_distribution_payload(platform, alias, testing_url)
        return jsonify(payload)

    # -----------------------------------------------------------------------
    # Live Real-Time Event Stream (Server-Sent Events)
    # -----------------------------------------------------------------------
    @bp.route('/security/events/stream')
    @admin_required
    def events_stream():
        """SSE stream endpoint pushing live telemetry events to admin dashboard."""
        def event_generator():
            q = broadcaster.subscribe()
            try:
                # Initial keep-alive ping
                yield f": connected to real-time event pipeline\n\n"
                while True:
                    try:
                        evt = q.get(timeout=20)
                        data_str = json.dumps(evt)
                        yield f"data: {data_str}\n\n"
                    except Exception:
                        # Keep-alive heartbeat ping every 20s
                        yield f": keep-alive\n\n"
            finally:
                broadcaster.unsubscribe(q)

        return Response(event_generator(), mimetype='text/event-stream', headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        })

    # -----------------------------------------------------------------------
    # Controlled File Demonstration Management
    # -----------------------------------------------------------------------
    @bp.route('/security/file-demonstrations/<int:fid>/delete', methods=['POST'], endpoint='file_delete')
    @bp.route('/security/file-demonstration/<int:fid>/delete', methods=['POST'], endpoint='file_demo_delete')
    @admin_required
    def file_delete(fid):
        upload = db.session.get(DemonstrationUpload, fid)
        if not upload:
            abort(404)
        
        upload_dir = os.getenv('UPLOAD_FOLDER', os.path.join('database', 'demonstration_uploads'))
        file_path = os.path.join(upload_dir, upload.stored_filename)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
        
        upload.deleted_at = utcnow_naive()
        db.session.commit()
        db.session.add(SecurityAuditLog(action='demonstration_file_deleted', target=f"Upload #{upload.id}", details=f"File: {upload.original_filename}"))
        db.session.commit()

        flash(f'Demonstration file "{upload.original_filename}" securely deleted from disk.', 'info')
        return redirect(url_for('security_platform.operations_dashboard'))

    # -----------------------------------------------------------------------
    # Reporting & Analytics
    # -----------------------------------------------------------------------
    @bp.route('/security/reports/csv')
    @admin_required
    def export_csv():
        """Export comprehensive security testing events as CSV."""
        events = TestingEvent.query.order_by(TestingEvent.id.desc()).all()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            'Event ID', 'Campaign ID', 'Event Type', 'Browser Family',
            'OS Family', 'Device Category', 'Details', 'Timestamp UTC'
        ])
        for e in events:
            writer.writerow([
                e.id, e.campaign_id, e.event_type, e.browser_family,
                e.os_family, e.device_category, e.details,
                e.timestamp.strftime('%Y-%m-%d %H:%M:%S') if e.timestamp else ''
            ])
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=phishlab_security_telemetry.csv'}
        )

    @bp.route('/security/reports/print/<int:cid>')
    @admin_required
    def print_report(cid):
        """Printable executive security report."""
        camp = db.session.get(TestingCampaign, cid)
        if not camp:
            abort(404)

        total_links = TestingLink.query.filter_by(campaign_id=camp.id).count()
        total_sessions = TestingSession.query.filter_by(campaign_id=camp.id).count()
        consents = ParticipantConsent.query.filter_by(campaign_id=camp.id).count()
        completed = TestingSession.query.filter_by(campaign_id=camp.id, completed=True).count()
        reported = TestingEvent.query.filter_by(campaign_id=camp.id, event_type='suspicious_reported').count()
        uploads = DemonstrationUpload.query.filter_by(campaign_id=camp.id).count()

        return render_template(
            'security_platform/report_print.html',
            campaign=camp,
            total_links=total_links,
            total_sessions=total_sessions,
            consents=consents,
            completed=completed,
            reported=reported,
            uploads=uploads,
            now=utcnow_naive()
        )
