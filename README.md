# BizFlow HRIS

BizFlow is a Django HRIS covering employee records, attendance, timekeeping, leave, payroll, scheduling, onboarding, talent, HR operations, employee self-service, and Philippine SaaS billing.

## Documentation

- [Setup, PostgreSQL, Supabase, demo data, and deployment](docs/SETUP.md)
- [Roles and access](docs/ROLES_AND_ACCESS.md)
- [Module workflows](docs/WORKFLOWS.md)
- [Operations, security, backup, and release](docs/OPERATIONS.md)
- [Production launch runbook](docs/production-launch.md)
- [Master project checklist](docs/master-checklist.md)
- [Architecture, route map, data setup order, and troubleshooting](docs/ARCHITECTURE_AND_API.md)

## Modules

- AdminLTE HR and ESS dashboards
- Separate employee time clock at `/clock/`
- Employee directory, schedules, attendance, Excel timekeeping import, and reports
- Leave balances/requests/approvals, payroll records, and printable payslips
- Recruiting, onboarding, performance, benefits, compensation, and offboarding
- HR Operations: announcements, policies/documents, acknowledgements, approvals, profile changes, projects/timesheets, and optional external connectors
- SaaS subscriptions, PayMongo billing checkout, invoices, and verified webhooks

## Production health

- `/health/` — process availability check
- `/ready/` — database readiness check; returns HTTP 503 when the database is unavailable

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
2. A persistent Django server should use a Direct connection when IPv6 is available, or the **Supavisor Session Pooler** on IPv4-only hosting. Use the exact host, username, and port provided in the dashboard.
3. Set the PostgreSQL environment variables from the Supabase dashboard and `POSTGRES_SSLMODE=require`.
4. Run migrations and seed data for a demo environment. Never commit database credentials or expose them in browser code.

## Deployment

The included `render.yaml` runs migrations and static collection during deployment, uses PostgreSQL, and checks `/ready/` for database readiness. Production configuration must set a real `DJANGO_SECRET_KEY`, allowed hosts, and CSRF trusted origins.

For the complete deployment, PayMongo, backup, monitoring, recovery, and first-customer procedure, follow [docs/production-launch.md](docs/production-launch.md).

## Production checklist

- Set `DJANGO_DEBUG=False`, a unique secret key, exact allowed hosts, and CSRF trusted origins.
- Use PostgreSQL and enable automated backups with a tested restore procedure.
- Remove demo users/data before processing real employee data.
- Configure PayMongo live credentials, recurring plans, and the production webhook signing secret.
- Configure email delivery and monitoring/alerts.
- Keep payroll, billing, benefits, messaging, and other provider secrets in host-managed environment variables—not in this repository.
- Complete the first-customer acceptance test before accepting real production data.
- Obtain appropriate legal, privacy, and payroll review before production use.
