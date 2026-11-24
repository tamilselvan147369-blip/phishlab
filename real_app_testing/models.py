"""Database models for the RealAppTesting subsystem.

All models use the shared SQLAlchemy instance defined in ``database.py``.
No circular imports are introduced because ``db`` is imported lazily at
module import time – the Flask app creates the instance before any
models are imported.
"""

import uuid
from typing import Any, Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm.decl_api import _declarative_constructor

from database import db  # shared SQLAlchemy instance

def utcnow_naive():
    """Return timezone-naive UTC datetime for SQLite compatibility without deprecation."""
    return datetime.now(timezone.utc).replace(tzinfo=None)

def _init_sa_model(instance, **kwargs):
    filtered = {k: v for k, v in kwargs.items() if v is not None}
    _declarative_constructor(instance, **filtered)

# ---------------------------------------------------------------------------
# Helper constants
# ---------------------------------------------------------------------------
PLATFORMS = {
    "whatsapp",
    "instagram",
    "facebook_messenger",
    "telegram",
    "x",
    "linkedin",
}

# ---------------------------------------------------------------------------
# RealAppExercise – represents a manual real‑app testing exercise.
# ---------------------------------------------------------------------------
class RealAppExercise(db.Model):
    __tablename__ = "real_app_exercise"

    id = db.Column(db.Integer, primary_key=True)
    # FK to the existing Campaign table (table name is ``campaigns``)
    campaign_id = db.Column(
        db.Integer,
        db.ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
    )
    campaign = db.relationship("Campaign", backref="real_app_exercises")

    platform = db.Column(db.String(32), nullable=False)
    demo_token_hash = db.Column(db.String(64), unique=True, nullable=False)
    token_expires_at = db.Column(db.DateTime, nullable=False)
    revoked_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default='active')
    exercise_name = db.Column(db.String, nullable=True)
    description = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=utcnow_naive)

    # Relationships to participants and manual confirmations
    participants = db.relationship(
        "ExerciseParticipant",
        back_populates="exercise",
        cascade="all, delete-orphan",
    )
    confirmations = db.relationship(
        "ManualEventConfirmation",
        back_populates="exercise",
        cascade="all, delete-orphan",
    )

    def __init__(
        self,
        campaign_id: Optional[int] = None,
        platform: Optional[str] = None,
        demo_token_hash: Optional[str] = None,
        token_expires_at: Optional[datetime] = None,
        revoked_at: Optional[datetime] = None,
        status: Optional[str] = None,
        exercise_name: Optional[str] = None,
        description: Optional[str] = None,
        created_at: Optional[datetime] = None,
        campaign: Optional[Any] = None,
        **kwargs: Any
    ):
        if campaign_id is not None: kwargs['campaign_id'] = campaign_id
        if platform is not None: kwargs['platform'] = platform
        if demo_token_hash is not None: kwargs['demo_token_hash'] = demo_token_hash
        if token_expires_at is not None: kwargs['token_expires_at'] = token_expires_at
        if revoked_at is not None: kwargs['revoked_at'] = revoked_at
        if status is not None: kwargs['status'] = status
        if exercise_name is not None: kwargs['exercise_name'] = exercise_name
        if description is not None: kwargs['description'] = description
        if created_at is not None: kwargs['created_at'] = created_at
        if campaign is not None: kwargs['campaign'] = campaign
        _init_sa_model(self, **kwargs)

    def __repr__(self):
        return f"<RealAppExercise {self.id} ({self.platform})>"

# ---------------------------------------------------------------------------
# ExerciseParticipant – stores a pseudonymous identifier for a participant.
# ---------------------------------------------------------------------------
class ExerciseParticipant(db.Model):
    __tablename__ = "exercise_participant"

    id = db.Column(db.Integer, primary_key=True)
    participant_uuid = db.Column(
        db.String(36),
        default=lambda: str(uuid.uuid4()),
        unique=True,
        nullable=False,
    )
    exercise_id = db.Column(
        db.Integer,
        db.ForeignKey("real_app_exercise.id", ondelete="CASCADE"),
        nullable=False,
    )
    exercise = db.relationship("RealAppExercise", back_populates="participants")

    created_at = db.Column(db.DateTime, default=utcnow_naive)

    def __init__(
        self,
        participant_uuid: Optional[str] = None,
        exercise_id: Optional[int] = None,
        exercise: Optional[Any] = None,
        created_at: Optional[datetime] = None,
        **kwargs: Any
    ):
        if participant_uuid is not None: kwargs['participant_uuid'] = participant_uuid
        if exercise_id is not None: kwargs['exercise_id'] = exercise_id
        if exercise is not None: kwargs['exercise'] = exercise
        if created_at is not None: kwargs['created_at'] = created_at
        _init_sa_model(self, **kwargs)

    def __repr__(self):
        return f"<ExerciseParticipant {self.participant_uuid}>"

# ---------------------------------------------------------------------------
# ManualEventConfirmation – records a consented participant action.
# ---------------------------------------------------------------------------
class ManualEventConfirmation(db.Model):
    __tablename__ = "manual_event_confirmation"

    id = db.Column(db.Integer, primary_key=True)
    exercise_id = db.Column(
        db.Integer,
        db.ForeignKey("real_app_exercise.id", ondelete="CASCADE"),
        nullable=False,
    )
    exercise = db.relationship("RealAppExercise", back_populates="confirmations")

    participant_id = db.Column(
        db.Integer,
        db.ForeignKey("exercise_participant.id", ondelete="SET NULL"),
        nullable=True,
    )
    participant = db.relationship("ExerciseParticipant")

    # Event type (e.g., "demo_viewed", "link_clicked")
    event_type = db.Column(db.String(32), nullable=False)
    timestamp = db.Column(db.DateTime, default=utcnow_naive)

    def __init__(
        self,
        exercise_id: Optional[int] = None,
        exercise: Optional[Any] = None,
        participant_id: Optional[int] = None,
        participant: Optional[Any] = None,
        event_type: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        **kwargs: Any
    ):
        if exercise_id is not None: kwargs['exercise_id'] = exercise_id
        if exercise is not None: kwargs['exercise'] = exercise
        if participant_id is not None: kwargs['participant_id'] = participant_id
        if participant is not None: kwargs['participant'] = participant
        if event_type is not None: kwargs['event_type'] = event_type
        if timestamp is not None: kwargs['timestamp'] = timestamp
        _init_sa_model(self, **kwargs)

    def __repr__(self):
        return f"<ManualEventConfirmation {self.event_type} at {self.timestamp}>"

# ---------------------------------------------------------------------------
# AuditLog – records admin and system actions for accountability.
# ---------------------------------------------------------------------------
class AuditLog(db.Model):
    __tablename__ = "realapp_audit_log"

    id = db.Column(db.Integer, primary_key=True)
    exercise_id = db.Column(
        db.Integer,
        db.ForeignKey("real_app_exercise.id", ondelete="SET NULL"),
        nullable=True,
    )
    exercise = db.relationship("RealAppExercise")

    action = db.Column(db.String(64), nullable=False)
    details = db.Column(db.Text, default='')
    actor = db.Column(db.String(128), default='admin')
    timestamp = db.Column(db.DateTime, default=utcnow_naive)

    def __init__(
        self,
        exercise_id: Optional[int] = None,
        exercise: Optional[Any] = None,
        action: Optional[str] = None,
        details: Optional[str] = None,
        actor: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        **kwargs: Any
    ):
        if exercise_id is not None: kwargs['exercise_id'] = exercise_id
        if exercise is not None: kwargs['exercise'] = exercise
        if action is not None: kwargs['action'] = action
        if details is not None: kwargs['details'] = details
        if actor is not None: kwargs['actor'] = actor
        if timestamp is not None: kwargs['timestamp'] = timestamp
        _init_sa_model(self, **kwargs)

    def __repr__(self):
        return f"<AuditLog {self.action} at {self.timestamp}>"
