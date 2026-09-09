# BizFlow HRIS

BizFlow is a Django HRIS covering employee records, attendance, timekeeping, leave, payroll, scheduling, onboarding, talent, HR operations, and employee self-service.

## Documentation

- [Setup, PostgreSQL, Supabase, demo data, and deployment](docs/SETUP.md)
- [Roles and access](docs/ROLES_AND_ACCESS.md)
- [Module workflows](docs/WORKFLOWS.md)
- [Operations, security, backup, and release](docs/OPERATIONS.md)
- [Architecture, route map, data setup order, and troubleshooting](docs/ARCHITECTURE_AND_API.md)

## Modules

- AdminLTE HR and ESS dashboards
- Separate employee time clock at `/clock/`
- Employee directory, schedules, attendance, Excel timekeeping import, and reports
- Leave balances/requests/approvals, payroll records, and printable payslips
- Recruiting, onboarding, performance, benefits, compensation, and offboarding
- HR Operations: announcements, policies/documents, acknowledgements, approvals, profile changes, projects/timesheets, and optional external connectors

## Local setup

Install Python 3.11+ and PostgreSQL for production (SQLite is fine for local evaluation):

```powershell
cd C:\Users\pcruz\Documents\HRIS
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python manage.py migrate
python manage.py runserver
```

Open `http://127.0.0.1:8000/`.

## Full demo data

After migrations, run the idempotent seed command:

```powershell
python manage.py seed_demo
```

It creates employees, departments, shifts, attendance, leave balances, payroll, role accounts, onboarding, talent records, benefits, offboarding, policies, announcements, approvals, timesheets, and disabled connector placeholders.

| Account | Password | Use |
| --- | --- | --- |
| `demo_superuser` | `DemoRole2026!` | Django/HRIS Super User |
| `demo_hr` | `DemoRole2026!` | HR workspace and Excel import |
| `demo_manager` | `DemoRole2026!` | Manager workspace |
| `demo_employee` | `DemoRole2026!` | Employee Self-Service |
| `demo.juan` to `demo.sofia` | `DemoEmployee2026!` | Employee and time-clock demos |

These accounts are demonstration-only; change/remove them before real deployment.

## Excel timekeeping import

HR, Super User, and Django superuser accounts can import timekeeping from the Attendance page. Download the template there and use these headers in exact order:

```text
Employee Number | Attendance Date | Time In | Time Out | Status | Remarks
```

Upload `.xlsx` only. Supported statuses are `PRESENT`, `ABSENT`, `LEAVE`, and `HOLIDAY`. Every row is validated before a single transaction saves the workbook, so invalid files do not partially change attendance.

## PostgreSQL

Set the following in `.env` for a local PostgreSQL server:

```dotenv
DB_ENGINE=postgresql
POSTGRES_DB=bizflow
POSTGRES_USER=bizflow_app
POSTGRES_PASSWORD=use-a-long-unique-password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_SSLMODE=prefer
```

Then run `python manage.py migrate` and `python manage.py seed_demo`.

## Supabase PostgreSQL

1. Create a Supabase project, select **Connect**, and copy its connection details.
2. A persistent Django server should use a Direct connection when IPv6 is available, or the **Supavisor Session Pooler** on IPv4-only hosting. Use the exact host, username, and port provided in the dashboard. [Supabase connection guide](https://supabase.com/docs/guides/database/connecting-to-postgres)
3. Set:

```dotenv
DB_ENGINE=postgresql
POSTGRES_DB=postgres
POSTGRES_USER=postgres.PROJECT_REF
POSTGRES_PASSWORD=YOUR_SUPABASE_DATABASE_PASSWORD
POSTGRES_HOST=aws-REGION.pooler.supabase.com
POSTGRES_PORT=5432
POSTGRES_SSLMODE=require
```

4. Run migrations and seed data. Never commit database credentials or expose them in browser code or connector records.

## Free deployment with Render + Supabase

The included `render.yaml` configures a Django web service. Push this repository to GitHub, create a Render Blueprint/Web Service, and set:

```text
Build: pip install -r requirements.txt && python manage.py collectstatic --noinput
Start: gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
```

Add `DJANGO_DEBUG=False`, a generated `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS=YOUR-SERVICE.onrender.com`, and the Supabase PostgreSQL variables above in Render’s environment settings. After deployment run:

```text
python manage.py migrate && python manage.py seed_demo
```

Render provides a free `*.onrender.com` URL. Free web services sleep after idle time and have an ephemeral filesystem, so use Supabase/PostgreSQL—not SQLite—for data. [Render free-tier details](https://render.com/docs/free)

For a branded domain, buy/register one, add it in Render Custom Domains, configure the requested DNS record, and add it to `DJANGO_ALLOWED_HOSTS`. Render provisions HTTPS automatically. [Render custom-domain guide](https://render.com/docs/custom-domains)

## Production checklist

- Set `DJANGO_DEBUG=False`, an unguessable secret key, exact allowed hosts, and strong administrator passwords.
- Run migrations before deployment and back up PostgreSQL.
- Remove demo users/data before processing real employee data.
- Keep payroll, benefits, e-signature, messaging, and other provider secrets in host-managed environment variables—not in this repository.
- Obtain appropriate legal, privacy, and payroll review before production use.
