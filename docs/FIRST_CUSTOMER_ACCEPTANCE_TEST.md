# First-customer acceptance test

Run this against a dedicated staging/test tenant before loading real employee data. Record evidence for every result.

## 1. Tenant and access isolation

- [ ] Create customer organization.
- [ ] Create HR administrator and employee users.
- [ ] Verify inactive/unverified users cannot access protected workflows.
- [ ] Verify a user cannot read or modify another organization's employees.
- [ ] Verify role restrictions for HR, payroll processor, payroll approver and employee self-service.
- [ ] Verify audit events are tenant-scoped.

## 2. Employee lifecycle

- [ ] Create employee.
- [ ] Add effective-dated assignment.
- [ ] Upload a private employee document.
- [ ] Verify document access is authorized and tenant-scoped.
- [ ] Exercise onboarding required-document gate.
- [ ] Exercise offboarding clearance/document gate.

## 3. Workforce and attendance

- [ ] Configure work schedule, rest day and shift.
- [ ] Create an approved schedule exception.
- [ ] Create and approve a cover shift.
- [ ] Record attendance for normal, late, overtime and rest-day cases.
- [ ] Verify split work segments where required.
- [ ] Verify unresolved attendance exceptions appear before payroll approval.
- [ ] Test clock controls if the customer requires device/geofence enforcement.

## 4. Leave

- [ ] Configure leave type/balance.
- [ ] Submit employee leave request.
- [ ] Approve and reject separate requests.
- [ ] Verify employee notification and audit trail.
- [ ] Verify balance changes are correct.

## 5. Payroll

- [ ] Create payroll period.
- [ ] Confirm salary/effective wage data.
- [ ] Process a representative employee.
- [ ] Verify absence, overtime, holiday/rest-day and night-differential scenarios applicable to the customer.
- [ ] Review statutory deductions and tax classification.
- [ ] Run payroll confidence preflight.
- [ ] Resolve/block any required exceptions.
- [ ] Verify maker/checker segregation.
- [ ] Approve payroll and generate payslip.
- [ ] Generate controlled bank disbursement output only after the period is eligible.

## 6. Employee self-service

- [ ] Employee can view permitted profile information.
- [ ] Employee can submit permitted leave requests.
- [ ] Employee can access permitted payslips/documents.
- [ ] Password recovery works through configured transactional email.
- [ ] Email verification works for a new account.

## 7. Billing

- [ ] Verify subscription state for the tenant.
- [ ] Verify plan/employee limit behavior.
- [ ] Test checkout in provider test mode.
- [ ] Verify signed/idempotent webhook behavior.
- [ ] Confirm provider failures are visible and retryable.

## 8. Reporting and operations

- [ ] Export required attendance/payroll/management reports.
- [ ] Search and filter audit events.
- [ ] Review operational exception dashboards.
- [ ] Verify health and readiness endpoints.
- [ ] Verify scheduled maintenance commands complete successfully.

## 9. Security and recovery

- [ ] Confirm HTTPS and exact host/CSRF configuration.
- [ ] Confirm production secrets are stored outside source control.
- [ ] Confirm private object storage is used.
- [ ] Perform a backup and restore test.
- [ ] Verify monitoring alerts for application/database failure.

## Acceptance record

Customer/tenant: ____________________

Test date: ____________________

Tester: ____________________

Application commit: ____________________

Result: PASS / FAIL / CONDITIONAL

Open issues and owner: ____________________

Customer acceptance/sign-off: ____________________
