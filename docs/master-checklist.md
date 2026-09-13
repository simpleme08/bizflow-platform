# BizFlow HRIS master checklist

## Product and platform foundation

- [x] Django HRIS application foundation
- [x] Organization/tenant model and memberships
- [x] Role-based permissions and audit events
- [x] Employee master data and lifecycle
- [x] Effective-dated employee/assignment history
- [x] Workforce, scheduling and lifecycle integration
- [x] Attendance, time clock and atomic Excel import
- [x] Leave balances, requests and approvals
- [x] Payroll periods, salary/wage data and payroll processing
- [x] Adjustments, loans and final-pay workflow
- [x] PDF payslips
- [x] Philippine payroll/compliance foundations and reporting exports
- [x] Employee self-service and HR Hub
- [x] Onboarding
- [x] Recruiting, performance, benefits and offboarding foundations
- [x] HR Operations workflows
- [x] Reports and audit visibility

## SaaS and billing foundation

- [x] Free/Starter/Growth/Business plan catalog
- [x] Active-employee usage limits
- [x] Subscription state model
- [x] PayMongo checkout/subscriptions
- [x] Invoice synchronization
- [x] Plan changes and cancellation
- [x] Signed/idempotent PayMongo webhook handling
- [x] Billing audit events and tenant isolation

## Engineering and security foundation

- [x] Migration graph hardening
- [x] Regression test coverage across major workflows
- [x] Production secret fail-closed configuration
- [x] Secure production defaults
- [x] Health endpoint `/health/`
- [x] Database readiness endpoint `/ready/`
- [x] Render deployment configuration
- [x] Setup, architecture, API, security, testing and operations documentation

## Critical product hardening — required before claiming production-grade completeness

### Workforce and attendance

- [ ] Replace continuous employee assignment as the only scheduling model with a true date-aware/recurring schedule model (workdays, rest days, rotating shifts and schedule exceptions).
- [ ] Add an explicit approved Cover Shift workflow that can override an employee's normal shift for a specific work date without destroying the permanent assignment.
- [ ] Store the covered shift/client/site context on the attendance event for payroll reconciliation.
- [ ] Support multiple work segments in one date where operationally required; the current one-record-per-employee-per-date model is insufficient for split/double shifts.
- [ ] Reconcile cover/unscheduled punches before payroll approval with a visible exception queue.
- [ ] Add attendance policy configuration for grace periods, rounding, meal breaks and company-specific overtime rules.
- [ ] Add optional site/device/geofence controls only where a customer requires them.
- [ ] Move attendance proof photos to private persistent object storage before production; local/ephemeral filesystem storage is not sufficient.
- [ ] Establish photo retention, deletion and privacy controls.

### Payroll Confidence Engine

- [ ] Version the Philippine payroll rule registry with effective dates and official-source provenance.
- [ ] Add a payroll calculation provenance record/hash after a proper migration-backed implementation.
- [ ] Separate base pay, premium pay and statutory/tax classifications so taxable/non-taxable treatment is explicit instead of inferred from broad buckets.
- [ ] Implement holiday + rest-day + overtime + night-differential stacking using the applicable effective rule set.
- [ ] Implement absence/unpaid-day handling so an ABSENT attendance record cannot silently leave full basic pay untouched.
- [ ] Add monthly statutory reconciliation so semimonthly rounding differences are reconciled rather than simply divided across periods.
- [ ] Add regional wage-rate hard gates for minimum-wage earners and effective-date validation.
- [ ] Add annual BIR reconciliation using only the appropriate approved/paid payroll records and explicit tax classifications.
- [ ] Make 13th-month computation auditable against calendar-year basic salary actually earned.
- [ ] Add a confidence preflight with `READY`, `REVIEW`, and `BLOCKED` outcomes and explainable exceptions.
- [ ] Add regression scenarios for current SSS, PhilHealth, Pag-IBIG, BIR and DOLE/NWPC rules and maintain source/effective-date tests.
- [ ] Add maker/checker payroll segregation so processing, approval and payment are not automatically the same authority.
- [ ] Add payment-batch/disbursement workflow; bank files should be generated for upload to the customer's bank portal before any future automated bank integration.
- [ ] Add payroll period-level reconciliation for gross, deductions, employer cost, net pay and payment totals.

### HR and employee lifecycle

- [ ] Add configurable employee onboarding/offboarding checklists and required-document gates per organization.
- [ ] Add employee document expiry notifications and configurable retention rules.
- [ ] Add notifications/email delivery for approvals, payroll release, leave decisions and important HR events.
- [ ] Add self-service password recovery/email verification for production onboarding.

### Reporting and audit

- [ ] Add exportable management reports with period filters and organization-specific reporting configuration.
- [ ] Add audit-log search/filter/export and retention controls suitable for customer investigations.
- [ ] Add operational exception dashboards for attendance, leave, payroll and billing.

### SaaS productization

- [ ] Add organization self-service signup/invitation and controlled first-admin provisioning.
- [ ] Add customer-facing billing/subscription management UI beyond backend endpoints.
- [ ] Add provider failure/retry visibility for PayMongo and transactional email.
- [ ] Add a documented customer migration/import path for employees, attendance and payroll opening balances.
- [ ] Add client-configurable branding/site configuration rather than relying primarily on source-controlled client profiles.

## Final operational gate — required before real customer data

- [ ] Provision production PostgreSQL
- [ ] Configure production domain/DNS/HTTPS
- [ ] Configure production secrets and exact hosts/CSRF origins
- [ ] Configure PayMongo live account, plans, credentials and webhook
- [ ] Configure transactional email
- [ ] Enable automated backups and verify restore
- [ ] Configure monitoring and alerts
- [ ] Establish privacy/data-retention process
- [ ] Complete first-customer acceptance test
- [ ] Complete qualified Philippine payroll/tax/employment/privacy review

These final items depend on live infrastructure, third-party accounts and organizational controls. They cannot be truthfully marked complete from source control alone.

## Documentation index

- `README.md` — project entry point
- `docs/PRODUCT.md` — product scope and commercial model
- `docs/SETUP.md` — installation and environment setup
- `docs/ARCHITECTURE_AND_API.md` — architecture and routes
- `docs/API.md` — API reference
- `docs/ROLES_AND_ACCESS.md` — authorization model
- `docs/WORKFLOWS.md` — end-to-end workflows
- `docs/PAYROLL_AND_COMPLIANCE.md` — payroll/compliance boundary
- `docs/BILLING.md` — SaaS and PayMongo operations
- `docs/SECURITY.md` — security model
- `docs/TESTING.md` — test strategy
- `docs/OPERATIONS.md` — routine operations and releases
- `docs/production-launch.md` — production go-live gate
- `docs/CONTRIBUTING.md` — development workflow
