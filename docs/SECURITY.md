# Security model

## Security objectives

BizFlow handles employee, payroll, attendance, leave and billing data. The primary controls are tenant isolation, role/permission checks, authenticated sessions, CSRF protection, server-side validation, audit events, and production-safe secret handling.

## Tenant isolation

Every organization-facing operation must resolve the authenticated organization membership and scope queries to that organization. Never accept an organization ID from the browser as the authority for access.

When a resource belongs to another organization, avoid revealing its existence. Employee profile access, for example, returns not-found behavior for cross-organization identifiers.

## Authentication and authorization

- Django authentication establishes the user identity.
- `OrganizationMembership` establishes organization membership and role.
- Role permissions determine allowed operations.
- Django superusers have maintenance/admin access.
- Inactive memberships must not retain operational access.
- UI hiding is not an authorization control; every sensitive endpoint must enforce permission server-side.

## Sensitive operations

Payroll processing/approval, employee lifecycle actions, attendance corrections/imports, leave decisions, profile changes, compensation approvals and billing state changes require server-side validation and should create audit records where the workflow supports them.

## Secrets

Never commit:

- Django secret keys
- database passwords
- PayMongo secret/public keys or webhook secrets
- email credentials
- SSO/provider credentials
- connector credentials

Use the deployment platform's secret/environment facility.

## Production baseline

Set `DJANGO_DEBUG=False`, use PostgreSQL, exact `DJANGO_ALLOWED_HOSTS`, HTTPS, CSRF trusted origins, secure cookies, HSTS and the configured security headers. Production startup must fail closed when the required Django secret is absent.

## Billing security

The browser is not authoritative for subscription state or plan limits. PayMongo webhook signatures must be verified against the raw request body before processing. Webhook event handling must tolerate duplicate delivery without applying the same business effect twice.

## Data handling

Employee and payroll information should be collected only for legitimate business purposes, retained according to the organization's approved retention schedule, and removed or archived using a documented process. Review applicable Philippine privacy, employment and tax requirements with qualified advisers.

## Security testing checklist

Before a production release, test at minimum:

- unauthenticated access to protected pages/APIs
- inactive membership access
- cross-organization employee/payroll/attendance/leave access
- permission escalation by changing request parameters
- invalid lifecycle transitions
- duplicate attendance/time-clock actions
- malformed/oversized attendance imports
- unauthorized payslip access
- invalid and duplicate PayMongo webhooks
- missing production secrets and incorrect hosts

## Incident response

1. Preserve relevant logs/audit events.
2. Disable compromised user memberships or provider credentials.
3. Protect payroll/billing workflows from further mutation.
4. Rotate affected secrets.
5. Determine affected organizations and records.
6. Restore from a known-good backup only after validating the recovery target.
7. Document the incident, remediation and required customer/regulatory notifications.
