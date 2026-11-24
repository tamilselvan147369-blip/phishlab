"""Database Migration Utility: SQLite to PostgreSQL for PhishLab.

Safely copies all existing records from the local SQLite database
(database/phishlab.db) to a target PostgreSQL database (e.g., on Render).
Preserves all primary keys, foreign keys, timestamps, UUIDs, and resets
PostgreSQL auto-increment sequences.

Usage:
    python scripts/migrate_sqlite_to_postgres.py --target "postgresql://user:pass@host/dbname"
Or set TARGET_DATABASE_URL environment variable:
    python scripts/migrate_sqlite_to_postgres.py
"""

import os
import sys
import argparse
from datetime import datetime

# Add project root to sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from sqlalchemy import create_engine, MetaData, Table, select, text, inspect
from database import db
from app import create_app

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
    'security_audit_logs'
]


def normalize_db_url(url: str) -> str:
    """Normalize database URL for SQLAlchemy 2.x and psycopg2."""
    if not url:
        return ""
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg2://", 1)
    if url.startswith("postgresql://") and "+psycopg2" not in url:
        return url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


def migrate(source_url: str, target_url: str, dry_run: bool = False):
    print("=" * 65)
    print("PHISHLAB DATABASE MIGRATION: SQLITE -> POSTGRESQL")
    print("=" * 65)
    print(f"Source Database: {source_url}")
    print(f"Target Database: {target_url.split('@')[-1] if '@' in target_url else target_url}")
    print(f"Dry Run Mode:    {dry_run}\n")

    source_engine = create_engine(normalize_db_url(source_url))
    target_engine = create_engine(normalize_db_url(target_url))

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
        print("✓ Connected to target PostgreSQL database.")
    except Exception as e:
        print(f"✗ Failed connecting to target database: {e}")
        sys.exit(1)

    # Ensure all models are imported so db.metadata contains all tables
    import security_platform.models
    import social_simulation.models
    import real_app_testing.models
    import database
    db.metadata.create_all(bind=target_engine)
    print("✓ Target database schema synchronized (all 26 tables initialized).\n")

    source_meta = MetaData()
    source_meta.reflect(bind=source_engine)

    target_meta = MetaData()
    target_meta.reflect(bind=target_engine)

    stats = []

    with source_engine.connect() as s_conn, target_engine.connect() as t_conn:
        for table_name in TABLE_ORDER:
            if table_name not in source_meta.tables:
                continue

            s_table = source_meta.tables[table_name]
            t_table = target_meta.tables.get(table_name)
            if t_table is None:
                print(f"⚠️  Skipping {table_name}: not found in target schema.")
                continue

            # Read source rows
            rows = s_conn.execute(select(s_table)).mappings().all()
            source_count = len(rows)

            if dry_run or source_count == 0:
                stats.append((table_name, source_count, 0))
                continue

            # Insert rows into target table
            inserted = 0
            for row in rows:
                data = dict(row)
                # Filter to columns that exist in target table
                filtered: dict[str, object] = {str(k): v for k, v in data.items() if str(k) in t_table.columns}
                try:
                    t_conn.execute(t_table.insert().values(filtered))
                    inserted += 1
                except Exception as ex:
                    # In case of duplicate/existing key, log and continue
                    print(f"  [Warning] {table_name} row {filtered.get('id')}: {ex}")

            t_conn.commit()

            # Reset PostgreSQL serial sequences to prevent ID collision on new inserts
            try:
                if 'id' in t_table.columns:
                    seq_query = text(f"SELECT setval(pg_get_serial_sequence('{table_name}', 'id'), COALESCE(MAX(id), 1)) FROM {table_name};")
                    t_conn.execute(seq_query)
                    t_conn.commit()
            except Exception:
                pass  # Ignore if table uses non-serial or SQLite target

            stats.append((table_name, source_count, inserted))

    # Print summary table
    print("\n" + "=" * 65)
    print(f"{'TABLE NAME':<32} {'SOURCE ROWS':<14} {'MIGRATED':<10}")
    print("=" * 65)
    total_src = 0
    total_mig = 0
    for name, src, mig in stats:
        total_src += src
        total_mig += mig
        status_flag = "✓" if src == mig else ("(dry run)" if dry_run else "⚠️")
        print(f"{name:<32} {src:<14} {mig:<10} {status_flag}")
    print("-" * 65)
    print(f"{'TOTAL':<32} {total_src:<14} {total_mig:<10}")
    print("=" * 65)
    print("\nMigration completed successfully!")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Migrate PhishLab SQLite database to PostgreSQL.")
    parser.add_argument('--source', default=f"sqlite:///{os.path.abspath(os.path.join(BASE_DIR, 'database', 'phishlab.db'))}",
                        help="Source database URI (default: database/phishlab.db)")
    parser.add_argument('--target', default=os.getenv('TARGET_DATABASE_URL', os.getenv('DATABASE_URL')),
                        help="Target PostgreSQL database URI (or set TARGET_DATABASE_URL)")
    parser.add_argument('--dry-run', action='store_true', help="Preview row counts without writing to target")

    args = parser.parse_args()

    if not args.target:
        print("Error: Target database URL is required. Provide --target <url> or set TARGET_DATABASE_URL environment variable.")
        print("Example: python scripts/migrate_sqlite_to_postgres.py --target postgresql://user:password@host:5432/dbname")
        sys.exit(1)

    migrate(args.source, args.target, dry_run=args.dry_run)
