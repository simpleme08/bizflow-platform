# Security production gate

BizFlow HRIS handles employee identity, compensation, attendance, leave, payroll, and statutory records. Security is therefore a release gate, not a post-launch enhancement.

## Current controls

- Organization membership is used to scope employee-facing and scheduling access.
- Employee assignment validation rejects tenant-owned shift templates from another organization.
- Tenant-owned shift templates use `PROTECT` deletion semantics.
- Payroll processing has approval/payment separation and immutable lifecycle protections.
- Payroll records retain calculation provenance and input/output hashes.
- Django CSRF middleware, clickjacking protection, content-type sniffing protection, and secure referrer policy are enabled.
- Production requires `DJANGO_SECRET_KEY` when `DJANGO_DEBUG=False`.

## Release blockers

Do not declare the application production-ready until all of the following are closed and covered by automated tests:

1. Remove CSRF exemptions from authenticated state-changing scheduling endpoints. JSON POST/DELETE requests must use Django CSRF protection or an explicitly reviewed non-cookie authentication mechanism.
2. Scope every scheduling lookup to the requester's organization. In particular, shift-template listing must never expose another organization's tenant-owned templates.
3. Enforce organization consistency for every `EmployeeAssignment` relationship: employee, shift template, client, client site, and cost center.
4. Replace or harden local media storage for employee documents/proof photos. Sensitive files must not be publicly enumerable or served without authorization.
5. Add authentication abuse controls: login throttling/lockout, password recovery, session rotation, and security-event logging.
6. Add authorization tests for every payroll/HR mutation, including cross-tenant object IDs and privilege escalation attempts.
7. Run `manage.py check --deploy` in the production build with production environment variables and fail the build on security warnings that are applicable to the deployment.
8. Add backup/restore verification, audit-log retention, incident response, and secret rotation procedures before handling real payroll data.

## Tenant-isolation rule

Never trust an object ID supplied by a browser. Every read, update, delete, and export must constrain the queryset by the authenticated organization before the object is loaded. Model-level `clean()` validation is useful defense-in-depth, but it does not replace organization-scoped querysets at the API boundary.

## Production environment baseline

At minimum, production deployment must explicitly provide:

- `DJANGO_DEBUG=False`
- a unique high-entropy `DJANGO_SECRET_KEY`
- an explicit `DJANGO_ALLOWED_HOSTS`
- an explicit `DJANGO_CSRF_TRUSTED_ORIGINS` matching the HTTPS application origins
- TLS at the public edge
- a private database and private object storage
- restricted service credentials with least privilege

This document is a release gate and should be updated whenever a security-sensitive subsystem changes.
