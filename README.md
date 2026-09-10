# BizFlow HRIS

BizFlow is a Django-based, Philippine-focused HRIS for small and mid-sized organizations. It combines employee records, lifecycle management, scheduling, timekeeping, attendance, leave, payroll, employee self-service, HR operations, talent workflows, reporting, and SaaS billing.

## What is included

- Multi-tenant organizations and organization memberships
- Role-based access control and audit events
- Employee master data, lifecycle history, assignments and documents
- Scheduling, clients/sites, shifts and lifecycle-aware workforce operations
- Employee time clock and HR attendance correction/import workflows
- Atomic Excel `.xlsx` timekeeping import
- Leave balances, requests and approvals
- Payroll periods, salary/wage data, adjustments, loans and final pay
- PDF payslips and statutory/remittance reporting exports
- Employee self-service and HR Hub
- Recruiting, onboarding, performance, benefits and offboarding
- HR Operations: policies, acknowledgements, announcements, approvals, profile changes, compensation, projects/timesheets and connector metadata
- SaaS plans, employee limits and PayMongo recurring billing integration
- Production health/readiness endpoints and Render deployment configuration

## Documentation

Start here:

1. [Product guide](docs/PRODUCT.md)
2. [Setup and configuration](docs/SETUP.md)
3. [Architecture and API map](docs/ARCHITECTURE_AND_API.md)
4. [API reference](docs/API.md)
5. [Roles and access](docs/ROLES_AND_ACCESS.md)
6. [Operating workflows](docs/WORKFLOWS.md)
7. [Payroll and Philippine compliance](docs/PAYROLL_AND_COMPLIANCE.md)
8. [SaaS billing and PayMongo](docs/BILLING.md)
9. [Security model](docs/SECURITY.md)
10. [Testing strategy](docs/TESTING.md)
11. [Operations and release procedure](docs/OPERATIONS.md)
12. [Production launch runbook](docs/production-launch.md)
13. [Master project checklist](docs/master-checklist.md)
14. [Contributing](docs/CONTRIBUTING.md)

## Technology

- Python 3.11+
- Django 5.x
- Django sessions/authentication and CSRF protection
- PostgreSQL for hosted/shared environments; SQLite for local evaluation
- AdminLTE static assets
- ReportLab for PDF payslips
- OpenPyXL for Excel timekeeping import
- WhiteNoise for static files
- Gunicorn for production application serving
- PayMongo for recurring SaaS subscriptions

## Local setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python manage.py migrate
python manage.py check
python manage.py test
python manage.py runserver
```

Open `http://127.0.0.1:8000/`.

SQLite is convenient for evaluation. Use PostgreSQL for any shared, staging or production environment.

## Demo data

For a disposable local/demo database:

```powershell
python manage.py seed_demo
```

The seed is intended for demonstrations and creates representative organizations, users, employees and module data. **Do not run it against a real production HR database.** Change/remove all demo accounts before real use.

## Timekeeping import

HR, Super User, and Django superuser accounts can use the Attendance import. Download the in-app template and preserve this exact header order:

```text
Employee Number | Attendance Date | Time In | Time Out | Status | Remarks
```

Upload `.xlsx` only. Supported statuses are `PRESENT`, `ABSENT`, `LEAVE`, and `HOLIDAY`. Validation occurs before the workbook is committed so an invalid workbook does not partially update attendance.

## Health endpoints

- `GET /health/` — process availability
- `GET /ready/` — database readiness; returns HTTP 503 when the database is unavailable

## Production

Production requires PostgreSQL, HTTPS, a real `DJANGO_SECRET_KEY`, exact allowed hosts/CSRF origins, managed secrets, backups, monitoring, email delivery, PayMongo live configuration, and a tested restore procedure.

The included `render.yaml` runs migrations and static collection during deployment and uses `/ready/` as its health check. A free Render service is suitable for demonstration only; production should use infrastructure appropriate for availability, persistent storage, backups and monitoring.

See [docs/production-launch.md](docs/production-launch.md) for the complete go-live gate.

## Compliance and responsibility

The payroll module provides Philippine payroll/compliance foundations and reporting workflows. It is not a substitute for current government rules, professional payroll/tax advice, legal review, or government filing systems. Verify effective-date and region-specific rules before every production payroll cycle.

## Security

Never commit secrets, credentials, customer data, production database dumps or provider keys. All sensitive features must enforce permissions and tenant scope on the server. See [docs/SECURITY.md](docs/SECURITY.md).
