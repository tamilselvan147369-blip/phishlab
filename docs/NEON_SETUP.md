# PhishLab — Neon PostgreSQL Setup & Vercel Integration Guide

This guide walks through provisioning **Neon PostgreSQL** for PhishLab and connecting it to your Vercel deployment (`https://phishlab-nine.vercel.app`) without exposing secrets or risking existing local SQLite data.

---

## 1. Create Your Neon Project
1. Sign in at **[https://console.neon.tech/](https://console.neon.tech/)**.
2. Click **New Project**:
   - **Project name:** `phishlab`
   - **Database name:** `neondb` (recommended default)
   - **Region:** Choose the AWS region closest to your Vercel deployment (e.g., `AWS US East (N. Virginia)` / `us-east-1` or `AWS US East (Ohio)` / `us-east-2`).
3. Click **Create Project**.

---

## 2. Obtain the Pooled Connection String
1. On the project dashboard, click **Connect**.
2. Enable the **Connection pooling** toggle (this uses Neon's PgBouncer `-pooler` endpoint, which is recommended for Vercel serverless functions).
3. Copy the PostgreSQL connection string. It will look like:
   ```text
   postgresql://<user>:<password>@ep-<endpoint>-pooler.<region>.aws.neon.tech/neondb?sslmode=require
   ```
   > **Security:** Never commit this URL to Git, `.env.example`, or share it in chat/logs.

---

## 3. Configure `DATABASE_URL` in Vercel
1. Open **Vercel Dashboard → `phishlab-nine` → Settings → Environment Variables**.
2. Add/update:
   - **Key:** `DATABASE_URL`
   - **Value:** Your Neon **pooled** connection string (`?sslmode=require`)
   - **Environment:** **Production**
3. Save and redeploy after completing verification below.

---

## 4. Verify Connection Locally (Read-Only)
Set `DATABASE_URL` in your current PowerShell session only (not saved to Git):

```powershell
$env:DATABASE_URL = "<PASTE_YOUR_NEON_POOLED_URL>"
.\.venv\Scripts\python.exe scripts/check_database_connection.py
```

Expected output:
- `Dialect: postgresql`
- `SSL Mode: require`
- `✓ Database connection verified.` (credentials are automatically redacted)

---

## 5. Run Safe Migration Dry-Run (No Writes)
Always run a dry-run against your verified SQLite backup first:

```powershell
.\.venv\Scripts\python.exe scripts/migrate_sqlite_to_postgres.py `
  --source "sqlite:///database/backups/phishlab_backup_20261125_070209.db" `
  --target "$env:DATABASE_URL" `
  --dry-run
```

Verify that it reports `26` source tables, `52` source rows, and `Target database was NOT modified.`

---

## 6. Execute One-Time Migration (Only After Explicit Approval)
Once you have reviewed the dry-run output and confirmed you want to migrate:

```powershell
.\.venv\Scripts\python.exe scripts/migrate_sqlite_to_postgres.py `
  --source "sqlite:///database/backups/phishlab_backup_20261125_070209.db" `
  --target "$env:DATABASE_URL"
```

Re-running the script safely skips any already-migrated primary keys without duplicating records.

---

## 7. Troubleshooting
- **`sslmode` / SSL EOF errors:** Ensure `?sslmode=require` is present in `DATABASE_URL`. PhishLab also automatically enforces `sslmode=require` for `neon.tech` hosts in `app.py` and `migrate_sqlite_to_postgres.py`.
- **`too many clients` / connection limit:** Ensure you copied the **pooled** (`-pooler`) Neon URL, not the direct unpooled host. `app.py` restricts Vercel serverless pools to `pool_size=2, max_overflow=3`.
- **Tables not found:** `app.py` runs `db.create_all()` safely on startup, and `migrate_sqlite_to_postgres.py` initializes all 26 tables before inserting rows.
