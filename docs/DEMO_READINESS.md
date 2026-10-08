# HR demo readiness — October 2026

This document is the practical gate for demonstrating BizFlow HRIS to an HR stakeholder. It is intentionally narrower than the production go-live checklist.

## Demo status

**Current state: DEMO-READY — final Thursday validation gate**

The application has the core HRIS demonstration path: organization/roles, employee records and lifecycle, scheduling/attendance, leave, payroll processing with confidence preflight and maker/checker controls, payslips/reporting, employee self-service, onboarding, talent and HR operations.

The demo seed is designed to start payroll in a **DRAFT/open review state**, so the presenter can show the actual payroll story instead of displaying a pre-approved result.

## What must work in the HR demo

- [x] HR login and organization-scoped workspace
- [x] Employee directory and employee profile
- [x] Employee lifecycle/assignment data
- [x] Scheduling and attendance records
- [x] Leave request/approval flow
- [x] Payroll period, processing and confidence preflight
- [x] Payroll maker/checker separation
- [x] Payroll payment state and payslip authorization
- [x] ESS employee view
- [x] Onboarding workflow
- [x] Recruiting/performance/benefits/offboarding foundations
- [x] HR Operations: policies, announcements, approvals and timesheets
- [x] Reports and audit visibility
- [x] Demo seed command with representative data, including the SME role

## Presenter script

1. Log in as HR.
2. Start at the workspace dashboard and explain the organization/employee count.
3. Open Employees and show a complete employee profile, assignment and employment information.
4. Open Attendance and explain how schedule → actual attendance → payroll connects.
5. Open Leave and show a pending/approved request and balance.
6. Open Payroll: select the demo payroll period; run confidence preflight; process the period; review gross, statutory deductions, tax, net pay and exceptions; explain that processing and approval are intentionally separated; approve using the authorized checker account; mark payment only after the payment step; open a payslip.
7. Open Reports and show payroll/attendance/leave outputs.
8. Switch to Employee/ESS and demonstrate that the employee sees only their own information.
9. Show Onboarding, Talent and HR Operations as the broader HR platform story.
10. Close with the product boundary: Philippine payroll rules require current effective-date verification and qualified review before real payroll use.

## Do not claim in the demo

Do not present the following as completed production capabilities:
- true recurring/rotating date-aware scheduling and approved cover-shift workflow;
- split/double-shift attendance;
- complete payroll holiday/rest-day/overtime/night-differential stacking for every applicable rule combination;
- annual BIR reconciliation and full 13th-month audit workflow;
- bank disbursement file workflow;
- configurable onboarding/document-retention automation;
- production transactional email/password recovery;
- customer self-service signup and billing UI;
- live PayMongo, email, backup/restore and monitoring operations unless separately verified.

These are tracked in docs/master-checklist.md.

## Demo environment gate

Before the meeting:
- use a disposable demo/staging organization;
- seed data only with BIZFLOW_DEMO_PASSWORD supplied outside source control;
- verify the four demo roles: HR, Manager, Employee and Super User;
- verify the HR account can complete the payroll walkthrough;
- verify the checker/payment authority is a different user from the payroll processor;
- verify the employee account cannot see another employee's payroll or profile;
- run python manage.py check;
- run python manage.py migrate --check;
- run python manage.py test;
- verify /health/ and /ready/;
- use PostgreSQL/Redis and private object storage when demonstrating a hosted environment.

## Production is a separate gate

A successful HR demo is not the same as production readiness. Real customer data still requires PostgreSQL, HTTPS, exact secrets/hosts/CSRF configuration, shared cache, private object storage, PayMongo live configuration where applicable, transactional email, automated backups and a tested restore, monitoring/alerts, privacy/retention controls, customer acceptance testing, and qualified Philippine payroll/tax/employment/privacy review.