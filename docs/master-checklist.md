# BizFlow HRIS master checklist

## Product and platform

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
- [x] Recruiting, performance, benefits and offboarding
- [x] HR Operations workflows
- [x] Reports and audit visibility

## SaaS and billing

- [x] Free/Starter/Growth/Business plan catalog
- [x] Active-employee usage limits
- [x] Subscription state model
- [x] PayMongo checkout/subscriptions
- [x] Invoice synchronization
- [x] Plan changes and cancellation
- [x] Signed/idempotent PayMongo webhook handling
- [x] Billing audit events and tenant isolation

## Engineering and security

- [x] Migration graph hardening
- [x] Regression test coverage across major workflows
- [x] Production secret fail-closed configuration
- [x] Secure production defaults
- [x] Health endpoint `/health/`
- [x] Database readiness endpoint `/ready/`
- [x] Render deployment configuration
- [x] Setup, architecture, API, security, testing and operations documentation

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
