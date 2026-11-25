"""Safe database connection verification script for PhishLab.

Reads DATABASE_URL (or POSTGRES_URL / NEON_DATABASE_URL) from the environment,
connects to the database, executes SELECT 1, reports dialect and SSL status
without exposing credentials or the full connection URL, and closes safely.
"""

import os
import sys
import urllib.parse
from sqlalchemy import create_engine, text

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from scripts.migrate_sqlite_to_postgres import normalize_db_url, redact_db_url


def check_connection(raw_url: str | None = None) -> tuple[bool, dict]:
    """Verify database connectivity and return (ok, info_dict) without leaking secrets."""
    url = (
        raw_url
        or os.getenv("DATABASE_URL")
        or os.getenv("POSTGRES_URL")
        or os.getenv("NEON_DATABASE_URL")
        or ""
    ).strip()

    if not url:
        return False, {"error": "DATABASE_URL is not set in the environment."}

    norm_url = normalize_db_url(url)
    parsed = urllib.parse.urlparse(norm_url)
    query_params = urllib.parse.parse_qs(parsed.query)
    ssl_mode = (query_params.get("sslmode") or ["unspecified"])[0]
    is_neon = "neon.tech" in (parsed.hostname or "")

    engine_kwargs = {"pool_pre_ping": True}
    if is_neon:
        engine_kwargs["connect_args"] = {"sslmode": "require"}

    engine = None
    try:
        engine = create_engine(norm_url, **engine_kwargs)
        with engine.connect() as conn:
            val = conn.execute(text("SELECT 1")).scalar()
        return (val == 1), {
            "dialect": engine.dialect.name,
            "target": redact_db_url(norm_url),
            "sslmode": ssl_mode,
            "neon_tls": is_neon,
        }
    except Exception as exc:
        return False, {
            "target": redact_db_url(norm_url),
            "sslmode": ssl_mode,
            "error": str(exc).split("@")[-1],
        }
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    ok, info = check_connection()
    if ok:
        print("✓ Database connection verified.")
        print(f"  Dialect:  {info['dialect']}")
        print(f"  Target:   {info['target']}")
        print(f"  SSL Mode: {info['sslmode']}")
        sys.exit(0)
    else:
        print("✗ Database connection failed.")
        for k, v in info.items():
            print(f"  {k}: {v}")
        sys.exit(1)
