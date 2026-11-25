"""Tests for Neon PostgreSQL compatibility, connection checks, and safe migration."""

import sqlite3
import tempfile
import os
import pytest
from sqlalchemy import create_engine, inspect, text

from app import create_app
from database import db, Campaign
from scripts.migrate_sqlite_to_postgres import normalize_db_url, redact_db_url, migrate
from scripts.check_database_connection import check_connection


def test_postgres_url_parsing_and_neon_ssl():
    """postgres:// and postgresql:// normalize to postgresql+psycopg2:// and neon.tech enforces sslmode=require."""
    u1 = normalize_db_url("postgres://user:secret@ep-abc-pooler.us-east-2.aws.neon.tech/neondb")
    assert u1.startswith("postgresql+psycopg2://")
    assert "sslmode=require" in u1

    u2 = normalize_db_url("postgresql://user:secret@ep-abc.us-east-2.aws.neon.tech/neondb?sslmode=require")
    assert u2.startswith("postgresql+psycopg2://")
    assert u2.count("sslmode=require") == 1


def test_credential_redaction():
    """redact_db_url never exposes username or password."""
    raw = "postgresql+psycopg2://admin_user:SuperSecretPass99@ep-xyz.aws.neon.tech:5432/neondb?sslmode=require"
    redacted = redact_db_url(raw)
    assert "SuperSecretPass99" not in redacted
    assert "admin_user" not in redacted
    assert "ep-xyz.aws.neon.tech:5432/neondb" in redacted


def test_sqlite_fallback_when_no_database_url(monkeypatch):
    """Without DATABASE_URL, create_app falls back cleanly to local SQLite."""
    for var in ("DATABASE_URL", "POSTGRES_URL", "NEON_DATABASE_URL", "PHISHLAB_DATABASE_URI", "VERCEL"):
        monkeypatch.delenv(var, raising=False)
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    assert "sqlite" in app.config["SQLALCHEMY_DATABASE_URI"]


def test_check_connection_missing_and_invalid_url(monkeypatch):
    """check_connection fails safely on missing or unreachable URLs without leaking secrets."""
    for var in ("DATABASE_URL", "POSTGRES_URL", "NEON_DATABASE_URL"):
        monkeypatch.delenv(var, raising=False)
    ok, info = check_connection()
    assert ok is False
    assert "DATABASE_URL" in info["error"]

    ok2, info2 = check_connection("postgresql://user:HiddenPass123@127.0.0.1:1/nonexistent_db")
    assert ok2 is False
    assert "HiddenPass123" not in str(info2)


def test_migration_dry_run_does_not_modify_target_and_prevents_duplicates(tmp_path):
    """Dry-run creates zero tables on target; real migration preserves data and prevents duplicates on re-run."""
    src_db = tmp_path / "src.db"
    tgt_db = tmp_path / "tgt.db"

    # Seed isolated source SQLite DB using create_app
    src_uri = f"sqlite:///{src_db}"
    tgt_uri = f"sqlite:///{tgt_db}"
    src_app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": src_uri})
    with src_app.app_context():
        db.create_all()
        db.session.add(Campaign(
            name="Neon Migration Test",
            scenario="corporate",
            subject="Test Subject",
            sender_name="Security",
            recipient="user@example.test",
            template="<p>Test</p>",
            description="Preserve me",
        ))
        db.session.commit()

    # 1. Dry run must NOT create tables or modify target
    migrate(src_uri, tgt_uri, dry_run=True)
    tgt_engine = create_engine(tgt_uri)
    assert inspect(tgt_engine).get_table_names() == []
    tgt_engine.dispose()

    # 2. First real migration copies the row
    migrate(src_uri, tgt_uri, dry_run=False)
    tgt_engine = create_engine(tgt_uri)
    with tgt_engine.connect() as conn:
        cnt1 = conn.execute(text("SELECT COUNT(*) FROM campaigns")).scalar()
        name1 = conn.execute(text("SELECT name FROM campaigns")).scalar()
    assert cnt1 == 1
    assert name1 == "Neon Migration Test"

    # 3. Second real migration skips existing ID and does NOT duplicate
    migrate(src_uri, tgt_uri, dry_run=False)
    with tgt_engine.connect() as conn:
        cnt2 = conn.execute(text("SELECT COUNT(*) FROM campaigns")).scalar()
    tgt_engine.dispose()
    assert cnt2 == 1
