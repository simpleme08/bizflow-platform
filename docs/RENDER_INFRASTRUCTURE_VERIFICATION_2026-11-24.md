# Render Infrastructure Verification — 24 November 2026

**Workspace:** BIzFlow (`tea-dak9srlg1s2s73bibr3g`)  
**Web service:** `hris` (`srv-dakaqtp5efls73dbd38g`)  
**Repository:** `simpleme08/bizflow-platform`  
**Production branch:** `release/production-hardening`  
**Reviewed working branch:** `audit/leave-authorization-hardening-2026-11-24`  
**Production changes made:** None. No deploy, restart, env-var mutation, database query, migration, or cron run was performed.  
**Owner-reported configuration update:** Supabase database and storage configured; Redis and Django secret configured; email host not configured. See verification limits below.

## Verified live service facts

- Service is a Python web service named `hris`, connected to `simpleme08/bizflow-platform` and branch `release/production-hardening`.
- Region: Singapore.
- Plan: Free; one instance.
- Auto-deploy: enabled on commits to the configured branch.
- Actual build command: `pip install -r requirements.txt && python manage.py collectstatic --noinput`.
- Actual start command: `python manage.py migrate --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`.
- Actual health-check path: empty.
- Latest live deploy at inspection: commit `26cb40782f0c63bbfc45e214aabb7cb0872c6d5b`, deploy `dep-dbqggsavcj2c73etrdk0`, status `live`.
- The Render workspace contains no Render-managed PostgreSQL instance.
- The workspace has one Render Key Value resource, `bizflow-hris-redis`, plan `free`, region Singapore, persistence `off`, eviction policy `allkeys_lru`.
- No maintenance cron service was returned in the service inventory.
- Queried recent application logs showed successful login/workspace/payroll page and API requests (HTTP 200/302), plus a missing favicon request (404). No database connectivity can be inferred from these request logs.
- Service metrics and historical event data were not enough to certify availability, capacity, or restore readiness.

## Important interpretation

**Owner-reported configuration (24 November 2026; not independently verified):** The project uses Supabase for its PostgreSQL database and object storage. Redis is configured, the Django secret is configured, and the Supabase storage endpoint and bucket are configured. The email host is not yet configured. These details were supplied by the project owner in conversation; no secret values were requested or accessed, and no live environment values or provider consoles were inspected.

The absence of a Render-managed Postgres resource is consistent with the owner-reported external Supabase database. It does not by itself verify the Supabase project, database connection, SSL enforcement, backups, PITR, or restore readiness. Likewise, configured Supabase endpoint/bucket values do not prove that the bucket is private, encrypted, backed up, or correctly permissioned.

The Render Key Value instance remains a free, non-persistent cache. The inspected Django settings use Redis as the shared Django cache; Django's default session backend remains database-backed unless overridden elsewhere. Cache loss may reset transient throttling state, so Redis must not be used as a durable queue or source of truth. The owner reports Redis is configured, but target identity, TLS/authentication, ACLs, memory pressure, and cache health still require verification.

## Blueprint hardening committed to the audit branch

Updated `render.yaml` in this audit branch only:

1. Blueprint service name changed from `bizflow-hris` to `hris` to match the existing live service and reduce risk of an accidental duplicate service.
2. Kept the existing Free web plan for the current zero-budget demo phase.
3. Kept deployment checks in the build command: `manage.py check --deploy` and `makemigrations --check --dry-run`.
4. Kept `/ready/` as the intended health check; the endpoint exists and tests the database and cache with a 503 when either is unavailable.
5. Changed `BIZFLOW_PROVISION_ACCOUNTS` default from `true` to `false`. Account provisioning must be a deliberate, separately reviewed operation and must never be an automatic deployment side effect.
6. Removed the Starter-plan maintenance cron from the Blueprint. The current budget is zero, so this avoids silently introducing a paid resource. The existing retention command can permanently delete audit events and archived documents, so it must not be scheduled until legal-hold, immutable archive, dry-run review, and retention policy approvals exist.
7. The revised YAML was parsed locally and assertions verified: one web service, correct service name, readiness path, account provisioning disabled by default, and no cron service.

This is a branch-only configuration change. It has **not** been applied to Render and does not alter the live service.

## Deployment configuration drift remains

The live service does not yet match the Blueprint's intended build command or health-check path. The live start command currently runs migrations automatically at service startup. This is a known risk: a future migration may be destructive or incompatible with the currently running application. Before changing the live service, establish a reviewed migration policy and a verified database backup/restore path.

Because auto-deploy is enabled on the production branch, do not merge code/configuration to `release/production-hardening` until the release gates below pass.

## Release gates — still open

### A. Database and recovery
- Supabase is the owner-reported PostgreSQL provider; verify the exact Supabase project/organization and responsible owner.
- Confirm the database is production PostgreSQL, SSL enforced, and not an expiring/free trial resource.
- Verify automated backups, retention, point-in-time recovery if available, and an actual restore into an isolated staging database.
- Record RPO/RTO and a documented rollback procedure.
- Confirm schema migration backups and reviewed migration plan before enabling any deploy that runs migrations.

### B. Redis/cache
- Verify the configured `REDIS_URL` targets the intended Singapore instance and that TLS/authentication and network restrictions are correct.
- Confirm the cache is only used for transient data; do not place durable job queues or authoritative sessions there.
- Confirm eviction and memory limits are compatible with login throttling; allkeys-LRU plus cache loss is not a durable rate-limit ledger.
- Confirm readiness checks work against the configured cache.

### C. Object storage and employee documents
- Supabase Storage endpoint and bucket are owner-reported as configured; verify project/bucket ownership, private access policies (no unintended public access), encryption, least-privilege service credentials, lifecycle/versioning/backups where supported, and a restore test.
- Verify employee document access is tenant- and role-scoped before real employee files are uploaded.
- Verify signed URLs are short-lived and downloads are audited.

### D. Runtime and release
- Reconcile the actual service configuration with the reviewed Blueprint: build checks, readiness path, and startup/migration policy.
- Owner reports the Django secret, Redis, Supabase storage endpoint, and bucket are configured. Verify presence and correctness without exposing values for `DATABASE_URL`, `REDIS_URL`, Supabase storage credentials/endpoint/bucket, `DJANGO_SECRET_KEY`, allowed hosts, CSRF origins, and any enabled payment settings.
- Configure and test the email host and related SMTP credentials/settings. Until then, email-dependent workflows (notifications, password reset, onboarding/offboarding emails) are not release-ready; verify safe failure/retry behavior.
- Confirm `/ready/` returns 200 only when database and cache are usable, and 503 otherwise.
- Add a deployment rollback and incident response runbook.
- Run browser E2E smoke tests against a staging environment before production.

### E. Scheduled jobs and legal retention
- No Render cron was created because the plan is paid and the budget is zero.
- Do not run `apply_retention_policy` automatically: it deletes audit events and archived documents without a confirmed legal-hold mechanism.
- First add legal holds, immutable archive/export, policy approval, and an idempotent job claim/retry model for notification delivery.
- Only then price and approve a scheduled worker/cron. Use dry-run and inspect output before any destructive retention run.

### F. Payroll
- Payroll remains blocked from real use until effective-dated rule sets drive calculations, agency-specific contribution bases are implemented, absence recalculations share the same tax logic, and golden examples are reviewed by a Philippine payroll professional.

## Evidence limitations

- Render service/resource metadata and recent logs were inspected through the connected workspace.
- Environment variable values were not accessed. A safe variable-name-only inventory was not available from the connected Render tool surface.
- The project owner identified Supabase as the database and object-storage provider and reported the relevant settings as configured; this has not been independently validated against Render or Supabase.
- No production database query, migration, backup, restore, file access, email send, cron run, or deploy was attempted.
- This is an infrastructure configuration review, not a penetration test or production certification.
