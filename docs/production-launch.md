# Production launch runbook

This is the operational gate for using BizFlow with real customer HR/payroll data. Source control can provide the application and deployment configuration; the items requiring live infrastructure or third-party accounts must be completed by the operator.

## 1. Application configuration

Set:

- `DJANGO_DEBUG=False`
- unique long `DJANGO_SECRET_KEY`
- exact production `DJANGO_ALLOWED_HOSTS`
- exact HTTPS `DJANGO_CSRF_TRUSTED_ORIGINS`
- `DB_ENGINE=postgresql`
- `POSTGRES_SSLMODE=require` or stronger supported mode
- PayMongo variables appropriate to test/live mode

Do not store secret values in GitHub files.

## 2. Database

- Provision production PostgreSQL.
- Restrict database access.
- Configure automated backups and retention.
- Perform a real restore test into a separate recovery target.
- Record the recovery procedure and owner.

## 3. Domain and HTTPS

- Configure DNS for the production host.
- Provision valid TLS/HTTPS.
- Set allowed hosts and CSRF origins to the exact production origin.
- Verify redirects/cookies/security headers in production mode.

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

Configure a real transactional email provider if production workflows require email. Store credentials in managed secrets and test delivery, sender identity and failure handling.

## 6. Monitoring

Monitor `/health/` for process availability and `/ready/` for database readiness. Also monitor HTTP errors/latency, database health, payroll failures, billing/webhook failures and backup status.

## 7. First-customer acceptance test

Use a staging or controlled customer account first:

1. Create organization and owner.
2. Configure company structure.
3. Create employees and verify employee limits.
4. Configure assignments, schedules, attendance and leave.
5. Configure payroll inputs.
6. Run payroll preflight/review.
7. Process and approve a test payroll.
8. Generate a payslip and reporting/remittance exports.
9. Verify employee self-service isolation.
10. Start a PayMongo test/live subscription as appropriate.
11. Verify provider webhook synchronization.
12. Verify duplicate/invalid webhooks are handled safely.
13. Verify cross-organization access is denied.
14. Verify `/health/` and `/ready/` from monitoring.
15. Execute a backup and restore test.

## 8. Go-live gate

Do not accept real customer data until all of these are complete:

- [ ] production PostgreSQL
- [ ] domain/DNS/HTTPS
- [ ] secure production Django configuration
- [ ] PayMongo live account/plans/webhook
- [ ] transactional email
- [ ] automated backups and tested restore
- [ ] monitoring and alerting
- [ ] first-customer acceptance test
- [ ] privacy/retention process
- [ ] qualified Philippine payroll/tax/employment review

## 9. Rollback and incident response

If a deployment causes material errors:

1. Stop additional production changes.
2. Preserve logs and audit events.
3. Assess whether application rollback or database recovery is safer.
4. Protect payroll/billing state from duplicate processing.
5. Restore from a known-good backup only after validating the target.
6. Rotate compromised secrets if applicable.
7. Document the incident and customer/regulatory response.
