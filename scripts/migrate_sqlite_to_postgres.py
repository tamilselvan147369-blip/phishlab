"""Database Migration Utility: SQLite to PostgreSQL for PhishLab.

Safely copies all existing records from a local SQLite database or verified backup
to a target PostgreSQL database (e.g., Neon PostgreSQL).
Preserves all primary keys, foreign keys, timestamps, UUIDs, password hashes,
and resets PostgreSQL auto-increment sequences.

Dry-run mode is strictly read-only and never modifies the target database.
Re-running the migration skips already-existing primary keys so records are
never duplicated.

Usage:
    python scripts/migrate_sqlite_to_postgres.py --source "sqlite:///database/backups/phishlab_backup_20261125_070209.db" --target "<DATABASE_URL>" --dry-run
"""

import os
import sys
import argparse
import urllib.parse
from sqlalchemy import create_engine, MetaData, select, text

# Add project root to sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from database import db

# Dependency-ordered list of tables to insert parent tables before child tables
TABLE_ORDER = [
    # Core
    'campaigns',
    'events',

    # Real-App Testing
    'real_app_exercise',
    'exercise_participant',
    'manual_event_confirmation',
    'realapp_audit_log',

    # Social Simulation
    'social_simulations',
    'social_message_templates',
    'simulation_configurations',
    'generated_scenarios',
    'generated_messages',
    'simulated_conversations',
    'simulated_messages',
    'simulation_participants',
    'simulation_events',
    'awareness_responses',

    # Security Platform
    'testing_campaigns',
    'testing_participants',
    'testing_links',
    'testing_sessions',
    'participant_consents',
    'testing_events',
    'demonstration_uploads',
    'platform_message_templates',
    'message_distributions',
    'security_audit_logs',
]


def normalize_db_url(url: str) -> str:
    """Normalize database URL for SQLAlchemy 2.x, psycopg2, and Neon SSL."""
    if not url:
        return ""
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif url.startswith("postgresql://") and "+psycopg2" not in url:
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
    if "neon.tech" in url and "sslmode=" not in url:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}sslmode=require"
    return url


def redact_db_url(url: str) -> str:
    """Redact username and password from a database URI for safe logging."""
    if not url:
        return "<unset>"
    if url.startswith("sqlite"):
        return f"sqlite:///{os.path.basename(url.split('///')[-1])}"
    parsed = urllib.parse.urlparse(url)
    host = parsed.hostname or "unknown-host"
    port = f":{parsed.port}" if parsed.port else ""
    db_name = parsed.path or ""
    return f"{parsed.scheme}://***:***@{host}{port}{db_name}"


def migrate(source_url: str, target_url: str, dry_run: bool = False):
    print("=" * 68)
    print("PHISHLAB DATABASE MIGRATION: SQLITE -> POSTGRESQL")
    print("=" * 68)
    print(f"Source Database: {redact_db_url(source_url)}")
    print(f"Target Database: {redact_db_url(target_url)}")
    print(f"Dry Run Mode:    {dry_run}\n")

    norm_source = normalize_db_url(source_url)
    norm_target = normalize_db_url(target_url)

    source_engine = create_engine(norm_source)
    target_kwargs = {"pool_pre_ping": True}
    if "neon.tech" in norm_target:
        target_kwargs["connect_args"] = {"sslmode": "require"}
    target_engine = create_engine(norm_target, **target_kwargs)

    # Test connections
    try:
        with source_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✓ Connected to source SQLite database.")
    except Exception as e:
        print(f"✗ Failed connecting to source database: {e}")
        sys.exit(1)

    try:
        with target_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✓ Connected to target database.")
    except Exception as e:
        print(f"✗ Failed connecting to target database: {e}")
        sys.exit(1)

    # Import all models so db.metadata contains all 26 tables
    import security_platform.models  # noqa: F401
    import social_simulation.models  # noqa: F401
    import real_app_testing.models  # noqa: F401
    import database  # noqa: F401

    if not dry_run:
        db.metadata.create_all(bind=target_engine)
        print("✓ Target database schema synchronized (all 26 tables initialized).\n")
    else:
        print("✓ Dry-run mode: target schema will NOT be modified.\n")

    source_meta = MetaData()
    source_meta.reflect(bind=source_engine)

    target_meta = MetaData()
    target_meta.reflect(bind=target_engine)

    stats = []
    source_table_count = len([t for t in TABLE_ORDER if t in source_meta.tables])
    target_table_count = len([t for t in TABLE_ORDER if t in target_meta.tables])
    total_target_existing = 0

    with source_engine.connect() as s_conn, target_engine.connect() as t_conn:
        for table_name in TABLE_ORDER:
            if table_name not in source_meta.tables:
                continue

            s_table = source_meta.tables[table_name]
            t_table = target_meta.tables.get(table_name)

            rows = s_conn.execute(select(s_table)).mappings().all()
            source_count = len(rows)

            if t_table is None:
                if dry_run:
                    stats.append((table_name, source_count, 0, source_count))
                else:
                    print(f"⚠️  Skipping {table_name}: not found in target schema.")
                continue

            existing_ids = set()
            existing_count = 0
            if 'id' in t_table.columns:
                existing_ids = {r[0] for r in t_conn.execute(select(t_table.c.id)).all()}
                existing_count = len(existing_ids)
            else:
                existing_count = t_conn.execute(text(f'SELECT COUNT(*) FROM "{table_name}"')).scalar() or 0
            total_target_existing += existing_count

            rows_to_insert = []
            for row in rows:
                data = dict(row)
                if 'id' in t_table.columns and data.get('id') in existing_ids:
                    continue
                filtered = {str(k): v for k, v in data.items() if str(k) in t_table.columns}
                rows_to_insert.append(filtered)

            if dry_run:
                stats.append((table_name, source_count, existing_count, len(rows_to_insert)))
                continue

            inserted = 0
            if rows_to_insert:
                for filtered in rows_to_insert:
                    t_conn.execute(t_table.insert().values(filtered))
                    inserted += 1
                t_conn.commit()

            # Reset PostgreSQL serial sequences to prevent ID collision on new inserts
            try:
                if 'id' in t_table.columns and target_engine.dialect.name == 'postgresql':
                    seq_query = text(
                        f"SELECT setval(pg_get_serial_sequence('{table_name}', 'id'), "
                        f"COALESCE(MAX(id), 1)) FROM {table_name};"
                    )
                    t_conn.execute(seq_query)
                    t_conn.commit()
            except Exception:
                pass

            stats.append((table_name, source_count, existing_count, inserted))

    # Print summary table
    print("=" * 78)
    col_last = "TO MIGRATE" if dry_run else "MIGRATED"
    print(f"{'TABLE NAME':<30} {'SRC ROWS':<12} {'TGT EXISTING':<14} {col_last:<12}")
    print("=" * 78)
    total_src = 0
    total_action = 0
    for name, src, tgt_ex, act in stats:
        total_src += src
        total_action += act
        status_flag = "(dry run)" if dry_run else "✓"
        print(f"{name:<30} {src:<12} {tgt_ex:<14} {act:<12} {status_flag}")
    print("-" * 78)
    print(f"Source tables: {source_table_count} | Target tables present: {target_table_count}")
    print(f"{'TOTAL':<30} {total_src:<12} {total_target_existing:<14} {total_action:<12}")
    print("=" * 78)
    if dry_run:
        print("\nDry-run completed cleanly. Target database was NOT modified.")
    else:
        print("\nMigration completed successfully!")

    source_engine.dispose()
    target_engine.dispose()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Migrate PhishLab SQLite database to PostgreSQL.")
    parser.add_argument(
        '--source',
        default=f"sqlite:///{os.path.abspath(os.path.join(BASE_DIR, 'database', 'phishlab.db'))}",
        help="Source database URI (default: database/phishlab.db)",
    )
    parser.add_argument(
        '--target',
        default=os.getenv('TARGET_DATABASE_URL', os.getenv('DATABASE_URL')),
        help="Target PostgreSQL database URI (or set TARGET_DATABASE_URL / DATABASE_URL)",
    )
    parser.add_argument('--dry-run', action='store_true', help="Preview row counts without writing to target")

    args = parser.parse_args()

    if not args.target:
        print("Error: Target database URL is required. Provide --target <url> or set DATABASE_URL.")
        sys.exit(1)

    migrate(args.source, args.target, dry_run=args.dry_run)
