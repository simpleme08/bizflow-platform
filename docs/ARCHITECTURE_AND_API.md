# Architecture, routes, and data model

## Technology

- Django 5.x server-rendered application with JSON APIs
- AdminLTE static assets for dashboards and modules
- SQLite default for local evaluation; PostgreSQL/Supabase for shared and hosted environments
- Django session authentication and CSRF protection
- ReportLab PDF payslips, OpenPyXL timekeeping workbooks, WhiteNoise static files, Gunicorn hosting

## Application structure

| App | Responsibility |
| --- | --- |
| `core` | UUID base model, audit events, demo commands, landing page |
| `accounts` | Sign-in and role-based workspace routing |
| `organization` | Organization tenant, membership roles, departments, positions, employment types, cost centers |
| `employees` | Employee profile and shift/client assignment |
| `workforce` | Clients, sites, shift templates |
| `attendance` | Clock, attendance calculation, dashboard, manual attendance, Excel import |
| `leave` | Leave types, balances, applications, approval decisions |
| `payroll` | Salary, payroll periods/records, processing, approval, payslip PDF |
| `scheduling` | Shift assignment interface and APIs |
| `onboarding` | Workflows, templates, employee onboarding tasks |
| `talent` | Recruiting, performance, benefits, offboarding |
| `operations` | Documents, acknowledgements, announcements, approvals, profile changes, compensation, projects/timesheets, connectors |
| `ess` | Employee dashboard and self-service summary |
| `reports` | Organization attendance, leave, and payroll summaries |

## Tenant boundary

The active `OrganizationMembership` determines the organization scope. Read/write endpoints filter records by that organization before returning or changing them. Do not create cross-organization foreign keys through Admin or custom scripts.

## Main page routes

| Page | Route | Audience |
| --- | --- | --- |
| Landing page | `/` | Public |
| HR login | `/login/` | Public |
| Public time clock | `/clock/` | Employee credentials required for actions |
| HR dashboard | `/workspace/` | Non-employee roles |
| ESS dashboard | `/ess/` | Employee |
| Employee directory | `/employees/` | Authorized roles |
| Attendance | `/attendance/` | Attendance managers |
| Shift scheduling | `/scheduling/` | Attendance managers |
| Leave | `/leave/` | Employee / leave approvers |
| Payroll | `/payroll/` | Employee history or payroll visibility |
| Reports | `/reports/` | Report viewers |
| Onboarding | `/onboarding/` | Employee managers |
| Talent | `/talent/` | Employee managers/HR |
| HR Operations | `/operations/` | Employee managers/HR |
| Employee HR Hub | `/employee-hub/` | Employee |
| Admin Console | `/admin/` | Django staff users |

## API map

The browser pages call the following internal APIs. These are session-authenticated and role-protected; they are not a public third-party API contract.

| Area | API |
| --- | --- |
| Identity/dashboard | `/api/me/`, `/api/dashboard/` |
| Employees | `/api/employees/` |
| Attendance | `/api/attendance/`, `/api/attendance/import/`, `/api/attendance/template/` |
| Time clock | `/clock/login/`, `/clock/action/` |
| Leave | `/api/leave/`, `/api/leave/me/`, `/api/leave/<id>/decision/` |
| Payroll | `/api/payroll/`, `/api/payroll/me/`, `/api/payroll/process/`, `/api/payroll/<id>/approve/`, `/api/payroll/<id>/payslip/` |
| Scheduling | `/api/scheduling/shifts/`, `clients/`, `employees/`, `employee-schedule/`, `assign/`, `delete/` |
| Onboarding | `/api/onboarding/`, `/api/onboarding/<id>/tasks/<id>/` |
| Talent | `/api/recruiting/`, `/api/performance/`, `/api/benefits/`, `/api/offboarding/` |
| Operations | `/api/operations/`, `/api/operations/employee/`, `/api/operations/approvals/<id>/decision/` |
| Reports/ESS | `/api/reports/`, `/api/ess/` |

## Required administration sequence

For a new organization, create data in this order:

1. Organization.
2. Departments, positions, employment types, cost centers.
3. Shift templates; clients and sites if applicable.
4. Django users and organization memberships.
5. Employee profiles linked to users.
6. Employee assignments, including a primary current assignment.
7. Leave types/balances and employee salary where applicable.
8. Payroll periods, onboarding workflows, talent/operations content.

## Troubleshooting

| Symptom | Likely cause / action |
| --- | --- |
| `python` not found | Install Python 3.11+ with PATH enabled; recreate `.venv` |
| Virtual environment points to missing Python | Delete/recreate only `.venv`, then reinstall requirements |
| `DisallowedHost` | Add exact host to `DJANGO_ALLOWED_HOSTS` and redeploy |
| Static assets missing | Run `python manage.py collectstatic --noinput`; verify WhiteNoise/Gunicorn deployment |
| Database refused | Verify `POSTGRES_*`, SSL mode, network reachability, and Supabase pooler mode |
| No module on dashboard | Confirm active membership and role permission; sign out/in after role changes |
| Time clock rejects clock-in | Employee needs an active assignment for local date |
| Timekeeping import fails | Download template; correct exact headers, employee number, active assignment, dates/times, and statuses |
| Payslip not found | Record must belong to logged-in employee and be `APPROVED` or `PAID` |

## Testing

Run before deployment:

```powershell
python manage.py check
python manage.py test
python manage.py migrate
```

Use a separate staging database for production-like testing. Never run `seed_demo` against a real production HR database.
