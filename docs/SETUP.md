# Setup and configuration

## 1. Install prerequisites

Install Python 3.11+ and Git. PostgreSQL 15+ is recommended for any shared or hosted environment. SQLite is supported only for local evaluation.

```powershell
cd C:\Users\pcruz\Documents\HRIS
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python manage.py migrate
python manage.py check
python manage.py runserver
```

Browse to `http://127.0.0.1:8000/`.

If `python` is not recognized, install Python from python.org and select **Add Python to PATH**, then recreate `.venv`. Do not reuse a virtual environment that references a removed Python installation.

## 2. Environment variables

| Variable | Development | Production |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | Unique local secret | New random, private value |
| `DJANGO_DEBUG` | `True` | `False` |
| `DJANGO_ALLOWED_HOSTS` | `127.0.0.1,localhost` | Exact comma-separated hosts |
| `DB_ENGINE` | `sqlite` | `postgresql` |
| `POSTGRES_*` | Not needed with SQLite | Required |
| `POSTGRES_SSLMODE` | `prefer` locally | `require` or stronger hosted |

Never commit `.env`, database passwords, Supabase credentials, or connector secrets.

## 3. PostgreSQL

Create a least-privilege application database/user, then set:

```dotenv
DB_ENGINE=postgresql
POSTGRES_DB=bizflow
POSTGRES_USER=bizflow_app
POSTGRES_PASSWORD=CHANGE_ME
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_SSLMODE=prefer
```

Run `python manage.py migrate` followed by `python manage.py seed_demo` for demonstration data.

## 4. Supabase

Create a project, select **Connect**, then copy the exact connection host, user, port, and password. A persistent Django service should use Direct connection when its host supports IPv6; otherwise use the Supavisor **Session Pooler** connection.

```dotenv
DB_ENGINE=postgresql
POSTGRES_DB=postgres
POSTGRES_USER=postgres.PROJECT_REF
POSTGRES_PASSWORD=YOUR_DATABASE_PASSWORD
POSTGRES_HOST=aws-REGION.pooler.supabase.com
POSTGRES_PORT=5432
POSTGRES_SSLMODE=require
```

Then migrate and seed. Use the values supplied by the Supabase project, not the examples above. Consult the official [Supabase connection guide](https://supabase.com/docs/guides/database/connecting-to-postgres) for current pooler details.

## 5. Demo seed

```powershell
python manage.py migrate
python manage.py seed_demo
```

This command is safe to rerun. It creates a superuser, organization memberships, employees, attendance, payroll, leave balances, onboarding, talent, operations, and connector placeholders.

| Login | Password | Intended walkthrough |
| --- | --- | --- |
| `demo_superuser` | `DemoRole2026!` | Admin Console and all HRIS features |
| `demo_hr` | `DemoRole2026!` | HR workspace and Excel timekeeping import |
| `demo_manager` | `DemoRole2026!` | Shift scheduling and leave approvals |
| `demo_employee` | `DemoRole2026!` | ESS, leave, payroll, and HR Hub |
| `demo.juan` – `demo.sofia` | `DemoEmployee2026!` | Individual employee/time-clock samples |

Change or remove every demo account before real use.

## 6. Deploy to Render

The repository contains `render.yaml`. Push to GitHub, create a Render Blueprint or Web Service, and configure:

```text
Build command: pip install -r requirements.txt && python manage.py collectstatic --noinput
Start command: gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
```

Set `DJANGO_DEBUG=False`, `DJANGO_ALLOWED_HOSTS=YOUR-SERVICE.onrender.com`, a generated `DJANGO_SECRET_KEY`, and the Supabase variables in Render’s secret environment settings. Run migrations and seed data after first deployment.

Free Render web services idle after inactivity and their filesystem is temporary. Use Supabase/PostgreSQL, never `db.sqlite3`, for a hosted deployment. The free `onrender.com` URL is suitable for a demo; a branded domain must be registered separately. See [Render free services](https://render.com/docs/free) and [custom domains](https://render.com/docs/custom-domains).
