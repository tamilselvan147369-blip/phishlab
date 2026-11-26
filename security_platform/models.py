"""Database models for the Real-Time Phishing Security Testing Platform.

Reuses the shared SQLAlchemy instance defined in ``database.py``.
All models maintain explicit constructor signatures with _init_sa_model
for static analysis compliance and SQLAlchemy 2.x compatibility.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy.orm.decl_api import _declarative_constructor

from database import db


def utcnow_naive():
    """Return timezone-naive UTC datetime for SQLite compatibility."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _init_sa_model(instance, **kwargs):
    filtered = {k: v for k, v in kwargs.items() if v is not None}
    _declarative_constructor(instance, **filtered)


# ---------------------------------------------------------------------------
# TestingCampaign
# ---------------------------------------------------------------------------
class TestingCampaign(db.Model):
    __test__ = False
    __tablename__ = 'testing_campaigns'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text, default='')
    objective = db.Column(db.String(256), default='')
    scenario_type = db.Column(db.String(64), default='credential_audit')
    target_platforms = db.Column(db.String(256), default='whatsapp,instagram,facebook_messenger,telegram,x,linkedin')
    status = db.Column(db.String(20), default='active')  # 'active', 'paused', 'closed'
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    max_uses_per_link = db.Column(db.Integer, default=0)  # 0 = unlimited within TTL
    link_ttl_hours = db.Column(db.Integer, default=48)
    created_at = db.Column(db.DateTime, default=utcnow_naive)
    updated_at = db.Column(db.DateTime, default=utcnow_naive, onupdate=utcnow_naive)

    participants = db.relationship('TestingParticipant', back_populates='campaign', cascade='all, delete-orphan')
    links = db.relationship('TestingLink', back_populates='campaign', cascade='all, delete-orphan')
    events = db.relationship('TestingEvent', back_populates='campaign', cascade='all, delete-orphan')
    uploads = db.relationship('DemonstrationUpload', back_populates='campaign', cascade='all, delete-orphan')
    distributions = db.relationship('MessageDistribution', back_populates='campaign', cascade='all, delete-orphan')

    def __init__(
        self,
        name=None,
        description=None,
        objective=None,
        scenario_type='credential_audit',
        target_platforms='whatsapp,instagram,facebook_messenger,telegram,x,linkedin',
        status='active',
        start_date=None,
        end_date=None,
        max_uses_per_link=0,
        link_ttl_hours=48,
        created_at=None,
        updated_at=None,
        **kwargs
    ):
        if name is not None: kwargs['name'] = name
        if description is not None: kwargs['description'] = description
        if objective is not None: kwargs['objective'] = objective
        if scenario_type is not None: kwargs['scenario_type'] = scenario_type
        if target_platforms is not None: kwargs['target_platforms'] = target_platforms
        if status is not None: kwargs['status'] = status
        if start_date is not None: kwargs['start_date'] = start_date
        if end_date is not None: kwargs['end_date'] = end_date
        if max_uses_per_link is not None: kwargs['max_uses_per_link'] = max_uses_per_link
        if link_ttl_hours is not None: kwargs['link_ttl_hours'] = link_ttl_hours
        if created_at is not None: kwargs['created_at'] = created_at
        if updated_at is not None: kwargs['updated_at'] = updated_at
        _init_sa_model(self, **kwargs)

    def get_platforms(self):
        return [p.strip() for p in (self.target_platforms or '').split(',') if p.strip()]

    def __repr__(self):
        return f"<TestingCampaign {self.id}: {self.name}>"


# ---------------------------------------------------------------------------
# TestingParticipant
# ---------------------------------------------------------------------------
class TestingParticipant(db.Model):
    __test__ = False
    __tablename__ = 'testing_participants'

    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('testing_campaigns.id', ondelete='CASCADE'), nullable=False)
    participant_uuid = db.Column(db.String(36), default=lambda: str(uuid.uuid4()), unique=True, nullable=False)
    alias = db.Column(db.String(64), nullable=False)
    email = db.Column(db.String(128), default='')
    department = db.Column(db.String(64), default='General')
    created_at = db.Column(db.DateTime, default=utcnow_naive)

    campaign = db.relationship('TestingCampaign', back_populates='participants')
    links = db.relationship('TestingLink', back_populates='participant', cascade='all, delete-orphan')
    sessions = db.relationship('TestingSession', back_populates='participant')
    events = db.relationship('TestingEvent', back_populates='participant')
    uploads = db.relationship('DemonstrationUpload', back_populates='participant')

    def __init__(
        self,
        campaign_id=None,
        participant_uuid=None,
        alias=None,
        name=None,
        email=None,
        department='General',
        created_at=None,
        campaign=None,
        **kwargs
    ):
        if name is not None and alias is None:
            alias = name
        if campaign_id is not None: kwargs['campaign_id'] = campaign_id
        if participant_uuid is not None: kwargs['participant_uuid'] = participant_uuid
        if alias is not None: kwargs['alias'] = alias
        if email is not None: kwargs['email'] = email
        if department is not None: kwargs['department'] = department
        if created_at is not None: kwargs['created_at'] = created_at
        if campaign is not None: kwargs['campaign'] = campaign
        _init_sa_model(self, **kwargs)

    @property
    def name(self):
        return self.alias

    def __repr__(self):
        return f"<TestingParticipant {self.id}: {self.alias}>"


# ---------------------------------------------------------------------------
# TestingLink
# ---------------------------------------------------------------------------
class TestingLink(db.Model):
    __test__ = False
    __tablename__ = 'testing_links'

    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('testing_campaigns.id', ondelete='CASCADE'), nullable=False)
    participant_id = db.Column(db.Integer, db.ForeignKey('testing_participants.id', ondelete='CASCADE'), nullable=True)
    scenario_key = db.Column(db.String(64), default='security_alert')
    token_hash = db.Column(db.String(64), unique=True, nullable=False, index=True)
    raw_token = db.Column(db.String(64), default='')  # Stored for authorized admin retrieval/copying
    destination_path = db.Column(db.String(128), default='/test')
    max_uses = db.Column(db.Integer, default=0)
    use_count = db.Column(db.Integer, default=0)
    expires_at = db.Column(db.DateTime, nullable=False)
    revoked_at = db.Column(db.DateTime, nullable=True)
    is_revoked = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=utcnow_naive)

    campaign = db.relationship('TestingCampaign', back_populates='links')
    participant = db.relationship('TestingParticipant', back_populates='links')
    sessions = db.relationship('TestingSession', back_populates='link', cascade='all, delete-orphan')
    events = db.relationship('TestingEvent', back_populates='link')

    def __init__(
        self,
        campaign_id=None,
        participant_id=None,
        scenario_key='security_alert',
        token_hash=None,
        raw_token=None,
        destination_path='/test',
        max_uses=0,
        max_usages=None,
        use_count=0,
        expires_at=None,
        revoked_at=None,
        is_revoked=False,
        created_at=None,
        campaign=None,
        participant=None,
        **kwargs
    ):
        if campaign_id is not None: kwargs['campaign_id'] = campaign_id
        if participant_id is not None: kwargs['participant_id'] = participant_id
        if scenario_key is not None: kwargs['scenario_key'] = scenario_key
        if token_hash is not None: kwargs['token_hash'] = token_hash
        if raw_token is not None: kwargs['raw_token'] = raw_token
        if destination_path is not None: kwargs['destination_path'] = destination_path
        if max_usages is not None: kwargs['max_uses'] = max_usages
        elif max_uses is not None: kwargs['max_uses'] = max_uses
        if use_count is not None: kwargs['use_count'] = use_count
        if expires_at is not None: kwargs['expires_at'] = expires_at
        if revoked_at is not None: kwargs['revoked_at'] = revoked_at
        if is_revoked is not None: kwargs['is_revoked'] = is_revoked
        if created_at is not None: kwargs['created_at'] = created_at
        if campaign is not None: kwargs['campaign'] = campaign
        if participant is not None: kwargs['participant'] = participant
        _init_sa_model(self, **kwargs)

    @property
    def max_usages(self):
        return self.max_uses

    @max_usages.setter
    def max_usages(self, val):
        self.max_uses = val

    @property
    def is_expired(self):
        return utcnow_naive() > self.expires_at

    @property
    def is_usable(self):
        if self.is_revoked or self.is_expired:
            return False
        if self.max_uses > 0 and self.use_count >= self.max_uses:
            return False
        return True

    def __repr__(self):
        return f"<TestingLink {self.id}: Hash={self.token_hash[:8]}...>"


# ---------------------------------------------------------------------------
# TestingSession
# ---------------------------------------------------------------------------
class TestingSession(db.Model):
    __test__ = False
    __tablename__ = 'testing_sessions'

    id = db.Column(db.Integer, primary_key=True)
    session_uuid = db.Column(db.String(36), default=lambda: str(uuid.uuid4()), unique=True, nullable=False)
    campaign_id = db.Column(db.Integer, db.ForeignKey('testing_campaigns.id', ondelete='CASCADE'), nullable=False)
    link_id = db.Column(db.Integer, db.ForeignKey('testing_links.id', ondelete='CASCADE'), nullable=False)
    participant_id = db.Column(db.Integer, db.ForeignKey('testing_participants.id', ondelete='SET NULL'), nullable=True)
    ip_hash = db.Column(db.String(64), default='')
    user_agent = db.Column(db.String(256), default='')
    browser_family = db.Column(db.String(64), default='Unknown')
    browser_version = db.Column(db.String(32), default='')
    os_family = db.Column(db.String(64), default='Unknown')
    device_category = db.Column(db.String(32), default='Desktop')
    referrer = db.Column(db.String(256), default='')
    screen_resolution = db.Column(db.String(32), default='')
    has_consented = db.Column(db.Boolean, default=False)
    completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=utcnow_naive)

    link = db.relationship('TestingLink', back_populates='sessions')
    participant = db.relationship('TestingParticipant', back_populates='sessions')
    consent = db.relationship('ParticipantConsent', back_populates='session', uselist=False, cascade='all, delete-orphan')
    events = db.relationship('TestingEvent', back_populates='session', cascade='all, delete-orphan')
    uploads = db.relationship('DemonstrationUpload', back_populates='session', cascade='all, delete-orphan')

    def __init__(
        self,
        session_uuid=None,
        campaign_id=None,
        link_id=None,
        participant_id=None,
        ip_hash=None,
        user_agent=None,
        browser_family='Unknown',
        browser_version=None,
        os_family='Unknown',
        device_category='Desktop',
        referrer=None,
        screen_resolution=None,
        has_consented=False,
        completed=False,
        created_at=None,
        **kwargs
    ):
        if session_uuid is not None: kwargs['session_uuid'] = session_uuid
        if campaign_id is not None: kwargs['campaign_id'] = campaign_id
        if link_id is not None: kwargs['link_id'] = link_id
        if participant_id is not None: kwargs['participant_id'] = participant_id
        if ip_hash is not None: kwargs['ip_hash'] = ip_hash
        if user_agent is not None: kwargs['user_agent'] = user_agent
        if browser_family is not None: kwargs['browser_family'] = browser_family
        if browser_version is not None: kwargs['browser_version'] = browser_version
        if os_family is not None: kwargs['os_family'] = os_family
        if device_category is not None: kwargs['device_category'] = device_category
        if referrer is not None: kwargs['referrer'] = referrer
        if screen_resolution is not None: kwargs['screen_resolution'] = screen_resolution
        if has_consented is not None: kwargs['has_consented'] = has_consented
        if completed is not None: kwargs['completed'] = completed
        if created_at is not None: kwargs['created_at'] = created_at
        _init_sa_model(self, **kwargs)

    def __repr__(self):
        return f"<TestingSession {self.session_uuid[:8]}>"


# ---------------------------------------------------------------------------
# ParticipantConsent
# ---------------------------------------------------------------------------
class ParticipantConsent(db.Model):
    __tablename__ = 'participant_consents'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('testing_sessions.id', ondelete='CASCADE'), nullable=False, unique=True)
    participant_id = db.Column(db.Integer, db.ForeignKey('testing_participants.id', ondelete='SET NULL'), nullable=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('testing_campaigns.id', ondelete='CASCADE'), nullable=False)
    consent_text = db.Column(db.Text, nullable=False)
    consented = db.Column(db.Boolean, default=True)
    timestamp = db.Column(db.DateTime, default=utcnow_naive)

    session = db.relationship('TestingSession', back_populates='consent')

    def __init__(
        self,
        session_id=None,
        participant_id=None,
        campaign_id=None,
        consent_text=None,
        consented=True,
        timestamp=None,
        **kwargs
    ):
        if session_id is not None: kwargs['session_id'] = session_id
        if participant_id is not None: kwargs['participant_id'] = participant_id
        if campaign_id is not None: kwargs['campaign_id'] = campaign_id
        if consent_text is not None: kwargs['consent_text'] = consent_text
        if consented is not None: kwargs['consented'] = consented
        if timestamp is not None: kwargs['timestamp'] = timestamp
        _init_sa_model(self, **kwargs)


# ---------------------------------------------------------------------------
# TestingEvent
# ---------------------------------------------------------------------------
class TestingEvent(db.Model):
    __test__ = False
    __tablename__ = 'testing_events'

    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('testing_campaigns.id', ondelete='CASCADE'), nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey('testing_sessions.id', ondelete='SET NULL'), nullable=True)
    participant_id = db.Column(db.Integer, db.ForeignKey('testing_participants.id', ondelete='SET NULL'), nullable=True)
    link_id = db.Column(db.Integer, db.ForeignKey('testing_links.id', ondelete='SET NULL'), nullable=True)
    event_type = db.Column(db.String(64), nullable=False)  # 'link_opened', 'consent_submitted', 'suspicious_reported', 'file_selected', 'file_uploaded', 'assessment_completed'
    browser_family = db.Column(db.String(64), default='Unknown')
    os_family = db.Column(db.String(64), default='Unknown')
    device_category = db.Column(db.String(32), default='Desktop')
    details = db.Column(db.Text, default='')
    timestamp = db.Column(db.DateTime, default=utcnow_naive)

    campaign = db.relationship('TestingCampaign', back_populates='events')
    session = db.relationship('TestingSession', back_populates='events')
    participant = db.relationship('TestingParticipant', back_populates='events')
    link = db.relationship('TestingLink', back_populates='events')

    def __init__(
        self,
        campaign_id=None,
        session_id=None,
        participant_id=None,
        link_id=None,
        event_type=None,
        browser_family='Unknown',
        os_family='Unknown',
        device_category='Desktop',
        details=None,
        timestamp=None,
        **kwargs
    ):
        if campaign_id is not None: kwargs['campaign_id'] = campaign_id
        if session_id is not None: kwargs['session_id'] = session_id
        if participant_id is not None: kwargs['participant_id'] = participant_id
        if link_id is not None: kwargs['link_id'] = link_id
        if event_type is not None: kwargs['event_type'] = event_type
        if browser_family is not None: kwargs['browser_family'] = browser_family
        if os_family is not None: kwargs['os_family'] = os_family
        if device_category is not None: kwargs['device_category'] = device_category
        if details is not None: kwargs['details'] = details
        if timestamp is not None: kwargs['timestamp'] = timestamp
        _init_sa_model(self, **kwargs)

    def to_dict(self):
        return {
            'id': self.id,
            'campaign_id': self.campaign_id,
            'event_type': self.event_type,
            'browser_family': self.browser_family,
            'os_family': self.os_family,
            'device_category': self.device_category,
            'details': self.details,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S') if self.timestamp else ''
        }


# ---------------------------------------------------------------------------
# DemonstrationUpload
# ---------------------------------------------------------------------------
class DemonstrationUpload(db.Model):
    __test__ = False
    __tablename__ = 'demonstration_uploads'

    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('testing_campaigns.id', ondelete='CASCADE'), nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey('testing_sessions.id', ondelete='CASCADE'), nullable=False)
    participant_id = db.Column(db.Integer, db.ForeignKey('testing_participants.id', ondelete='SET NULL'), nullable=True)
    original_filename = db.Column(db.String(128), nullable=False)
    stored_filename = db.Column(db.String(128), nullable=False, unique=True)
    file_size_bytes = db.Column(db.Integer, default=0)
    mime_type = db.Column(db.String(64), default='application/octet-stream')
    sha256_hash = db.Column(db.String(64), nullable=False)
    consent_acknowledged = db.Column(db.Boolean, default=True)
    deleted_at = db.Column(db.DateTime, nullable=True)
    uploaded_at = db.Column(db.DateTime, default=utcnow_naive)

    campaign = db.relationship('TestingCampaign', back_populates='uploads')
    session = db.relationship('TestingSession', back_populates='uploads')
    participant = db.relationship('TestingParticipant', back_populates='uploads')

    def __init__(
        self,
        campaign_id=None,
        session_id=None,
        participant_id=None,
        original_filename=None,
        stored_filename=None,
        file_size_bytes=0,
        mime_type='application/octet-stream',
        sha256_hash=None,
        consent_acknowledged=True,
        deleted_at=None,
        uploaded_at=None,
        **kwargs
    ):
        if campaign_id is not None: kwargs['campaign_id'] = campaign_id
        if session_id is not None: kwargs['session_id'] = session_id
        if participant_id is not None: kwargs['participant_id'] = participant_id
        if original_filename is not None: kwargs['original_filename'] = original_filename
        if stored_filename is not None: kwargs['stored_filename'] = stored_filename
        if file_size_bytes is not None: kwargs['file_size_bytes'] = file_size_bytes
        if mime_type is not None: kwargs['mime_type'] = mime_type
        if sha256_hash is not None: kwargs['sha256_hash'] = sha256_hash
        if consent_acknowledged is not None: kwargs['consent_acknowledged'] = consent_acknowledged
        if deleted_at is not None: kwargs['deleted_at'] = deleted_at
        if uploaded_at is not None: kwargs['uploaded_at'] = uploaded_at
        _init_sa_model(self, **kwargs)

    @property
    def file_hash_sha256(self):
        return self.sha256_hash


# ---------------------------------------------------------------------------
# PlatformMessageTemplate
# ---------------------------------------------------------------------------
class PlatformMessageTemplate(db.Model):
    __tablename__ = 'platform_message_templates'

    id = db.Column(db.Integer, primary_key=True)
    platform = db.Column(db.String(32), nullable=False)  # whatsapp, instagram, facebook_messenger, telegram, x, linkedin
    scenario_title = db.Column(db.String(128), nullable=False)
    sender_name = db.Column(db.String(64), nullable=False)
    sender_handle = db.Column(db.String(64), default='')
    message_body = db.Column(db.Text, nullable=False)
    red_flags = db.Column(db.Text, default='')
    educational_explanation = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=utcnow_naive)

    def __init__(
        self,
        platform=None,
        scenario_title=None,
        sender_name=None,
        sender_handle=None,
        message_body=None,
        red_flags=None,
        educational_explanation=None,
        created_at=None,
        **kwargs
    ):
        if platform is not None: kwargs['platform'] = platform
        if scenario_title is not None: kwargs['scenario_title'] = scenario_title
        if sender_name is not None: kwargs['sender_name'] = sender_name
        if sender_handle is not None: kwargs['sender_handle'] = sender_handle
        if message_body is not None: kwargs['message_body'] = message_body
        if red_flags is not None: kwargs['red_flags'] = red_flags
        if educational_explanation is not None: kwargs['educational_explanation'] = educational_explanation
        if created_at is not None: kwargs['created_at'] = created_at
        _init_sa_model(self, **kwargs)


# ---------------------------------------------------------------------------
# MessageDistribution
# ---------------------------------------------------------------------------
class MessageDistribution(db.Model):
    __tablename__ = 'message_distributions'

    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('testing_campaigns.id', ondelete='CASCADE'), nullable=False)
    participant_id = db.Column(db.Integer, db.ForeignKey('testing_participants.id', ondelete='CASCADE'), nullable=False)
    link_id = db.Column(db.Integer, db.ForeignKey('testing_links.id', ondelete='CASCADE'), nullable=False)
    platform = db.Column(db.String(32), nullable=False)
    delivery_channel = db.Column(db.String(32), default='manual_dispatch')  # 'manual_dispatch', 'official_api'
    dispatch_status = db.Column(db.String(32), default='dispatched')  # 'pending', 'dispatched', 'confirmed_delivered', 'failed'
    dispatched_at = db.Column(db.DateTime, default=utcnow_naive)
    delivery_confirmed_at = db.Column(db.DateTime, nullable=True)

    campaign = db.relationship('TestingCampaign', back_populates='distributions')
    participant = db.relationship('TestingParticipant')
    link = db.relationship('TestingLink')

    def __init__(
        self,
        campaign_id=None,
        participant_id=None,
        link_id=None,
        platform=None,
        delivery_channel='manual_dispatch',
        dispatch_status='dispatched',
        dispatched_at=None,
        delivery_confirmed_at=None,
        **kwargs
    ):
        if campaign_id is not None: kwargs['campaign_id'] = campaign_id
        if participant_id is not None: kwargs['participant_id'] = participant_id
        if link_id is not None: kwargs['link_id'] = link_id
        if platform is not None: kwargs['platform'] = platform
        if delivery_channel is not None: kwargs['delivery_channel'] = delivery_channel
        if dispatch_status is not None: kwargs['dispatch_status'] = dispatch_status
        if dispatched_at is not None: kwargs['dispatched_at'] = dispatched_at
        if delivery_confirmed_at is not None: kwargs['delivery_confirmed_at'] = delivery_confirmed_at
        _init_sa_model(self, **kwargs)


# ---------------------------------------------------------------------------
# SecurityAuditLog
# ---------------------------------------------------------------------------
class SecurityAuditLog(db.Model):
    __tablename__ = 'security_audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    actor = db.Column(db.String(64), default='admin')
    action = db.Column(db.String(64), nullable=False)
    target = db.Column(db.String(128), default='')
    details = db.Column(db.Text, default='')
    timestamp = db.Column(db.DateTime, default=utcnow_naive)

    def __init__(
        self,
        actor='admin',
        action=None,
        target=None,
        details=None,
        timestamp=None,
        **kwargs
    ):
        if actor is not None: kwargs['actor'] = actor
        if action is not None: kwargs['action'] = action
        if target is not None: kwargs['target'] = target
        if details is not None: kwargs['details'] = details
        if timestamp is not None: kwargs['timestamp'] = timestamp
        _init_sa_model(self, **kwargs)
