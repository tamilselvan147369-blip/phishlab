# PhishLab – Academic Phishing Attack Simulation Platform

## Overview
PhishLab is a lightweight, self‑contained Flask application that demonstrates the full lifecycle of a phishing campaign **in a controlled, educational environment**. It lets you:
- Define a campaign (name, scenario, email subject, sender, recipient, template).
- Send a simulated phishing email via a local Mailpit SMTP server.
- Track events such as email sent, email opened (preview), demo link clicks and form submissions.
- View real statistics on a dark‑themed attacker dashboard powered by Chart.js.

All data is stored locally in an SQLite database; no credentials or personal data are ever collected or persisted.

## Project Structure
```
PhishLab/
├── app.py                 # Main Flask app
├── database.py            # SQLAlchemy models & init helper
├── campaign.py            # Helper for dashboard stats (optional)
├── simulator.py           # Simple async event simulator (future use)
├── requirements.txt
├── README.md
├── .env.example           # Example environment file
├── database/
│   └── phishlab.db        # SQLite DB (created on first run)
├── templates/
│   ├── dashboard.html
│   ├── campaign.html
│   ├── email_preview.html
│   ├── demo_login.html
│   └── results.html
└── static/
    ├── css/style.css
    └── js/dashboard.js
```

## Prerequisites
- **Windows 10** (or any OS with Python 3.12+).
- **Python 3.12** or newer.
- **VS Code** (or any editor/IDE).
- **Mailpit** – a local SMTP testing server. Download from https://github.com/axllent/mailpit/releases and run `mailpit` (default SMTP port 1025, UI at http://127.0.0.1:8025).

## Installation
```bash
# Clone the repository (or copy the files into a folder)
cd "e:\fish lab"

# Create a virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Configuration
1. Copy the example env file:
```bash
copy .env.example .env
```
2. Edit `.env` (optional) to set a custom secret key or Mailpit host/port:
```
FLASK_SECRET_KEY=your‑random‑secret
MAIL_SERVER=127.0.0.1
MAIL_PORT=1025
MAIL_SENDER=phishlab@example.test
```
The defaults work with a standard Mailpit installation.

## Initialise the Database
```bash
# Initialise (or reset) the SQLite DB
flask init-db
```
This creates `database/phishlab.db` with the required tables.

## Run the Application
```bash
python app.py
```
The app will start on **http://127.0.0.1:5000**. All routes are bound to `127.0.0.1` – no external access.

## Usage Walk‑through
1. Open the dashboard at `/` – you’ll see empty statistics initially.
2. Click **Create Campaign** and fill the form. Use one of the sample email templates (see below) or craft your own HTML. The *Test Recipient Email* must be an address that Mailpit will accept (e.g., `demo@example.test`).
3. Submit the form – the campaign is saved, an `email_sent` event is recorded, and the email is dispatched to Mailpit.
4. In Mailpit’s UI you can view the received message. Click **Open** to visit the preview page – this records an `email_opened` event.
5. From the preview page click **Open Demo Login Page** – this records a `demo_link_clicked` event.
6. Submit the dummy login form – a `demo_form_submitted` event is recorded.
7. Return to the dashboard to see live statistics update, and open the **Results** page for the campaign to view a timeline of events.

## Sample Email Templates
Add the following HTML strings to the **Email Template** field when creating a campaign.

### Template A – University Account Notification
```html
<p>Dear Student,</p>
<p>We have detected unusual activity on your university account. Please verify your credentials to avoid service interruption.</p>
<p><a href="{{ url_for('demo_login', cid=campaign.id, _external=True) }}">Verify Account</a></p>
<p><em>Simulation notice: This is an educational demonstration. No real credentials are collected.</em></p>
```

### Template B – Corporate Security Notification
```html
<p>Hello,</p>
<p>Your corporate email login was flagged for a possible security breach. Confirm your identity immediately.</p>
<p><a href="{{ url_for('demo_login', cid=campaign.id, _external=True) }}">Confirm Identity</a></p>
<p><em>Simulation notice: This is an educational demonstration. No real credentials are collected.</em></p>
```

### Template C – Account Verification (Banking)
```html
<p>Dear Customer,</p>
<p>We need to verify your banking account due to recent suspicious activity. Please log in to confirm.</p>
<p><a href="{{ url_for('demo_login', cid=campaign.id, _external=True) }}">Log In to Verify</a></p>
<p><em>Simulation notice: This is an educational demonstration. No real credentials are collected.</em></p>
```

## RealAppTesting Subsystem (Mode B)

In addition to local simulation (Mode A), PhishLab includes the **RealAppTesting** subsystem for authorized cybersecurity awareness exercises across six major platforms:
- WhatsApp
- Instagram
- Facebook Messenger
- Telegram
- X (Twitter)
- LinkedIn

### Key RealAppTesting Features
- **Admin Exercise Creation**: Admin selects a campaign and platform (`/realapp/select/<cid>`).
- **Cryptographic Token Protection**: One-way SHA-256 hashed tokens with configurable TTL (default 4 hours).
- **Consent-Driven Workflow**: Participants access an educational demo via a secure token link (`/realapp/demo/<token>`) and explicitly provide consent before any interaction is tracked.
- **Privacy & Safety**: Pseudonymous participant UUIDs only; zero credential, OTP, session token, or message collection.
- **Admin Dashboard & Analytics**:
  - Exercise History: `/realapp/history`
  - Analytics & Metrics: `/realapp/analytics`
  - CSV Export: `/realapp/export/csv`
  - Audit Logging: `/realapp/audit`
  - Exercise Details: `/realapp/exercise/<id>`
  - Token Revocation: `/realapp/revoke/<id>` (immediately revokes access; returns HTTP 403)
  - Connector Instructions: `/realapp/connector/<id>` (manual step-by-step guidance for exercise administrators)

## Unified Security Testing Architecture

PhishLab integrates four specialized cybersecurity awareness capabilities into one centralized platform:

1. **Local Simulation Engine (Mode A)**: Local SMTP integration via Mailpit with HTML sanitization (Bleach), email preview tracking, simulated credential harvesting avoidance, and Chart.js analytics.
2. **RealAppTesting Subsystem (Mode B)**: Consent-driven security training modules across six major social communication platforms (WhatsApp, Instagram, Facebook Messenger, Telegram, X, LinkedIn) with cryptographically secure token lifecycles and manual platform connectors.
3. **Unified Social Media Generator**: AI-assisted awareness scenario generation across 11 threat categories with cross-platform fidelity adapters and preview simulators.
4. **Real-Time Phishing Security Testing Platform**: Controlled assessment infrastructure with cryptographically secure testing URLs, real-time participant browser interaction collection, Server-Sent Events (SSE) live operations dashboard, device telemetry analysis, controlled file demonstration sandbox, and automated reporting.

## Production Hosting & Deployment (Render)

PhishLab is production-ready for deployment on Render with PostgreSQL, persistent demonstration storage, and optional Redis event clustering:
- **Web Service Entrypoint**: `gunicorn --config gunicorn.conf.py app:app` (threaded worker model with SSE support)
- **Database Engine**: PostgreSQL with SQLAlchemy connection pooling and automatic dialect normalization (`postgresql+psycopg2://`)
- **Automated SQLite-to-PostgreSQL Migration**: `python scripts/migrate_sqlite_to_postgres.py --target "$DATABASE_URL"`
- **Health Monitoring**: Dedicated JSON status endpoints at `/healthz` and `/health`

## Automated Testing

Run the full automated test suite using the project virtual environment:
```bash
.venv\Scripts\python.exe -m pytest -v
.venv\Scripts\python.exe -m compileall -q app.py database.py campaign.py simulator.py real_app_testing security_platform social_simulation tests
.venv\Scripts\python.exe -m pip check
```
Current test suite status: **58 passed in 3.9s**.

## Security Measures
- **Local‑only binding** – Flask runs on `127.0.0.1`.
- **CSRF protection** via `Flask‑WTF`.
- **All form inputs** are validated with WTForms validators.
- **SQLAlchemy** uses parameterised queries – no raw string concatenation.
- **No passwords or OTPs** are ever stored; the demo login only records a boolean event.
- **Environment variables** hold secret configuration (`FLASK_SECRET_KEY`).

## Testing
1. Ensure Mailpit is running.
2. Follow the *Usage Walk‑through* steps.
3. Verify that each interaction creates a row in the `events` table (you can inspect the DB with any SQLite viewer).
4. Check that the dashboard numbers match the recorded events.

## Troubleshooting
| Issue | Likely Cause | Fix |
|-------|--------------|-----|
| No email appears in Mailpit | Mailpit not running or wrong SMTP host/port | Start Mailpit (`mailpit`) and ensure `MAIL_SERVER`/`MAIL_PORT` in `.env` match the defaults (127.0.0.1:1025). |
| CSRF token missing | Form submitted without the hidden tag | Ensure `{{ form.hidden_tag() }}` is present in the template (already included). |
| Database errors | `phishlab.db` missing or corrupted | Delete `database/phishlab.db` and run `flask init-db` again. |
| Dashboard shows zero stats after actions | Events not being recorded | Check the console for errors; ensure `record_event` is called in each route. |

## License
This project is for **educational and research purposes only**. Use responsibly within authorised environments.
