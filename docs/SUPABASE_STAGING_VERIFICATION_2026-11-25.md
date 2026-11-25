# Supabase Staging Verification Runbook — 25 Nov 2026

## Safety rules

- Use a dedicated Supabase staging project and a separate Render staging service/environment.
- Do not point staging at the production database or production storage bucket.
- Do not copy real employee records, payroll data, government identifiers, medical/benefit documents, or credentials into staging. Use synthetic fixtures only.
- Do not paste secrets into chat, issues, logs, screenshots, or this runbook.
- Do not change the live Render `hris` service, its environment variables, or the production Supabase project while performing these checks.
- Do not merge PR #42 or deploy until the release gates are reviewed and explicitly approved.

## 1. Staging resource inventory

Create or identify the following isolated resources:

- Supabase staging project with a dedicated PostgreSQL database.
- Supabase Storage bucket dedicated to staging employee and policy files.
- A dedicated least-privilege storage credential for the staging application.
- A separate Render staging web service connected to the audit branch or a controlled staging branch.
- A staging-only Redis endpoint if the application requires shared cache for throttling/readiness.

Record resource names, regions, owners, and dashboard links in the private operations record. Never record credential values.

## 2. Environment-variable presence check

In the Render staging service, verify that the required variable names exist. Inspect only whether each value is present; do not reveal or copy the values into logs.

Application/runtime:
- `DJANGO_ENV` set to the intended staging environment.
- `DJANGO_DEBUG` disabled.
- `DJANGO_SECRET_KEY` present and unique to staging.
- `DATABASE_URL` present and points to the staging Supabase database.
- `REDIS_URL` present and points to staging Redis.
- `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` contain only staging hostnames.
- `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, and `DEFAULT_FROM_EMAIL` configured only if staging email testing is enabled. Use a mail sandbox/test inbox; do not send to real employees.

Storage (names must match the Django settings implementation):
- `DJANGO_STORAGE` set to the S3-compatible backend expected by the project.
- `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` present and staging-only.
- `AWS_STORAGE_BUCKET_NAME` points to the staging bucket.
- `AWS_S3_ENDPOINT_URL` points to the staging Supabase Storage S3 endpoint.
- Confirm any project-specific `BIZFLOW_STORAGE_*` variables are not mistakenly mixed with the Django S3 backend variables. Reconcile the actual settings code before setting duplicate or conflicting names.

Do not assume that a variable being present proves it has the correct target. Verify the target through provider dashboards and a controlled connectivity test.

## 3. Supabase Storage privacy and access

In the staging Supabase dashboard:

1. Confirm the staging bucket is private and public access is disabled.
2. Review Storage policies. The application credential must have only the operations needed by the backend; do not grant broad end-user access.
3. Confirm the application does not expose the service-role or S3 secret to browser JavaScript.
4. Confirm objects are not directly enumerable or downloadable by an unauthenticated user.
5. Review encryption, retention, versioning, and backup/restore capabilities supported by the selected Supabase plan and configuration. Record unsupported features as explicit residual risks rather than assuming they exist.
6. Confirm signed URL lifetime is bounded (the project default is intended to be 300 seconds) and that private download endpoints do not return raw storage credentials or permanent public URLs.

### Controlled file test

Use synthetic documents only, for example a generated PDF containing the text “BIZFLOW STAGING TEST — NO PERSONAL DATA”.

- Upload one allowed file through the Django HR Operations policy upload route.
- Upload one allowed employee-specific document through its intended HR route.
- Download each through the authenticated Django proxy as an authorized user.
- Verify the downloaded bytes match the uploaded bytes.
- Attempt unauthenticated access, access as a different organization, access as an unrelated employee, and access to an unpublished/expired policy document. Each must be denied.
- Inspect API responses and browser network traffic to confirm raw Supabase object URLs, access keys, and service credentials are not disclosed.
- Confirm download audit events are created with the correct organization, actor, and document reference.
- Delete only the synthetic staging objects after evidence has been recorded.

Do not run these tests against the production bucket.

## 4. Supabase database connectivity and safety

- Confirm the staging `DATABASE_URL` points to the staging project and uses TLS/SSL as required by the provider.
- Confirm connection pooling mode and connection limits are compatible with Django/Gunicorn settings.
- Run Django system checks in staging:
  - `python manage.py check`
  - `python manage.py check --deploy`
  - `python manage.py makemigrations --check --dry-run`
- Apply migrations only to the staging database after reviewing the migration plan.
- Verify the app can create/read/update/delete synthetic records in each core module and cannot retrieve records belonging to a second synthetic organization.
- Confirm production database credentials are not present in the staging service.

## 5. Backup and restore drill

Do not mark backups as verified based only on a dashboard badge.

1. Identify the backup schedule, retention window, encryption, and whether point-in-time recovery is available for the actual Supabase plan.
2. Record the recovery point objective (RPO) and recovery time objective (RTO) approved by the business owner.
3. Create a staging-only backup or restore point using the provider-supported process.
4. Restore it into a separate isolated staging target, never over production.
5. Verify schema, migration state, synthetic employee/leave/payroll records, and storage object references.
6. Run Django checks and representative read-only module smoke tests against the restored copy.
7. Record elapsed restore time, data-loss window, validation results, and any missing objects.
8. Keep the restore target isolated and remove it only after approval.

Database backups do not automatically prove that Supabase Storage objects are backed up. Test database and object-storage recovery separately.

## 6. Readiness and runtime checks

Against the staging host only:

- Confirm `/ready/` returns HTTP 200 when database and cache dependencies are healthy.
- In a controlled staging-only test, make a dependency unavailable and confirm readiness fails closed with HTTP 503.
- Confirm normal application routes remain tenant-scoped.
- Confirm login throttling works across multiple requests and fails closed if its shared cache is unavailable in production-like settings.
- Confirm logs do not contain secrets, database URLs, authorization headers, private document URLs, or personal data.

## 7. Evidence and sign-off

Capture the following in the private release evidence record:

- Staging Supabase project and bucket identifiers (not credentials).
- Confirmation of private bucket policy and policy review.
- Variable-name presence checklist (never values).
- Successful authorized upload/download and byte-integrity result.
- Denied unauthenticated, cross-tenant, unrelated-employee, unpublished, and expired-file tests.
- Database TLS/connectivity and migration results.
- Backup schedule/retention evidence and isolated restore result.
- Storage object restore result.
- RPO/RTO achieved.
- Readiness and dependency-failure results.
- Reviewer, timestamp, and any unresolved exceptions.

## Exit criteria

Supabase staging verification is complete only when the private-bucket and authorization tests pass, database and storage recovery have both been exercised, and evidence has been reviewed. A successful staging test is not a substitute for a production backup/restore plan or a production change approval.

## Current status

- Owner has reported Supabase is used for the database and object storage; independent staging verification has not yet been performed.
- Email host remains unconfigured according to the latest owner-provided status.
- No production service, database, storage bucket, environment variable, or deployment was changed while preparing this runbook.
