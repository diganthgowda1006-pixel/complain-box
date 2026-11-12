# Digital Suggestion Box for Local Governance

A mobile-first Flask app for citizens to submit suggestions or complaints and track their status. Local office staff can review reports, update progress, and view a dashboard. The interface supports English and Kannada.

## Features

- Suggestion form with category, description, ward/location, optional photo, and anonymous mode
- Unique tracking ID with a public status and remarks history
- Staff login, search/filter, and status updates
- Dashboard with status/category counts, a seven-day trend, and average resolution time
- English/Kannada interface switch
- Local keyword-based category suggestions and urgent-word flags
- Staff-only similar-report hints and a count-based weekly summary
- CSRF protection, password hashing, safe image decoding, upload limits, and spam throttling

The local assistant uses understandable keyword rules, not a trained AI model. It does not send report text outside the app. Staff should confirm its category and urgency suggestions; text matches are not proof that reports are duplicates.

## Requirements

- Python 3.10 or newer
- A terminal and a web browser

## Laptop-only demo setup

Run commands from this project folder.

### 1. Create and activate a virtual environment

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```bash
python -m pip install -r requirements.txt
```

This installs Flask, SQLAlchemy, form protection, Pillow image handling, request limits, and Waitress, the local WSGI server.

### 3. Set a private session key

Copy the example environment file and generate a random key:

```bash
cp .env.example .env
python -c "import secrets; print(secrets.token_hex(32))"
```

Open `.env` in VS Code and replace the example `SECRET_KEY` with the generated value. Keep `.env` private; it is ignored by Git. Leave `APP_ENV=development` for the HTTP-only loopback demo. Do not bind this setup to a public network.

### 4. Initialize or migrate the database

```bash
flask --app run.py init-db
```

This creates missing tables and adds the optional category/priority fields to an existing SQLite database without deleting its records.

### 5. Create the first staff account

```bash
flask --app run.py create-staff --role admin
```

Enter a username and a password of at least 12 characters when prompted. The password is hidden while typing and stored as a hash.

To change an existing staff password, run:

```bash
flask --app run.py change-staff-password --username diganth
```

Replace `diganth` with the account name. Enter a new password of at least 12 characters twice when prompted; it will not appear on screen or in shell history.

### 6. Start the local server

macOS/Linux:

```bash
waitress-serve --host=127.0.0.1 --port=5000 run:app
```

Windows PowerShell:

```powershell
.venv\Scripts\waitress-serve.exe --listen=127.0.0.1:5000 run:app
```

Open <http://127.0.0.1:5000/>. Staff sign in at <http://127.0.0.1:5000/admin/login>; the dashboard is at <http://127.0.0.1:5000/admin/dashboard>. Stop the server with Ctrl+C.

Binding to `127.0.0.1` makes the demo available only on the laptop. For citizens to access it from their own phones, deploy behind HTTPS with a persistent database and file storage; do not simply change the bind address to `0.0.0.0`.

## Data location and backups

- SQLite database: `instance/suggestion_box.db`
- Uploaded photos: `uploads/`
- Environment secrets: `.env`

To make a basic backup, stop the server first, then copy `instance/suggestion_box.db` and the `uploads/` folder to a separate, access-controlled location. To restore, stop the server and put both back in their original locations. Never include `.env` in a public repository or share it in screenshots.

## Tests

```bash
python -m unittest discover -s tests
```

The tests use temporary/in-memory databases and do not alter your local suggestion data.

## Database overview

- `submissions`: citizen report, chosen category, local suggested category/priority, anonymous flag, tracking code, current status, and timestamps.
- `staff_users`: staff usernames, password hashes, and roles.
- `status_updates`: status and remarks history, with visibility and staff attribution.

The core app does not collect citizen accounts or contact details. Anyone with a tracking ID can view that suggestion’s public status and remarks, so citizens should keep IDs private. Staff-only remarks do not appear on the public tracking page.

## Security and deployment limits

- CSRF is enabled for form posts; staff passwords are hashed.
- Photos are checked as real images, capped at 5 MB per request and 20 megapixels, re-encoded, and saved under generated names.
- Submissions and staff login are limited to five POST attempts per minute per IP. The default limiter is in-memory and suitable for a single local process.
- Production mode requires a secret key and sets secure session cookies, so production must use HTTPS. The laptop demo uses HTTP on loopback only.
- The project is configured for a local SQLite database. If hosting on a platform with an ephemeral filesystem, reports/photos can disappear after restarts; use persistent storage and backups before public use.
# suggestion-box
