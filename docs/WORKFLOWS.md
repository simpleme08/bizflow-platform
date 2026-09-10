# Operating workflows

## 1. Organization setup

1. Create the Organization.
2. Add departments, positions, employment types and cost centers.
3. Add shift templates and clients/sites if required.
4. Create users and active organization memberships.
5. Create employee profiles and primary assignments.
6. Configure leave types/balances and payroll salary/wage data.
7. Configure the subscription and PayMongo plan mapping when paid billing is enabled.

## 2. Employee lifecycle

### Hire/onboard

1. Create the user and active organization membership.
2. Create the Employee profile and unique employee number.
3. Set department, position, employment type and primary assignment.
4. Set salary/payroll profile when applicable.
5. Start an onboarding workflow and assign tasks.
6. Complete required documents, benefits, policies and acknowledgements.

### Changes

Use effective-dated employee/assignment history for changes that must preserve historical context. Controlled profile changes submitted by employees remain pending until authorized HR review applies them.

### Offboard

1. Create an offboarding record with last working day/reason.
2. Create tasks for assets, access, final pay, exit process and benefits.
3. Stop future scheduling/assignments.
4. Apply the lifecycle transition according to the configured effective date.
5. Complete final-pay review and retain required payroll/audit history.

## 3. Scheduling and attendance

Managers/HR create shift assignments for eligible employees. The employee time clock uses the employee's active assignment for the relevant date. Ineligible/separated employees cannot receive new operational assignments or perform normal clock-in actions.

### Manual attendance correction

Use Attendance to correct an employee/date record when required. Review the resulting late, undertime and overtime calculations against the assigned shift.

### Excel import

1. Download the in-app template.
2. Preserve exact headers:

```text
Employee Number | Attendance Date | Time In | Time Out | Status | Remarks
```

3. Upload `.xlsx`.
4. Correct every validation error reported by the importer.
5. Re-upload. The import is validated before save, so a failed workbook does not partially update attendance.

## 4. Leave

1. Configure leave types and credits.
2. Employee submits a date range/reason.
3. Authorized approver reviews the request.
4. Approval validates eligibility and remaining balance before applying the balance change.
5. Rejection leaves the balance unchanged.
6. Employees see their own status/history.

## 5. Payroll

1. Maintain employee salary/wage data and effective dates.
2. Create an organization-scoped payroll period.
3. Review attendance, leave, adjustments and loan inputs.
4. Process the period.
5. Review gross, deductions, net pay and exceptions.
6. Approve payroll records through the authorized workflow.
7. Mark records paid only after payment has actually occurred.
8. Generate payslips and reporting/remittance exports.
9. Perform the organization's statutory filing/payment process as applicable.

## 6. Employee self-service

Employees can use ESS/Employee Hub for their own supported information and requests. Self-service never grants access to another employee's payroll, leave, attendance, profile or billing data.

## 7. HR Operations

### Policies

Create a policy/document, choose whether acknowledgement is required, publish it, and have employees acknowledge it from Employee Hub. Avoid silently editing an already-acknowledged policy; publish a new version when historical wording must remain auditable.

### Announcements

Draft announcements remain internal until published. Published organization announcements are visible to eligible employees.

### Approvals/profile changes

Employee profile-change requests remain pending until authorized HR review. Compensation/controlled changes use the approval workflow where configured.

### Projects/timesheets

Employees submit project/date/hours entries. HR reviews and approves/rejects them. Approved timesheets should not feed payroll or billing externally until a formal integration and business rule is implemented.

## 8. Billing

1. Organization administrator selects a plan.
2. Application starts the PayMongo subscription flow.
3. Provider processes initial payment/subscription state.
4. Verified webhook events synchronize local subscription/invoice state.
5. Application enforces plan/employee limits server-side.
6. Monitor failed payments and webhook failures.

Do not mark an organization paid based solely on browser redirect success.

## 9. Reporting and audit

Review attendance, leave and payroll reports before payroll approval. Use AuditEvent records for investigation and access/compliance reviews. Export/archive information according to the organization's approved retention policy.
