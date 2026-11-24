"""Database setup and models for PhishLab.

Provides SQLAlchemy models for Campaign and Event, and a helper to
initialise the SQLite database.
"""

import os
import uuid
from typing import Any, Optional
from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm.decl_api import _declarative_constructor

db = SQLAlchemy()

def utcnow_naive():
    """Return timezone-naive UTC datetime for SQLite compatibility."""
    return datetime.now(timezone.utc).replace(tzinfo=None)

def _init_sa_model(instance, **kwargs):
    filtered = {k: v for k, v in kwargs.items() if v is not None}
    _declarative_constructor(instance, **filtered)

class Campaign(db.Model):
    __tablename__ = 'campaigns'
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String, nullable=False)
    scenario = db.Column(db.String, nullable=False)
    subject = db.Column(db.String, nullable=False)
    sender_name = db.Column(db.String, nullable=False)
    recipient = db.Column(db.String, nullable=False)
    template = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), nullable=False, default='Draft')
    created_at = db.Column(db.DateTime, default=utcnow_naive)

    def __init__(
        self,
        name: Optional[str] = None,
        scenario: Optional[str] = None,
        subject: Optional[str] = None,
        sender_name: Optional[str] = None,
        recipient: Optional[str] = None,
        template: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
        uuid: Optional[str] = None,
        created_at: Optional[datetime] = None,
        **kwargs: Any
    ):
        if name is not None: kwargs['name'] = name
        if scenario is not None: kwargs['scenario'] = scenario
        if subject is not None: kwargs['subject'] = subject
        if sender_name is not None: kwargs['sender_name'] = sender_name
        if recipient is not None: kwargs['recipient'] = recipient
        if template is not None: kwargs['template'] = template
        if description is not None: kwargs['description'] = description
        if status is not None: kwargs['status'] = status
        if uuid is not None: kwargs['uuid'] = uuid
        if created_at is not None: kwargs['created_at'] = created_at
        _init_sa_model(self, **kwargs)

class Event(db.Model):
    __tablename__ = 'events'
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaigns.id'), nullable=False)
    event_type = db.Column(db.String, nullable=False)
    timestamp = db.Column(db.DateTime, default=utcnow_naive)
    campaign = db.relationship('Campaign', backref='events')

    def __init__(
        self,
        campaign_id: Optional[int] = None,
        event_type: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        campaign: Optional[Any] = None,
        **kwargs: Any
    ):
        if campaign_id is not None: kwargs['campaign_id'] = campaign_id
        if event_type is not None: kwargs['event_type'] = event_type
        if timestamp is not None: kwargs['timestamp'] = timestamp
        if campaign is not None: kwargs['campaign'] = campaign
        _init_sa_model(self, **kwargs)

def init_db(app):
    """Initialise the SQLite database.

    This drops existing tables and recreates them, ensuring the schema
    (including newly added columns such as `uuid` and `status`) is up‑to‑date.
    In a production setting you would use proper migrations; for this
    academic demo a full reset is acceptable.
    """
    db.init_app(app)
    with app.app_context():
        os.makedirs('database', exist_ok=True)
        # Ensure all models are loaded in SQLAlchemy metadata before create_all
        try:
            import security_platform.models
        except ImportError:
            pass
        db.create_all()
        # Safe idempotent column migration for SQLite
        try:
            from sqlalchemy import inspect, text
            inspector = inspect(db.engine)
            if 'testing_links' in inspector.get_table_names():
                cols = [c['name'] for c in inspector.get_columns('testing_links')]
                if 'scenario_key' not in cols:
                    db.session.execute(text("ALTER TABLE testing_links ADD COLUMN scenario_key VARCHAR(64) DEFAULT 'security_alert'"))
                    db.session.commit()
        except Exception:
            pass
