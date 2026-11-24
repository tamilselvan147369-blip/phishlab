"""Database models for the Multi-Platform Social Media Simulation Engine.

Supports 6 social platforms: WhatsApp, Instagram, Facebook Messenger,
Telegram, X (Twitter), and LinkedIn in a safe, controlled local environment.
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

SOCIAL_PLATFORMS = {
    'whatsapp': 'WhatsApp',
    'instagram': 'Instagram',
    'facebook_messenger': 'Facebook Messenger',
    'telegram': 'Telegram',
    'x': 'X (Twitter)',
    'linkedin': 'LinkedIn',
}

# ---------------------------------------------------------------------------
# SocialSimulation – represents an overarching simulation campaign
# ---------------------------------------------------------------------------
class SocialSimulation(db.Model):
    __tablename__ = 'social_simulations'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text, default='')
    platforms = db.Column(db.String(256), nullable=False, default='whatsapp,instagram,facebook_messenger,telegram,x,linkedin')
    status = db.Column(db.String(20), nullable=False, default='active')
    created_at = db.Column(db.DateTime, default=utcnow_naive)

    conversations = db.relationship('SimulatedConversation', back_populates='simulation', cascade='all, delete-orphan')
    participants = db.relationship('SimulationParticipant', back_populates='simulation', cascade='all, delete-orphan')
    events = db.relationship('SimulationEvent', back_populates='simulation', cascade='all, delete-orphan')

    def __init__(self, name=None, description=None, platforms=None, status='active', created_at=None, **kwargs):
        if name is not None: kwargs['name'] = name
        if description is not None: kwargs['description'] = description
        if platforms is not None: kwargs['platforms'] = platforms
        if status is not None: kwargs['status'] = status
        if created_at is not None: kwargs['created_at'] = created_at
        _init_sa_model(self, **kwargs)

    def get_platform_list(self):
        return [p.strip() for p in (self.platforms or '').split(',') if p.strip()]

    def __repr__(self):
        return f"<SocialSimulation {self.id}: {self.name}>"

# ---------------------------------------------------------------------------
# SocialMessageTemplate – predefined & custom scenario message templates
# ---------------------------------------------------------------------------
class SocialMessageTemplate(db.Model):
    __tablename__ = 'social_message_templates'

    id = db.Column(db.Integer, primary_key=True)
    platform = db.Column(db.String(32), nullable=False)
    scenario_type = db.Column(db.String(64), nullable=False)  # e.g., 'urgent_security', 'recruitment', 'fake_contest'
    sender_name = db.Column(db.String(64), nullable=False)
    sender_handle = db.Column(db.String(64), default='')
    sender_avatar = db.Column(db.String(128), default='')
    content = db.Column(db.Text, nullable=False)
    simulated_link = db.Column(db.String(256), default='')
    attachment_name = db.Column(db.String(128), default='')
    attachment_type = db.Column(db.String(32), default='')  # e.g., 'pdf', 'image', 'document'
    is_suspicious = db.Column(db.Boolean, default=True)
    red_flags = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=utcnow_naive)

    def __init__(
        self,
        platform=None,
        scenario_type=None,
        sender_name=None,
        sender_handle=None,
        sender_avatar=None,
        content=None,
        simulated_link=None,
        attachment_name=None,
        attachment_type=None,
        is_suspicious=True,
        red_flags=None,
        created_at=None,
        **kwargs
    ):
        if platform is not None: kwargs['platform'] = platform
        if scenario_type is not None: kwargs['scenario_type'] = scenario_type
        if sender_name is not None: kwargs['sender_name'] = sender_name
        if sender_handle is not None: kwargs['sender_handle'] = sender_handle
        if sender_avatar is not None: kwargs['sender_avatar'] = sender_avatar
        if content is not None: kwargs['content'] = content
        if simulated_link is not None: kwargs['simulated_link'] = simulated_link
        if attachment_name is not None: kwargs['attachment_name'] = attachment_name
        if attachment_type is not None: kwargs['attachment_type'] = attachment_type
        if is_suspicious is not None: kwargs['is_suspicious'] = is_suspicious
        if red_flags is not None: kwargs['red_flags'] = red_flags
        if created_at is not None: kwargs['created_at'] = created_at
        _init_sa_model(self, **kwargs)

    def __repr__(self):
        return f"<SocialMessageTemplate {self.id}: {self.platform}/{self.scenario_type}>"

# ---------------------------------------------------------------------------
# SimulatedConversation – thread/chat container within a simulation
# ---------------------------------------------------------------------------
class SimulatedConversation(db.Model):
    __tablename__ = 'simulated_conversations'

    id = db.Column(db.Integer, primary_key=True)
    simulation_id = db.Column(db.Integer, db.ForeignKey('social_simulations.id', ondelete='CASCADE'), nullable=False)
    platform = db.Column(db.String(32), nullable=False)
    conversation_type = db.Column(db.String(32), default='one_to_one')  # 'one_to_one', 'group', 'channel', 'bot', 'request'
    title = db.Column(db.String(128), nullable=False)
    sender_avatar = db.Column(db.String(128), default='')
    subtitle = db.Column(db.String(128), default='')
    is_request = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=utcnow_naive)

    simulation = db.relationship('SocialSimulation', back_populates='conversations')
    messages = db.relationship('SimulatedMessage', back_populates='conversation', cascade='all, delete-orphan', order_by='SimulatedMessage.id')

    def __init__(
        self,
        simulation_id=None,
        platform=None,
        conversation_type='one_to_one',
        title=None,
        sender_avatar=None,
        subtitle=None,
        is_request=False,
        created_at=None,
        simulation=None,
        **kwargs
    ):
        if simulation_id is not None: kwargs['simulation_id'] = simulation_id
        if platform is not None: kwargs['platform'] = platform
        if conversation_type is not None: kwargs['conversation_type'] = conversation_type
        if title is not None: kwargs['title'] = title
        if sender_avatar is not None: kwargs['sender_avatar'] = sender_avatar
        if subtitle is not None: kwargs['subtitle'] = subtitle
        if is_request is not None: kwargs['is_request'] = is_request
        if created_at is not None: kwargs['created_at'] = created_at
        if simulation is not None: kwargs['simulation'] = simulation
        _init_sa_model(self, **kwargs)

    def __repr__(self):
        return f"<SimulatedConversation {self.id}: {self.platform} - {self.title}>"

# ---------------------------------------------------------------------------
# SimulatedMessage – individual message bubble in a conversation
# ---------------------------------------------------------------------------
class SimulatedMessage(db.Model):
    __tablename__ = 'simulated_messages'

    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('simulated_conversations.id', ondelete='CASCADE'), nullable=False)
    sender_name = db.Column(db.String(64), nullable=False)
    sender_handle = db.Column(db.String(64), default='')
    sender_avatar = db.Column(db.String(128), default='')
    is_from_user = db.Column(db.Boolean, default=False)
    content = db.Column(db.Text, nullable=False)
    simulated_link = db.Column(db.String(256), default='')
    attachment_name = db.Column(db.String(128), default='')
    attachment_type = db.Column(db.String(32), default='')
    read_status = db.Column(db.String(16), default='read')  # 'sent', 'delivered', 'read'
    is_suspicious = db.Column(db.Boolean, default=False)
    educational_notes = db.Column(db.Text, default='')
    timestamp = db.Column(db.DateTime, default=utcnow_naive)

    conversation = db.relationship('SimulatedConversation', back_populates='messages')

    def __init__(
        self,
        conversation_id=None,
        sender_name=None,
        sender_handle=None,
        sender_avatar=None,
        is_from_user=False,
        content=None,
        simulated_link=None,
        attachment_name=None,
        attachment_type=None,
        read_status='read',
        is_suspicious=False,
        educational_notes=None,
        timestamp=None,
        conversation=None,
        **kwargs
    ):
        if conversation_id is not None: kwargs['conversation_id'] = conversation_id
        if sender_name is not None: kwargs['sender_name'] = sender_name
        if sender_handle is not None: kwargs['sender_handle'] = sender_handle
        if sender_avatar is not None: kwargs['sender_avatar'] = sender_avatar
        if is_from_user is not None: kwargs['is_from_user'] = is_from_user
        if content is not None: kwargs['content'] = content
        if simulated_link is not None: kwargs['simulated_link'] = simulated_link
        if attachment_name is not None: kwargs['attachment_name'] = attachment_name
        if attachment_type is not None: kwargs['attachment_type'] = attachment_type
        if read_status is not None: kwargs['read_status'] = read_status
        if is_suspicious is not None: kwargs['is_suspicious'] = is_suspicious
        if educational_notes is not None: kwargs['educational_notes'] = educational_notes
        if timestamp is not None: kwargs['timestamp'] = timestamp
        if conversation is not None: kwargs['conversation'] = conversation
        _init_sa_model(self, **kwargs)

    def __repr__(self):
        return f"<SimulatedMessage {self.id} in Conv {self.conversation_id}>"

# ---------------------------------------------------------------------------
# SimulationParticipant – tracks participant consent and training progression
# ---------------------------------------------------------------------------
class SimulationParticipant(db.Model):
    __tablename__ = 'simulation_participants'

    id = db.Column(db.Integer, primary_key=True)
    simulation_id = db.Column(db.Integer, db.ForeignKey('social_simulations.id', ondelete='CASCADE'), nullable=False)
    participant_uuid = db.Column(db.String(36), default=lambda: str(uuid.uuid4()), unique=True, nullable=False)
    alias = db.Column(db.String(64), default='Participant')
    email = db.Column(db.String(128), default='')
    consent_given = db.Column(db.Boolean, default=False)
    consent_timestamp = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow_naive)

    simulation = db.relationship('SocialSimulation', back_populates='participants')
    events = db.relationship('SimulationEvent', back_populates='participant', cascade='all, delete-orphan')
    responses = db.relationship('AwarenessResponse', back_populates='participant', cascade='all, delete-orphan')

    def __init__(
        self,
        simulation_id=None,
        participant_uuid=None,
        alias=None,
        email=None,
        consent_given=False,
        consent_timestamp=None,
        created_at=None,
        simulation=None,
        **kwargs
    ):
        if simulation_id is not None: kwargs['simulation_id'] = simulation_id
        if participant_uuid is not None: kwargs['participant_uuid'] = participant_uuid
        if alias is not None: kwargs['alias'] = alias
        if email is not None: kwargs['email'] = email
        if consent_given is not None: kwargs['consent_given'] = consent_given
        if consent_timestamp is not None: kwargs['consent_timestamp'] = consent_timestamp
        if created_at is not None: kwargs['created_at'] = created_at
        if simulation is not None: kwargs['simulation'] = simulation
        _init_sa_model(self, **kwargs)

    def __repr__(self):
        return f"<SimulationParticipant {self.participant_uuid} ({self.alias})>"

# ---------------------------------------------------------------------------
# SimulationEvent – interaction tracking in the social media simulator
# ---------------------------------------------------------------------------
class SimulationEvent(db.Model):
    __tablename__ = 'simulation_events'

    id = db.Column(db.Integer, primary_key=True)
    simulation_id = db.Column(db.Integer, db.ForeignKey('social_simulations.id', ondelete='CASCADE'), nullable=False)
    participant_id = db.Column(db.Integer, db.ForeignKey('simulation_participants.id', ondelete='CASCADE'), nullable=True)
    platform = db.Column(db.String(32), nullable=False)
    conversation_id = db.Column(db.Integer, nullable=True)
    message_id = db.Column(db.Integer, nullable=True)
    event_type = db.Column(db.String(48), nullable=False)  # 'conversation_opened', 'message_viewed', 'link_clicked', etc.
    details = db.Column(db.Text, default='')
    timestamp = db.Column(db.DateTime, default=utcnow_naive)

    simulation = db.relationship('SocialSimulation', back_populates='events')
    participant = db.relationship('SimulationParticipant', back_populates='events')

    def __init__(
        self,
        simulation_id=None,
        participant_id=None,
        platform=None,
        conversation_id=None,
        message_id=None,
        event_type=None,
        details=None,
        timestamp=None,
        simulation=None,
        participant=None,
        **kwargs
    ):
        if simulation_id is not None: kwargs['simulation_id'] = simulation_id
        if participant_id is not None: kwargs['participant_id'] = participant_id
        if platform is not None: kwargs['platform'] = platform
        if conversation_id is not None: kwargs['conversation_id'] = conversation_id
        if message_id is not None: kwargs['message_id'] = message_id
        if event_type is not None: kwargs['event_type'] = event_type
        if details is not None: kwargs['details'] = details
        if timestamp is not None: kwargs['timestamp'] = timestamp
        if simulation is not None: kwargs['simulation'] = simulation
        if participant is not None: kwargs['participant'] = participant
        _init_sa_model(self, **kwargs)

    def __repr__(self):
        return f"<SimulationEvent {self.event_type} on {self.platform}>"

# ---------------------------------------------------------------------------
# AwarenessResponse – participant responses to security awareness questions
# ---------------------------------------------------------------------------
class AwarenessResponse(db.Model):
    __tablename__ = 'awareness_responses'

    id = db.Column(db.Integer, primary_key=True)
    simulation_id = db.Column(db.Integer, db.ForeignKey('social_simulations.id', ondelete='CASCADE'), nullable=False)
    participant_id = db.Column(db.Integer, db.ForeignKey('simulation_participants.id', ondelete='CASCADE'), nullable=True)
    platform = db.Column(db.String(32), nullable=False)
    message_id = db.Column(db.Integer, nullable=True)
    question_text = db.Column(db.Text, nullable=False)
    selected_option = db.Column(db.String(256), nullable=False)
    is_correct = db.Column(db.Boolean, default=False)
    explanation = db.Column(db.Text, default='')
    timestamp = db.Column(db.DateTime, default=utcnow_naive)

    participant = db.relationship('SimulationParticipant', back_populates='responses')

    def __init__(
        self,
        simulation_id=None,
        participant_id=None,
        platform=None,
        message_id=None,
        question_text=None,
        selected_option=None,
        is_correct=False,
        explanation=None,
        timestamp=None,
        participant=None,
        **kwargs
    ):
        if simulation_id is not None: kwargs['simulation_id'] = simulation_id
        if participant_id is not None: kwargs['participant_id'] = participant_id
        if platform is not None: kwargs['platform'] = platform
        if message_id is not None: kwargs['message_id'] = message_id
        if question_text is not None: kwargs['question_text'] = question_text
        if selected_option is not None: kwargs['selected_option'] = selected_option
        if is_correct is not None: kwargs['is_correct'] = is_correct
        if explanation is not None: kwargs['explanation'] = explanation
        if timestamp is not None: kwargs['timestamp'] = timestamp
        if participant is not None: kwargs['participant'] = participant
        _init_sa_model(self, **kwargs)

    def __repr__(self):
        return f"<AwarenessResponse for {self.platform}: Correct={self.is_correct}>"


# ===========================================================================
# UNIFIED SIMULATION GENERATOR MODELS
# ===========================================================================

class GeneratedScenario(db.Model):
    __tablename__ = 'generated_scenarios'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128), nullable=False)
    category = db.Column(db.String(64), nullable=False)
    platform = db.Column(db.String(32), nullable=False)
    fictional_sender = db.Column(db.String(64), nullable=False)
    sender_handle = db.Column(db.String(64), default='')
    sender_avatar = db.Column(db.String(128), default='')
    message_content = db.Column(db.Text, nullable=False)
    language = db.Column(db.String(16), default='en')
    simulated_link = db.Column(db.String(256), default='')
    simulated_attachment = db.Column(db.String(128), default='')
    attachment_type = db.Column(db.String(32), default='')
    warning_indicators = db.Column(db.Text, default='')
    educational_objective = db.Column(db.Text, default='')
    expected_action = db.Column(db.String(128), default='')
    awareness_explanation = db.Column(db.Text, default='')
    risk_category = db.Column(db.String(32), default='High')
    complexity_level = db.Column(db.String(32), default='Intermediate')
    tone = db.Column(db.String(32), default='Urgent')
    is_saved_template = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=utcnow_naive)

    messages = db.relationship('GeneratedMessage', back_populates='scenario', cascade='all, delete-orphan')

    def __init__(
        self,
        title=None,
        category=None,
        platform=None,
        fictional_sender=None,
        sender_handle=None,
        sender_avatar=None,
        message_content=None,
        language='en',
        simulated_link=None,
        simulated_attachment=None,
        attachment_type=None,
        warning_indicators=None,
        educational_objective=None,
        expected_action=None,
        awareness_explanation=None,
        risk_category='High',
        complexity_level='Intermediate',
        tone='Urgent',
        is_saved_template=False,
        created_at=None,
        **kwargs
    ):
        if title is not None: kwargs['title'] = title
        if category is not None: kwargs['category'] = category
        if platform is not None: kwargs['platform'] = platform
        if fictional_sender is not None: kwargs['fictional_sender'] = fictional_sender
        if sender_handle is not None: kwargs['sender_handle'] = sender_handle
        if sender_avatar is not None: kwargs['sender_avatar'] = sender_avatar
        if message_content is not None: kwargs['message_content'] = message_content
        if language is not None: kwargs['language'] = language
        if simulated_link is not None: kwargs['simulated_link'] = simulated_link
        if simulated_attachment is not None: kwargs['simulated_attachment'] = simulated_attachment
        if attachment_type is not None: kwargs['attachment_type'] = attachment_type
        if warning_indicators is not None: kwargs['warning_indicators'] = warning_indicators
        if educational_objective is not None: kwargs['educational_objective'] = educational_objective
        if expected_action is not None: kwargs['expected_action'] = expected_action
        if awareness_explanation is not None: kwargs['awareness_explanation'] = awareness_explanation
        if risk_category is not None: kwargs['risk_category'] = risk_category
        if complexity_level is not None: kwargs['complexity_level'] = complexity_level
        if tone is not None: kwargs['tone'] = tone
        if is_saved_template is not None: kwargs['is_saved_template'] = is_saved_template
        if created_at is not None: kwargs['created_at'] = created_at
        _init_sa_model(self, **kwargs)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'category': self.category,
            'platform': self.platform,
            'fictional_sender': self.fictional_sender,
            'sender_handle': self.sender_handle,
            'sender_avatar': self.sender_avatar,
            'message_content': self.message_content,
            'language': self.language,
            'simulated_link': self.simulated_link,
            'simulated_attachment': self.simulated_attachment,
            'attachment_type': self.attachment_type,
            'warning_indicators': self.warning_indicators,
            'educational_objective': self.educational_objective,
            'expected_action': self.expected_action,
            'awareness_explanation': self.awareness_explanation,
            'risk_category': self.risk_category,
            'complexity_level': self.complexity_level,
            'tone': self.tone,
            'is_saved_template': self.is_saved_template,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else ''
        }


class GeneratedMessage(db.Model):
    __tablename__ = 'generated_messages'

    id = db.Column(db.Integer, primary_key=True)
    scenario_id = db.Column(db.Integer, db.ForeignKey('generated_scenarios.id', ondelete='CASCADE'), nullable=False)
    platform = db.Column(db.String(32), nullable=False)
    format_type = db.Column(db.String(32), default='individual')
    sender_name = db.Column(db.String(64), nullable=False)
    sender_handle = db.Column(db.String(64), default='')
    sender_avatar = db.Column(db.String(128), default='')
    rendered_content = db.Column(db.Text, nullable=False)
    meta_json = db.Column(db.Text, default='{}')
    created_at = db.Column(db.DateTime, default=utcnow_naive)

    scenario = db.relationship('GeneratedScenario', back_populates='messages')

    def __init__(
        self,
        scenario_id=None,
        platform=None,
        format_type='individual',
        sender_name=None,
        sender_handle=None,
        sender_avatar=None,
        rendered_content=None,
        meta_json='{}',
        created_at=None,
        scenario=None,
        **kwargs
    ):
        if scenario_id is not None: kwargs['scenario_id'] = scenario_id
        if platform is not None: kwargs['platform'] = platform
        if format_type is not None: kwargs['format_type'] = format_type
        if sender_name is not None: kwargs['sender_name'] = sender_name
        if sender_handle is not None: kwargs['sender_handle'] = sender_handle
        if sender_avatar is not None: kwargs['sender_avatar'] = sender_avatar
        if rendered_content is not None: kwargs['rendered_content'] = rendered_content
        if meta_json is not None: kwargs['meta_json'] = meta_json
        if created_at is not None: kwargs['created_at'] = created_at
        if scenario is not None: kwargs['scenario'] = scenario
        _init_sa_model(self, **kwargs)


class SimulationConfiguration(db.Model):
    __tablename__ = 'simulation_configurations'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    platforms = db.Column(db.String(256), default='whatsapp,instagram,facebook_messenger,telegram,x,linkedin')
    scenario_category = db.Column(db.String(64), default='account_security')
    language = db.Column(db.String(16), default='en')
    ai_provider = db.Column(db.String(32), default='local')
    settings_json = db.Column(db.Text, default='{}')
    created_at = db.Column(db.DateTime, default=utcnow_naive)

    def __init__(
        self,
        name=None,
        platforms=None,
        scenario_category=None,
        language='en',
        ai_provider='local',
        settings_json='{}',
        created_at=None,
        **kwargs
    ):
        if name is not None: kwargs['name'] = name
        if platforms is not None: kwargs['platforms'] = platforms
        if scenario_category is not None: kwargs['scenario_category'] = scenario_category
        if language is not None: kwargs['language'] = language
        if ai_provider is not None: kwargs['ai_provider'] = ai_provider
        if settings_json is not None: kwargs['settings_json'] = settings_json
        if created_at is not None: kwargs['created_at'] = created_at
        _init_sa_model(self, **kwargs)

