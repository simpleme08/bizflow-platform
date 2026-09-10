# Operations, security, backup, and release procedure

## Daily operations

- Review time-clock exceptions and attendance import errors.
- Review leave and approval queues.
- Check payroll exceptions before the next payroll run.
- Check application health/readiness and infrastructure alerts.
- Review audit events for unexpected privileged or sensitive activity.

## Payroll-cycle operations

1. Confirm active employee roster and assignments.
2. Verify salary/wage effective dates.
3. Review attendance, leave, corrections, overtime/undertime and adjustments.
4. Process payroll.
5. Independently review gross, deductions and net pay.
6. Approve records.
7. Mark paid only after payment.
8. Generate payslips and reporting/remittance exports.
9. Archive required outputs according to policy.

## Monthly operations

- Review active memberships and privileged users.
- Review employee lifecycle/separation records.
- Review leave balances and benefit enrollments.
- Test PostgreSQL backup restoration.
- Review PayMongo subscription/invoice/webhook health.
- Review disabled connector metadata and confirm no secrets are stored there.
- Review application dependencies and security advisories.

## Database backup and recovery

For PostgreSQL, a logical backup can be created with:

```powershell
pg_dump -Fc -h HOST -U USER -d bizflow -f bizflow-backup.dump
```

Restore only into a verified recovery target:

```powershell
pg_restore -h HOST -U USER -d bizflow_restored --clean --if-exists bizflow-backup.dump
```

Hosted PostgreSQL providers may provide managed point-in-time recovery/backups; configure retention and test actual restoration rather than relying on a backup-success indicator alone.

## Release procedure

1. Confirm the change has tests and documentation.
2. Back up production PostgreSQL.
3. Validate against a staging database.
4. Install pinned requirements.
5. Run `python manage.py check`.
6. Run `python manage.py migrate --check`.
7. Run `python manage.py test`.
8. Review migration files and tenant/security impact.
9. Deploy application and migrations using the platform procedure.
10. Run `collectstatic` for production.
11. Verify `/health/` and `/ready/`.
12. Smoke-test login, ESS, time clock, leave, attendance import, payroll/payslip and Admin access.
13. Monitor errors and rollback/recover if required.

## Security baseline

- HTTPS only in production.
- `DJANGO_DEBUG=False`.
- Exact `DJANGO_ALLOWED_HOSTS` and CSRF trusted origins.
- Secret values stored outside Git.
- Least-privilege memberships.
- Tenant-scoped queries for every organization-facing operation.
- Server-side authorization on every sensitive endpoint.
- PayMongo webhook signature verification and idempotent event handling.
- Regular backup/restore tests.
- Appropriate privacy/retention controls for employee data.

## Monitoring

At minimum monitor:

- `/health/`
- `/ready/`
- HTTP 5xx rate and latency
- database connectivity/storage/connection saturation
- failed payroll operations
- billing webhook failures/retries and failed payments
- backup success/failure
- application error logs

Alert an operator when readiness fails, backups fail, or billing events repeatedly fail.

## Known operational boundaries

- Government filing/payment and tax/legal advice are not automatically provided by the application.
- Carrier transmission, SSO, background checks, signatures, email/SMS and other provider-dependent capabilities require verified external integrations.
- Connector registry data is metadata and must never be treated as a credential vault.
- A free Render service is demonstration infrastructure, not a production HRIS hosting tier.
- `seed_demo` is for disposable demo/staging data and must not be used on production HR data.
