# Operating workflows

## Employee lifecycle

### Create an employee

1. HR creates the user account and active organization membership in Admin.
2. HR creates the Employee profile; employee number is unique across the system.
3. HR assigns department, position, employment type, and a primary shift assignment.
4. HR sets salary if payroll will be processed.
5. HR starts onboarding at `/onboarding/`, selecting a workflow and expected completion date.
6. HR or task owners complete onboarding tasks. Use Talent/Operations records for benefits, documents, goals, and policy acknowledgements.

### Offboard an employee

1. HR creates an Offboarding Record in Admin/Talent with last working day and reason.
2. HR creates Offboarding Tasks: asset collection, access removal, final-pay review, exit interview, and benefits termination.
3. Stop future shift assignments and mark the employee inactive only after required payroll/records actions are complete.
4. Retain payroll and audit records according to your retention policy.

## Time, attendance, and scheduling

### Employee time clock

The public `/clock/` page is separate from the HRIS workspace. The employee signs in with their own username/password, clocks in or out, and the system uses their active assignment. The clock rejects an active clock-in without an assignment and prevents duplicate open records.

### HR manual attendance

At `/attendance/`, choose employee, date, time in/out, then save. The system calculates late, undertime, and overtime from the shift template. Use this for corrections only; it can overwrite the employee/date record.

### HR Excel timekeeping import

1. Sign in as HR, Super User, or Django superuser.
2. Open Attendance and download the Excel template.
3. Complete one row per employee/date using exact headers:

   ```text
   Employee Number | Attendance Date | Time In | Time Out | Status | Remarks
   ```

4. Upload `.xlsx`. The importer verifies header order, employee organization, active assignment, valid status, date/time order, and size.
5. If any row fails, nothing is saved; correct the listed rows and retry.
6. If valid, the importer creates or updates each employee/date attendance record and writes audit events.

### Shift scheduling

1. Manager/HR selects a worker in `/scheduling/`.
2. Select shift, optional client/site, start/end date, and whether it is primary.
3. Save; the assignment is used by the time clock and attendance calculation.
4. Review overlapping/old assignments before creating a new primary assignment. Delete only accidental assignments because attendance retains the assigned shift context.

## Leave

1. HR configures Leave Types and annual credits in Admin.
2. Employees use `/leave/` to see balances and submit date range/reason.
3. The request is pending until a Manager, Team Leader, HR, Owner, or Super User approves/rejects it according to their role.
4. Approval atomically checks remaining balance and increases used credits. Rejection leaves the balance unchanged.
5. Employees review request status and remarks in their leave history.

## Payroll

1. HR creates Employee Salary and Payroll Period records in Admin.
2. HR processes the period through `/api/payroll/process/` or the applicable administrative process.
3. Review draft records for salary, attendance adjustments, deductions, gross, and net pay.
4. A payroll manager approves individual records.
5. Employees only see approved/paid records at `/payroll/` and can download their own PDF payslip. They cannot access another employee’s payslip.

This payroll calculation is a system workflow, not a substitute for country-specific tax/statutory computation, filing, or legal review.

## Talent and performance

### Recruiting

1. HR creates Job Openings.
2. HR adds Candidates and creates Job Applications.
3. Move applications through Applied, Screening, Interview, Offer, Hired, or Rejected in Admin/API.
4. When hired, create the employee/user/assignment then begin onboarding.

### Performance

1. Create a Performance Cycle with dates and status.
2. Assign employee goals with measurable title, progress, status, and due date.
3. Managers create Performance Reviews with rating, strengths, development areas, comments, and review status.
4. Keep compensation change proposals in HR Operations linked to approvals.

### Benefits

1. HR creates Benefit Plans with provider and employee/employer cost.
2. HR creates Benefit Enrollments with effective date and status.
3. Use an external carrier connector only after the provider integration, data-sharing agreement, and secure secret configuration are complete.

## HR Operations and ESS

### Documents and announcements

1. HR opens `/operations/`, enters the policy title, category and summary, then either saves it as a draft or selects **Publish now**.
2. Select `Require acknowledgement` for policies that employees must confirm. Published, unexpired policies appear in `/employee-hub/`.
3. HR sends organization announcements from the same Operations page. A draft announcement is not visible to employees.
4. The employee opens `/employee-hub/` and selects **I acknowledge**. An acknowledgement is unique per employee/document.
5. Retire or replace outdated policies from Admin until document lifecycle actions are added to the Operations screen; do not silently edit a policy after employees have acknowledged it.

### Approvals and profile changes

1. Employees enter the requested name or email change in `/employee-hub/`. Nothing changes immediately.
2. HR reviews the pending request in `/operations/`, then chooses **Approve & apply** or **Reject**. Approval updates the authoritative Employee and User name/email fields.
3. HR creates Approval Requests for compensation or other controlled changes and can assign an HR Operations approver.
4. The assigned approver (or any authorized HR Operations user when unassigned) approves/rejects the request. Review audit events for traceability.

### Projects and timesheets

1. HR creates active Projects with a unique organization code and billable flag in `/operations/`.
2. Employees submit a date, project, hours and optional notes through `/employee-hub/`. Future dates and entries above 24 hours are rejected.
3. HR reviews submitted entries in `/operations/` and approves or rejects them. Only approved time should feed an external payroll/billing process after a formal integration is designed.

## Reports and audit

`/reports/` provides organization summaries for attendance, leave, and payroll. The Django Admin exposes `AuditEvent` records. Use report/audit review before payroll approval, after attendance imports, and during access/compliance reviews.
