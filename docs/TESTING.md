# Testing strategy

## Test layers

### Django checks

`python manage.py check` catches configuration and model/system-check problems.

### Unit and integration tests

`python manage.py test` is the primary regression suite. It covers organization boundaries, roles, employee lifecycle, workforce operations, leave, attendance, payroll, billing and other application workflows.

### Migration validation

Run:

```powershell
python manage.py migrate --check
python manage.py migrate
```

CI should run migrations against a clean database before the test suite.

## Required security regression coverage

Every access-controlled feature should include tests for:

- authenticated vs unauthenticated access
- authorized vs unauthorized role
- active vs inactive membership
- same-organization access
- cross-organization access
- invalid identifiers and missing records

For stateful workflows also test duplicate submission, invalid transitions and rollback behavior.

## Payroll tests

Payroll changes should test calculations, period boundaries, employee eligibility, approval/payment state, adjustments, loans, final pay, payslip authorization and reporting outputs. Compliance-sensitive values should be tied to effective dates and verified against current authoritative sources before release.

## Billing tests

Billing changes should test plan mapping, employee limits, checkout behavior, plan changes, cancellation, invoices, provider failures, invalid webhook signatures, duplicate webhook delivery and tenant isolation.

## File-import tests

Attendance import tests should cover exact headers, unsupported extensions, malformed rows, invalid employees, inactive assignments, invalid dates/times, oversized workbooks, duplicate rows and atomic rollback.

## Release gate

A release is not considered validated until CI is green and the migration/test steps complete successfully. Production acceptance additionally requires the operational checks in `docs/production-launch.md`.
