# BizFlow HRIS product guide

## Purpose

BizFlow is a Philippine-focused, multi-tenant Django HRIS for small and mid-sized organizations. It brings employee records, workforce operations, attendance, leave, payroll, employee self-service, HR operations, talent workflows, reporting, and SaaS subscription billing into one application.

## Target customer

The product is designed around organizations with roughly 10–200 employees, especially businesses with recurring payroll and timekeeping needs such as restaurants, retail, BPO/support teams, agencies, clinics, schools, construction, staffing, manufacturing, logistics, and professional services.

## Core value proposition

1. Keep employee and employment information in one authoritative record.
2. Connect schedules, assignments, attendance, leave, and payroll instead of maintaining disconnected spreadsheets.
3. Make Philippine payroll/statutory calculations reviewable and auditable.
4. Give employees controlled self-service access to their own information.
5. Enforce organization boundaries and role permissions throughout the application.
6. Support recurring SaaS billing without making billing state client-authoritative.

## Modules

| Module | Purpose |
| --- | --- |
| Core | UUID model foundation, audit events, shared utilities, health/readiness, demo tooling |
| Accounts | Authentication and role-based workspace routing |
| Organization | Tenants, memberships, roles, departments, positions, employment types, cost centers, subscriptions |
| Employees | Employee master data, lifecycle, assignments, history, documents |
| Workforce | Clients, sites, shift templates and workforce context |
| Attendance | Time clock, attendance records, calculations, manual corrections, Excel import |
| Leave | Leave types, balances, applications and approval decisions |
| Scheduling | Employee shift assignments and scheduling APIs/UI |
| Payroll | Salaries, wage rates, periods, records, adjustments, loans, final pay, payslips and remittance/reporting exports |
| ESS | Employee self-service dashboards and summaries |
| Reports | Organization-scoped attendance, leave and payroll reporting |
| Onboarding | Workflows, templates and employee tasks |
| Talent | Recruiting, performance, benefits and offboarding |
| Operations | Policies/documents, acknowledgements, announcements, approvals, profile changes, compensation, projects/timesheets and connector metadata |

## Commercial model

The application currently defines these plan defaults:

| Plan | Monthly price | Included active employees | Overage rate |
| --- | ---: | ---: | ---: |
| Free | ₱0 | 5 | ₱50/employee |
| Starter | ₱499 | 10 | ₱50/employee |
| Growth | ₱1,499 | 30 | ₱40/employee |
| Business | ₱2,999 | 75 | ₱30/employee |

The active-employee count is the usage metric used for activation limits. Subscription state and plan limits are enforced server-side.

## Important product boundaries

- The payroll engine is a calculation and workflow system, not a guarantee of legal or tax compliance.
- Wage rates and statutory rules can be effective-date and region-specific; production payroll requires current source verification and qualified review.
- Remittance exports are reporting/export aids unless an external filing integration explicitly implements an agency's current submission specification.
- Connector records are integration metadata, not active provider integrations or a secret store.
- Email, SSO, carrier transmission, external signatures, background checks, and other provider-dependent functions require real integrations and credentials.

## Typical customer workflow

**Organization → people setup → employee lifecycle → schedules → attendance → leave → payroll → approval → payslip/reporting → billing**

HR and managers operate the controlled workflows; employees use ESS and the standalone time clock for their own actions.
