# Production launch runbook

This is the final operational checklist for running the HRIS with real customer data.

## 1. Application

- Set `DJANGO_DEBUG=False`.
- Set a unique, long random `DJANGO_SECRET_KEY` in the deployment secret store.
- Set `DJANGO_ALLOWED_HOSTS` to the production hostname(s).
- Set `DJANGO_CSRF_TRUSTED_ORIGINS` to the HTTPS origin(s), for example `https://hris.example.com`.
- Use PostgreSQL with `DB_ENGINE=postgresql` and `POSTGRES_SSLMODE=require`.
- Run migrations and `collectstatic` during deployment.
- Configure the platform health check to `/health/` and readiness check to `/ready/`.

## 2. PayMongo

Configure production credentials in the deployment secret store:

- `PAYMONGO_SECRET_KEY`
- `PAYMONGO_PUBLIC_KEY`
- `PAYMONGO_WEBHOOK_SECRET`
- `PAYMONGO_LIVEMODE=True`
- `PAYMONGO_PLAN_STARTER`
- `PAYMONGO_PLAN_GROWTH`
- `PAYMONGO_PLAN_BUSINESS`

Create/verify the corresponding recurring-billing plans in the PayMongo account before enabling paid checkout. Register the production webhook endpoint:

`https://<production-host>/api/billing/webhook/paymongo/`

Use the webhook signing secret supplied by PayMongo. Never put provider secrets in source control. Perform a test subscription and verify that duplicate webhook delivery is harmless before accepting customers.

## 3. Database and recovery

- Enable automated PostgreSQL backups with a documented retention period.
- Test a restore before accepting production customer data.
- Restrict database access to the application and approved operators.
- Keep migrations in source control and deploy them before application code that depends on them.

## 4. Monitoring

Monitor:

- `/health/` for process availability.
- `/ready/` for database readiness.
- HTTP 5xx rate and latency.
- Failed payroll processing and approval operations.
- Billing webhook failures and repeated provider events.
- Database storage and connection saturation.
- Backup success/failure.

Alert an operator when readiness fails, backups fail, or billing webhooks repeatedly fail.

## 5. Security baseline

- HTTPS only in production.
- Production secret values stored outside Git.
- Least-privilege organization roles.
- Server-authoritative plan/subscription state.
- Tenant-scoped employee, workforce, payroll, and billing queries.
- Do not expose whether resources exist in another organization.
- Review audit events for billing and sensitive HR/payroll actions.
- Establish a customer data-retention/deletion policy before onboarding production customers.

## 6. First-customer acceptance test

1. Create an organization and owner account.
2. Configure company information, departments, positions, employment types, and payroll settings.
3. Import/create employees and verify employee-limit enforcement.
4. Configure schedules, attendance, and leave rules.
5. Configure salary/payroll profiles and applicable PH compliance references.
6. Run payroll preflight.
7. Process, review, approve, and mark a test payroll paid.
8. Generate a payslip and remittance/reporting exports.
9. Start a test paid subscription and verify the organization subscription state.
10. Deliver duplicate and invalid billing webhook payloads and verify they are rejected/idempotent.
11. Verify an authorized user can view billing history while another organization cannot.
12. Verify `/health/` and `/ready/` are monitored.
13. Verify backup restore procedure.

## 7. Go-live gate

Do not accept real customer data until the production database, domain/DNS, PayMongo live account, email delivery, backups, monitoring, and restore procedure are configured and the first-customer acceptance test passes.
