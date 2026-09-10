# Roles and access

## Access model

BizFlow uses organization membership plus role-based permissions. A user should have an active `OrganizationMembership` for the organization they are accessing. Django superusers additionally have Django maintenance/admin access.

## Roles

| Role | Typical capabilities |
| --- | --- |
| Owner / Super User | Full organization administration, users, employees, workforce, payroll, reports, talent and operations |
| HR | Employees, users, attendance/imports, leave approvals, payroll, reports, talent and HR Operations |
| Administrator | Administrative employee/attendance/leave/report/talent/operations functions according to configured permissions |
| CEO | Employee/attendance visibility, leave approval, payroll visibility and reports |
| Manager / Team Leader | Team employee/attendance visibility, scheduling, attendance actions and leave approvals |
| SME | Employee/attendance visibility, attendance actions and reports |
| Employee | Own ESS, leave requests, approved/paid payroll/payslips, HR Hub and time clock |

The exact permission mapping in code is authoritative if this table and implementation ever differ.

## Least privilege

Give each person the lowest role that supports their job. In particular:

- payroll approval should be limited to designated payroll authorities
- employee data should be limited to HR/authorized managers
- organization/billing configuration should be limited to designated administrators
- employees should only access their own self-service data

## Administration sequence

1. Create Organization.
2. Create departments, positions, employment types and cost centers.
3. Create shift templates and workforce clients/sites where needed.
4. Create Django users.
5. Add active OrganizationMembership records with the intended role.
6. Create Employee profiles linked to the correct users.
7. Create primary/current assignments.
8. Configure leave and salary/payroll data.

## Access changes

When someone leaves or should no longer have access, deactivate the organization membership promptly. Preserve the user/audit/payroll history rather than deleting records that are needed for traceability.

## Security rule

Never rely on route visibility or frontend controls for authorization. Every sensitive API/view must check authentication, membership, organization scope and permission on the server.

## Access review

At least monthly, review active memberships and privileged users. Before each payroll cycle, confirm payroll roles and employee status are correct. After role changes, sign out/in to refresh session context where necessary.
