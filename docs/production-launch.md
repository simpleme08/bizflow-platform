# Production launch runbook

This is the operational gate for using BizFlow with real customer HR/payroll data. Source control can provide the application and deployment configuration; the items requiring live infrastructure or third-party accounts must be completed by the operator.

## 1. Application configuration

Set:

- `DJANGO_ENV=production`
- `DJANGO_DEBUG=False`
- unique long `DJANGO_SECRET_KEY`
- exact production `DJANGO_ALLOWED_HOSTS`
- exact HTTPS `DJANGO_CSRF_TRUSTED_ORIGINS`
- `DB_ENGINE=postgresql` or a valid PostgreSQL `DATABASE_URL`
- `POSTGRES_SSLMODE=require` or stronger supported mode
- `REDIS_URL` for the shared production cache/login throttle
- `DJANGO_STORAGE=s3` and the private object-storage settings
- PayMongo variables appropriate to test/live mode

Do not store secret values in GitHub files.

### Production role accounts

The Render blueprint supports idempotent provisioning of the explicitly configured HR, SME and SUPER_USER application accounts. Account passwords are supplied only through Render environment variables. Passwords are not reset on subsequent deploys unless `BIZFLOW_PROVISION_RESET_PASSWORDS=true` is deliberately enabled.

The application-level `SUPER_USER` role is distinct from Django's `is_superuser`; use Django's admin account separately when `/admin/` access is required.

## 2. Database

- Provision production PostgreSQL.
- Restrict database access.
- Configure automated backups and retention.
- Perform a real restore test into a separate recovery target.
- Record the recovery procedure and owner.
- Verify migrations are fully applied after every release.
- Do not run demo seed commands against the production database.

## 3. Domain and HTTPS

- Configure DNS for the production host.
- Provision valid TLS/HTTPS.
- Set allowed hosts and CSRF origins to the exact production origin.
- Verify HTTP redirects to HTTPS.
- Verify secure session/CSRF cookies and security response headers.

## 4. PayMongo

Configure:

```dotenv
PAYMONGO_SECRET_KEY=
PAYMONGO_PUBLIC_KEY=
PAYMONGO_WEBHOOK_SECRET=
PAYMONGO_LIVEMODE=True
PAYMONGO_PLAN_STARTER=
PAYMONGO_PLAN_GROWTH=
PAYMONGO_PLAN_BUSINESS=
```

Create/verify matching recurring plans in PayMongo. Register:

`https://<production-host>/api/billing/webhook/paymongo/`

Use the production webhook signing secret supplied by PayMongo. Test checkout, activation, plan change, cancellation, invoice synchronization, failed payment handling, invalid signature rejection and duplicate delivery.

## 5. Email and communications

Configure a real transactional email provider if production workflows require email. Store credentials in managed secrets and test delivery, sender identity, bounce/failure handling and links generated from the production origin.

## 6. Monitoring and readiness

Monitor `/health/` for process availability and `/ready/` for **both database and shared-cache readiness**. A failed dependency should produce HTTP 503 from `/ready/` rather than allowing the service to appear healthy while a required dependency is unavailable.

Also monitor HTTP errors/latency, database health, payroll failures, billing/webhook failures and backup status. Alert on sustained readiness failures and repeated application errors.

## 7. First-customer acceptance test

Use a staging or controlled customer account first:

1. Create organization and owner.
2. Configure company structure.
3. Create employees and verify employee limits.
4. Configure assignments, schedules, attendance and leave.
5. Configure payroll inputs.
6. Run payroll preflight/review and resolve any confidence-gate warnings/errors.
7. Process and approve a test payroll.
8. Generate a payslip and reporting/remittance exports.
9. Verify employee self-service isolation.
10. Start a PayMongo test/live subscription as appropriate.
11. Verify provider webhook synchronization.
12. Verify duplicate/invalid webhooks are handled safely.
13. Verify cross-organization access is denied.
14. Verify `/health/` and `/ready/` from monitoring.
15. Execute a backup and restore test.
16. Verify mobile/tablet navigation and the principal employee/HR workflows on a real device.

## 8. Go-live gate

Do not accept real customer data until all of these are complete:

- [ ] production PostgreSQL
- [ ] domain/DNS/HTTPS
- [ ] secure production Django configuration
- [ ] shared production Redis/cache
- [ ] private object storage
- [ ] PayMongo live account/plans/webhook
- [ ] transactional email
- [ ] automated backups and tested restore
- [ ] monitoring and alerting
- [ ] first-customer acceptance test
- [ ] privacy/retention process
- [ ] qualified Philippine payroll/tax/employment review

## 9. Release procedure

1. Merge only reviewed changes into the production branch.
2. Require CI to pass migration consistency, migrations, application tests and production deployment checks.
3. Let Render auto-deploy the production branch.
4. Confirm the deployment is live and `/ready/` is healthy.
5. Confirm migrations completed successfully.
6. Confirm the production role accounts exist without exposing their passwords in logs.
7. Exercise login and one representative workflow.
8. Monitor application errors after release.

Do not bypass the migration consistency check with an ad-hoc database change. If a production database has a partially applied migration, create an idempotent migration repair with an explicit state/database strategy and test it against the CI PostgreSQL version before release.

## 10. Rollback and incident response

If a deployment causes material errors:

1. Stop additional production changes.
2. Preserve logs and audit events.
3. Assess whether application rollback or database recovery is safer.
4. Protect payroll/billing state from duplicate processing.
5. Restore from a known-good backup only after validating the target.
6. Rotate compromised secrets if applicable.
7. Document the incident and customer/regulatory response.
