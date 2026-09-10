# Workforce operations and employee lifecycle

Operational modules use the employee lifecycle as a shared eligibility boundary.

- `ONBOARDING`, `PROBATIONARY`, and `REGULAR` employees can receive new shift assignments while `is_active` is true.
- `SUSPENDED`, `RESIGNED`, `TERMINATED`, and `SEPARATED` employees cannot receive new shift assignments.
- Suspended and separated employees cannot start new attendance sessions because lifecycle actions mark them inactive.
- New leave requests must be submitted by an active employee and must fall before any separation date.
- Pending leave cannot be approved when the employee is no longer eligible for the requested leave dates.
- Scheduling, attendance dashboards, leave management, and employee APIs scope employee records through the authenticated organization membership.
- Cross-organization employee IDs are rejected rather than resolved globally.

These rules preserve historical payroll, attendance, leave, and employment records while preventing new operational activity after an employee becomes ineligible.