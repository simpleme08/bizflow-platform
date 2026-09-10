# Architecture, routes, and data model

## System overview

BizFlow is a Django 5.x server-rendered application with JSON endpoints used by its browser UI. The system is organized as Django apps around an organization/tenant boundary. PostgreSQL is the intended shared/hosted database; SQLite is supported for local evaluation.

## Technology

- Python 3.11+
- Django 5.x
- Django authentication/sessions and CSRF protection
- PostgreSQL or Supabase PostgreSQL for hosted environments
- SQLite for local evaluation
- AdminLTE dashboard assets
- ReportLab PDF generation
- OpenPyXL `.xlsx` processing
- WhiteNoise static-file serving
- Gunicorn production server
- PayMongo recurring subscription billing

## Application structure

| App | Responsibility |
| --- | --- |
| `core` | UUID model base, audit events, health/readiness, demo tooling |
| `accounts` | Authentication and role-based workspace routing |
| `organization` | Organization tenants, memberships, roles, structure and subscriptions |
| `employees` | Employee profile, lifecycle, assignments, history and documents |
| `workforce` | Clients, sites and shift templates |
| `attendance` | Clocking, attendance records/calculation, manual corrections and Excel import |
| `leave` | Leave types, balances, applications and decisions |
| `scheduling` | Shift assignment UI/APIs |
| `payroll` | Salary/wage data, periods, records, adjustments, loans, final pay, payslips and exports |
| `ess` | Employee self-service dashboard/data |
| `reports` | Organization attendance, leave and payroll summaries |
| `onboarding` | Onboarding workflows/templates/tasks |
| `talent` | Recruiting, performance, benefits and offboarding |
| `operations` | Policies, announcements, acknowledgements, approvals, profile changes, compensation, projects/timesheets and connector metadata |

## Architectural rules

### Tenant boundary

`OrganizationMembership` establishes the user's organization context. Organization-facing reads/writes must filter by that organization before returning or changing records. Do not use a browser-supplied organization ID as the access-control authority.

### Lifecycle boundary

Operational actions such as scheduling, clocking and leave must respect employee lifecycle/eligibility. Separated or otherwise ineligible employees cannot receive new operational assignments.

### Financial boundary

Payroll approval/payment state and subscription state are controlled server-side. Browser payloads cannot be trusted for payroll totals, plan limits, organization identity or payment status.

### Audit boundary

Sensitive HR, payroll and billing actions should produce audit events where the implemented workflow supports them. Audit records should be retained according to the organization's policy.

## Main page routes

| Page | Route | Audience |
| --- | --- | --- |
| Landing | `/` | Public |
| Login | `/login/` | Public |
| Time clock | `/clock/` | Employees |
| HR workspace | `/workspace/` | Authorized non-employee roles |
| ESS | `/ess/` | Employees |
| Employees | `/employees/` | Authorized HR/management roles |
| Attendance | `/attendance/` | Attendance managers |
| Scheduling | `/scheduling/` | Scheduling managers |
| Leave | `/leave/` | Employees/approvers |
| Payroll | `/payroll/` | Authorized payroll users/employees for own records |
| Reports | `/reports/` | Authorized report viewers |
| Onboarding | `/onboarding/` | Authorized HR/management |
| Talent | `/talent/` | Authorized HR/management |
| HR Operations | `/operations/` | Authorized HR/management |
| Employee Hub | `/employee-hub/` | Employees |
| Admin | `/admin/` | Django staff/superusers |
| Health | `/health/` | Monitoring |
| Readiness | `/ready/` | Monitoring/load balancer |

## API families

See [API.md](API.md) for the maintained endpoint reference. Major families are:

- identity/dashboard: `/api/me/`, `/api/dashboard/`
- organization billing/subscription: `/api/subscription/`, `/api/billing/`
- employees: `/api/employees/`
- attendance: `/api/attendance/`
- leave: `/api/leave/`
- payroll: `/api/payroll/`
- scheduling: `/api/scheduling/`
- onboarding: `/api/onboarding/`
- talent: `/api/recruiting/`, `/api/performance/`, `/api/benefits/`, `/api/offboarding/`
- operations: `/api/operations/`
- ESS/reports: `/api/ess/`, `/api/reports/`

These are internal APIs, not a versioned public API contract.

## New organization setup order

1. Organization.
2. Departments, positions, employment types and cost centers.
3. Shift templates and clients/sites when applicable.
4. Django users and organization memberships.
5. Employee profiles linked to users.
6. Employee assignments and primary current assignment.
7. Leave types/balances and salary/wage data.
8. Payroll periods and operational/talent/onboarding content.
9. Subscription/PayMongo configuration when paid billing is enabled.

## Data ownership principles

- Employee profile is the authoritative HR identity record.
- Employee assignment provides operational context such as department/position/shift/client/site and effective dates.
- Attendance records represent actual timekeeping outcomes and corrections.
- Leave balances and requests represent leave entitlement/use and approval state.
- Payroll records represent calculated payroll for a period and its approval/payment state.
- Organization subscription data represents local SaaS billing state synchronized with PayMongo.
- Audit events provide traceability for supported sensitive actions.

## Troubleshooting

| Symptom | Action |
| --- | --- |
| `DisallowedHost` | Add the exact hostname to `DJANGO_ALLOWED_HOSTS`. |
| CSRF failure | Add the exact HTTPS origin to `DJANGO_CSRF_TRUSTED_ORIGINS`. |
| Static files missing | Run `collectstatic`; verify WhiteNoise/Gunicorn configuration. |
| Database connection failure | Verify `POSTGRES_*`, SSL mode, network and Supabase connection type. |
| Dashboard feature missing | Check active organization membership and role permissions. |
| Time clock rejects action | Verify employee lifecycle and active assignment for the date. |
| Import rejected | Download the current template and correct all validation errors; imports are atomic. |
| Payslip unavailable | Verify employee ownership and payroll record status. |
| Billing not updating | Check PayMongo credentials/webhook signature configuration and webhook delivery logs. |

## Validation commands

```powershell
python manage.py check
python manage.py migrate --check
python manage.py test
python manage.py migrate
```

Use a separate staging database for production-like validation. Never seed demonstration data into production.
