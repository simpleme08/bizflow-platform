# Production operations checklist

This document is the operational companion to the production launch gate.

## Daily

- Check application health/readiness.
- Review failed notification deliveries.
- Review payroll and attendance exception queues.
- Review billing/provider failures.
- Check critical monitoring alerts.

## Before every payroll cycle

- Verify effective payroll rules and regional wage rates against current authoritative sources.
- Confirm employee master data and effective-dated compensation.
- Resolve attendance exceptions.
- Review payroll confidence preflight.
- Reconcile payroll totals.
- Enforce maker/checker approval.
- Review statutory classifications and outputs.
- Keep evidence of payroll approval and payment/disbursement.

## Weekly

- Review audit/security events.
- Review storage usage and retention jobs.
- Review failed scheduled jobs.
- Verify backup status.
- Review privileged accounts and remove unnecessary access.

## Monthly

- Perform or verify a restore test according to the organization's recovery schedule.
- Review retention settings and legal holds.
- Review dependency/security updates.
- Review PayMongo and email provider status/credentials.
- Review customer support and incident records.

## Incident response

1. Identify and scope the incident.
2. Protect customer data and contain unauthorized access.
3. Preserve relevant logs/audit evidence.
4. Rotate compromised credentials where necessary.
5. Restore service/data using the approved recovery procedure if required.
6. Document timeline, impact, actions and follow-up.
7. Complete customer/regulatory notifications according to applicable obligations.

## Change control

Production changes must be traceable to a reviewed Git commit/PR and should pass the repository's required checks before deployment. Database migrations must be included with the application change and verified before customer traffic is restored.

## Recovery objective record

For each production deployment, record the agreed RPO/RTO, backup provider, backup retention, restore owner and last successful restore-test date.

RPO: ____________________

RTO: ____________________

Backup owner: ____________________

Last restore test: ____________________

Next restore test: ____________________
