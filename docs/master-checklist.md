# HRIS master checklist

## Completed

- [x] Core HR organization, roles, permissions, audit logging, tenant isolation
- [x] Employee master data, lifecycle, effective-dated history, manager relationships, documents
- [x] Scheduling, attendance, leave, and lifecycle integration
- [x] Philippine payroll engine and compliance foundations
- [x] Loans, adjustments, final pay, payslips, remittance/reporting exports
- [x] SaaS plans, employee limits, subscription controls, usage API
- [x] PayMongo checkout, recurring subscriptions, plan changes, cancellation, invoices
- [x] Verified and idempotent billing webhooks and subscription state synchronization
- [x] Billing audit events, tenant isolation, and server-authoritative plan mapping
- [x] Migration/CI hardening and regression coverage
- [x] Production security defaults and fail-closed production secret configuration
- [x] Production health/readiness endpoints
- [x] Render deployment health check and migration command
- [x] Production operations/runbook and first-customer acceptance checklist

## Final operational gate

- [ ] Provision production PostgreSQL
- [ ] Configure production domain/DNS and HTTPS
- [ ] Configure PayMongo live account, plans, credentials, and webhook
- [ ] Configure email delivery
- [ ] Enable/test backups and restore
- [ ] Configure monitoring and alerts
- [ ] Complete first-customer acceptance test

These final items require access to the production infrastructure and third-party accounts; they cannot be completed safely from source control alone.
