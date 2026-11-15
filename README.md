# South Asian University - Library Management System (LMS)

Software Engineering Prototyping Project — CSE231  

---

## Project Structure

| Path | Description |
|------|-------------|
| `app.py` | Main Flask application — all routes, RBAC, DB logic |
| `db.sql` | Full database schema + seed data (run to recreate DB from scratch) |
| `templates/` | Jinja2 HTML templates for all views |
| `static/css/` | Stylesheets (`admin.css`, `styles.css`) |
| `CHANGELOG.md` | Dated history of each evolutionary prototype |
| `requirements.txt` | Python package dependencies |
| `.gitignore` | Excludes `env/`, `__pycache__/`, `.env` |

---

## Setup Instructions (Local / Second Laptop)

### 1. Clone the repository

```bash
git clone <repo-url>
cd "DBMS Application"
```

### 2. Create and activate a virtual environment

```bash
python -m venv env

# Windows (PowerShell):
.\env\Scripts\Activate.ps1

# Windows (cmd):
.\env\Scripts\activate.bat

# Linux / macOS:
source env/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up the MySQL database

- Install and start **MySQL Server** (tested on MySQL 8.x).
- Run `db.sql` to create the database, tables, and seed data:

```bash
mysql -u root -p < db.sql
```

> **Note:** The default DB config in `app.py` uses `host=localhost`, `user=root`, `password=root`.  
> If your local MySQL password is different, update `DB_CONFIG` in `app.py` before running.

### 5. Run the application

```bash
python app.py
```

Open your browser at: `http://127.0.0.1:5000`

---

## Default Test Accounts

| Username | Role    | Password |
|----------|---------|----------|
| `admin`  | Admin   | `pass123` |
| `priyad` | Faculty | `pass123` |
| `aaravs` | Student | `pass123` |
| `bhavnar`| Student | `pass123` |
| `chiragd`| Student | `pass123` |

> All passwords are stored as **bcrypt hashes** in the database. Plain-text passwords are never stored.

---

## Role-Based Access

| Role    | Accessible URLs |
|---------|----------------|
| Admin   | `/admin`, `/admin/*` |
| Student | `/portal`, `/portal/request` |
| Faculty | `/portal`, `/portal/request` |

Attempting to access another role's URL returns a **403 Forbidden** page.  
Attempting to access a non-existent URL returns a **404 Not Found** page.

---

## Member Portal Tabs

Logged-in Students and Faculty access `/portal` with three tabs:

| Tab | Feature | Requirement |
|-----|---------|-------------|
| Catalogue Search | Search books by title, author, subject, ISBN | FR-11 |
| My Loans & Fines | View active/returned loans, overdue fines | FR-17 |
| My Requests | Submit book requests, view admin decisions | FR-18, FR-19 |

---

## Library Policy Settings

An admin can configure dynamic operational parameters at `/admin/policy`:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `LOAN_PERIOD_DAYS` | 14 | Days before a loan is due |
| `FINE_RATE_PER_DAY` | 10.00 | Fine in Rupees per overdue day |
| `DEAD_STOCK_YEARS` | 1 | Min age (years) for Dead Stock report |
| `DEAD_STOCK_USAGE_LIMIT` | 2 | Max borrow count to flag as Dead Stock |

Changes take effect immediately for all subsequent loans and returns.

---

## Prototype Evolution Summary

| Prototype | Date | Key Additions |
|-----------|------|---------------|
| Prototype 0 | 2026-10-29 | Initial schema, auth, all admin CRUD views |
| Prototype 1 | 2026-11-05 | bcrypt security, RBAC, member portal, book requests with Decision_Note, atomic transactions |
| Prototype 2 | 2026-11-12 | Catalogue search, My Loans/Fines tab, dynamic POLICY engine, usage pattern and faculty reports |
| Prototype 3 | 2026-11-15 | Admin home dashboard with live stats, 404 page, mobile responsiveness (NFR-07), README completion |

---

## Troubleshooting

### MySQL connection refused
- Ensure MySQL service is running: `net start MySQL80` (Windows) or `sudo service mysql start` (Linux).
- Verify that the credentials in `DB_CONFIG` inside `app.py` match your local MySQL user/password.

### `ModuleNotFoundError` after cloning on a new laptop
- Make sure you activated the virtual environment before running `pip install -r requirements.txt`.
- Re-run: `pip install -r requirements.txt` inside the activated `env`.

### `ValueError: Invalid salt` on login
- This means a password in the DB was not properly hashed. Re-run `db.sql` to restore the correct bcrypt-hashed seed data.

### Port 5000 already in use
- Kill the existing process: `netstat -aon | findstr :5000`, then `taskkill /PID <pid> /F`.
- Or change the port: `app.run(debug=True, port=5001)` in `app.py`.

### Template syntax errors
- Run: `python -m py_compile app.py` to check Python syntax.
- For Jinja2 template errors, check `templates/` for unclosed `{% block %}` or `{% if %}` tags.
