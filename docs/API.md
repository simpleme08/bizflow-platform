# API reference

## Contract

The `/api/` endpoints are internal application APIs used by the Django-rendered UI. They are session-authenticated and permission-protected; they are not currently a versioned public third-party API.

All organization-scoped operations must resolve the authenticated user's active `OrganizationMembership` and filter by that organization before reading or mutating data.

## Identity and dashboards

| Endpoint | Purpose |
| --- | --- |
| `GET /api/me/` | Current authenticated user/context |
| `GET /api/dashboard/` | Role-appropriate dashboard data |
| `GET /api/subscription/` | Organization subscription, plan and active-employee usage |

## Employees

| Endpoint | Purpose |
| --- | --- |
| `GET /api/employees/` | Organization employee directory/data |
| `GET /api/employees/<employee_id>/` | Employee profile |
| `GET/POST /api/employees/<employee_id>/lifecycle/` | Lifecycle actions/history |

Cross-organization employee identifiers must not disclose whether a resource exists. Unauthorized cross-tenant access should behave as not found where implemented for that resource.

## Attendance and time clock

| Endpoint | Purpose |
| --- | --- |
| Attendance APIs | List/create/update organization attendance |
| `POST /api/attendance/import/` | Atomic `.xlsx` timekeeping import |
| `GET /api/attendance/template/` | Download import template |
| `POST /clock/login/` | Employee time-clock authentication |
| `POST /clock/action/` | Employee clock in/out action |

Time-clock actions require an eligible employee with an active assignment for the relevant date.

### Excel import headers

```text
Employee Number | Attendance Date | Time In | Time Out | Status | Remarks
```

Supported statuses: `PRESENT`, `ABSENT`, `LEAVE`, `HOLIDAY`.

## Leave

| Endpoint | Purpose |
| --- | --- |
| `GET/POST /api/leave/` | Organization leave workflow |
| `GET /api/leave/me/` | Employee's own leave history/balances |
| `POST /api/leave/<id>/decision/` | Authorized approval/rejection |

Lifecycle eligibility and leave balances are checked server-side.

## Payroll

| Endpoint | Purpose |
| --- | --- |
| `GET /api/payroll/` | Authorized payroll records |
| `GET /api/payroll/me/` | Employee's own payroll history |
| `POST /api/payroll/process/` | Process an organization payroll period |
| `POST /api/payroll/<id>/approve/` | Approve a payroll record |
| `GET /api/payroll/<id>/payslip/` | Generate/view authorized PDF payslip |
| `GET /api/payroll/remittance/<period_id>/<kind>/` | Reporting/remittance export |

Approved/paid payroll records are treated as controlled financial records; employee self-service must not expose another employee's records.

## Scheduling

The scheduling API covers shift templates, clients, employee schedules, assignment creation/deletion, and employee schedule views. Assignment creation is lifecycle-aware and organization-scoped.

## Onboarding, talent and operations

| Area | API prefix |
| --- | --- |
| Onboarding | `/api/onboarding/` |
| Recruiting | `/api/recruiting/` |
| Performance | `/api/performance/` |
| Benefits | `/api/benefits/` |
| Offboarding | `/api/offboarding/` |
| Operations | `/api/operations/` |
| ESS | `/api/ess/` |
| Reports | `/api/reports/` |

Consult the application views and tests for exact request/response fields; these endpoints are not yet a separately versioned external SDK contract.

## Billing

| Endpoint | Purpose |
| --- | --- |
| `POST /api/billing/checkout/` | Start PayMongo subscription checkout flow |
| `POST /api/billing/change-plan/` | Request/change organization plan |
| `POST /api/billing/cancel/` | Cancel subscription |
| `GET /api/billing/invoices/` | Organization billing invoices |
| `POST /api/billing/webhook/paymongo/` | PayMongo webhook receiver |

Billing webhooks are provider-to-server calls and must be signature-verified before business processing. Duplicate delivery must be idempotent.

## Health and readiness

- `GET /health/` returns process availability.
- `GET /ready/` checks database connectivity and returns HTTP 503 when the database is unavailable.

## Error handling and security expectations

Clients should treat non-2xx responses as authoritative failures and must not infer authorization from UI visibility. Do not put provider secrets in requests originating from browser code. Do not trust plan, employee count, approval state, payroll totals, or organization identifiers supplied only by the client.
