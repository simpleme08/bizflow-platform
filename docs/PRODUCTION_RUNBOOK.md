# BizFlow HRIS production runbook

This document is the release checklist for the production HR/payroll service. A green CI run is necessary but does not replace these operational controls.

## Zero-budget nationwide pilot architecture

For the initial nationwide pilot, Davao, Manila, and future Philippine customers use one BizFlow application and tenant-isolated data model. Do not create separate city deployments.

Recommended initial topology:

- GitHub: source control and CI/CD.
- Render Free, Singapore region: Django web service.
- Supabase Free: managed PostgreSQL database.
- A managed Redis/Valkey service: shared cache and login-throttling backend.
- S3-compatible private object storage: employee documents, attendance proof, and other private uploads.

Free-tier services are a temporary pilot infrastructure choice. They do not provide the same availability, backup, recovery, or monitoring guarantees as paid production infrastructure. Do not represent the free tier as a high-availability or disaster-recovery environment.

The first paid upgrade should prioritize verified PostgreSQL backups/PITR and restore capability, followed by an always-on application service and production monitoring.

## Required production configuration

- `DJANGO_ENV=production`
- `DJANGO_DEBUG=False`
- `DJANGO_SECRET_KEY` set to a unique secret and stored only in the deployment secret manager
- `DJANGO_ALLOWED_HOSTS` contains only the real application hostnames
- `DJANGO_CSRF_TRUSTED_ORIGINS` contains only the real HTTPS application origins
- `DB_ENGINE=postgresql`
- PostgreSQL credentials configured through deployment secrets
- `POSTGRES_SSLMODE=require` unless the managed database explicitly requires another secure mode
- `REDIS_URL` configured to a shared managed Redis/Valkey service
- `DJANGO_STORAGE=s3` in production
- Private object-storage credentials configured only as deployment secrets
- PayMongo live credentials and webhook secret configured before enabling paid subscriptions

Never commit production secrets, database credentials, webhook secrets, storage credentials, or customer data.

## Database and backup gate

Before onboarding real payroll data:

1. Enable managed PostgreSQL automated backups and point-in-time recovery where the provider supports it.
2. If the free database tier does not provide verified recovery, establish a scheduled encrypted logical database export as an interim pilot safeguard and keep it outside the application container.
3. Set and document the backup retention period required by the business.
4. Perform a restore test into an isolated database at least monthly and after major schema changes.
5. Verify that restored data can pass `python manage.py check --deploy` and application readiness checks.
6. Record the last successful restore date and owner of the recovery procedure.
7. Keep a second recovery copy or provider-supported disaster-recovery mechanism outside the primary database instance.

A backup that has never been restored is not considered verified.

## Deployment gate

1. CI must pass migrations, the complete Django test suite, and `check --deploy`.
2. Deploy application code and migrations using the hosting provider's controlled deployment process.
3. Confirm `/health/` returns HTTP 200.
4. Confirm `/ready/` returns HTTP 200 and reports the database as available.
5. Confirm HTTPS redirect, secure cookies, CSRF protection, and the real application hostname.
6. Confirm production does not expose `/media/` through Django's development static-media handler.
7. Confirm private document and attendance-proof endpoints require authenticated, tenant-scoped access.
8. Confirm PayMongo webhook delivery reaches the production endpoint and duplicate delivery is idempotent.

## Payroll release gate

Before approving a payroll period:

- Payroll confidence/preflight has no unresolved blocking findings.
- The period belongs to the selected organization.
- All payroll records have the expected calculation rule version and provenance hashes.
- The processor cannot approve their own payroll.
- The payment authority is distinct from the processor and approver.
- Approved payroll cannot be recalculated.
- Paid payroll cannot be paid a second time.
- Loan settlement is atomic and cannot create a negative balance.
- Required remittance exports have been reviewed before filing.

## Monitoring and incident response

Monitor at minimum:

- HTTP 5xx rate and latency
- `/ready/` failures
- database connection failures
- authentication failures / repeated login throttling
- PayMongo webhook failures and duplicate events
- payroll processing, approval, and payment audit events

For a suspected security incident:

1. Restrict or disable affected access.
2. Preserve application and audit logs.
3. Identify affected organization(s) and records.
4. Rotate compromised credentials or webhook secrets.
5. Verify database integrity and recent backups.
6. Restore only into an isolated environment until integrity is established.
7. Document the incident, remediation, and customer-notification decision.

## What is not a substitute for this runbook

- A green CI badge does not prove backups work.
- A successful deployment does not prove a restore works.
- A health endpoint does not prove payroll correctness.
- Tenant-scoped ORM queries do not replace endpoint authorization tests.
- PayMongo webhook receipt does not prove the webhook secret is configured correctly.
