# Security production gate

BizFlow HRIS handles employee identity, compensation, attendance, leave, payroll, and statutory records. Security is therefore a release gate, not a post-launch enhancement.

## Current controls

- Organization membership is used to scope employee-facing and scheduling access.
- Scheduling shift lists and mutations are organization-scoped; legacy global shift templates remain visible without exposing tenant-owned templates.
- Scheduling state-changing endpoints use Django CSRF protection.
- Employee assignment validation enforces organization consistency for employee, shift template, client, client site, and cost center.
- Tenant-owned shift templates use `PROTECT` deletion semantics.
- Payroll processing has approval/payment separation and immutable lifecycle protections.
- Payroll records retain calculation provenance and input/output hashes.
- Django CSRF middleware, clickjacking protection, content-type sniffing protection, secure referrer policy, secure session cookies, and SameSite cookies are configured.
- Production configuration defaults to `DEBUG=False` and requires `DJANGO_SECRET_KEY` when `DJANGO_ENV=production`.
- CI runs Django's production deployment checks with production-style security settings.

## Remaining release blockers

Do not declare the application production-ready until all of the following are closed and covered by automated tests:

1. Replace or harden local media storage for employee documents/proof photos. Sensitive files must not be publicly enumerable or served without authorization.
2. Add authentication abuse controls: login throttling/lockout, password recovery, and security-event logging. Django session rotation is used by `login()`, but the surrounding authentication lifecycle still needs explicit regression coverage.
3. Add authorization tests for every payroll/HR mutation, including cross-tenant object IDs and privilege escalation attempts.
4. Add backup/restore verification, audit-log retention, incident response, and secret rotation procedures before handling real payroll data.
5. Validate current Philippine statutory rules against authoritative sources and freeze regression fixtures for each effective payroll rule version; software tests are not legal certification.
6. Complete payment-batch/disbursement controls and reconciliation before treating payroll as an end-to-end production payment system.

## Tenant-isolation rule

Never trust an object ID supplied by a browser. Every read, update, delete, and export must constrain the queryset by the authenticated organization before the object is loaded. Model-level `clean()` validation is useful defense-in-depth, but it does not replace organization-scoped querysets at the API boundary.

## Production environment baseline

At minimum, production deployment must explicitly provide:

- `DJANGO_ENV=production`
- `DJANGO_DEBUG=False`
- a unique high-entropy `DJANGO_SECRET_KEY`
- an explicit `DJANGO_ALLOWED_HOSTS`
- an explicit `DJANGO_CSRF_TRUSTED_ORIGINS` matching the HTTPS application origins
- TLS at the public edge
- a private database and private object storage
- restricted service credentials with least privilege
- centralized error/health monitoring and tested alerting

This document is a release gate and should be updated whenever a security-sensitive subsystem changes.
