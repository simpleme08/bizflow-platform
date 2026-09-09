# Roles and access

Every record is scoped to an organization. A user needs an active organization membership and the relevant permission. Django superusers additionally have maintenance access.

| Role | Main capabilities |
| --- | --- |
| Super User / Owner | Full organization, user, employee, attendance, leave, payroll, reports, talent, and operations access |
| HR | Employees, users, attendance, Excel timekeeping import, leave approvals, payroll, reports, talent, and HR Operations |
| Administrator | Users, employees, attendance, leave approvals, reports, talent, and HR Operations |
| CEO | Employee/attendance visibility, leave approval, payroll visibility, reports |
| Manager / Team Leader | Employee/attendance visibility, shift scheduling, attendance actions, leave approvals |
| SME | Employee/attendance visibility, attendance actions, reports |
| Employee | ESS, their own leave submission, approved payroll/payslips, HR Hub, and standalone time clock |

## Administration workflow

1. Sign in as `demo_superuser` or a designated owner.
2. Open `/admin/`.
3. Create the Organization, then departments, positions, employment types, and cost centers.
4. Create a Django User and an Organization Membership with the correct role.
5. Create an Employee linked one-to-one to that user, then a primary Employee Assignment and Shift Template.
6. For payroll, create Employee Salary and Payroll Period records.

Do not assign more access than required. Revoke access by setting the membership inactive; do not delete a user while payroll/audit records need preservation.
