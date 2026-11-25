# Tenant Isolation and Workflow Authorization Follow-up — 25 Nov 2026

## Scope and evidence

Reviewed the current audit branch `audit/leave-authorization-hardening-2026-11-24` at the time of this note. This is a source review, not a penetration test. No production data, environment variables, Render settings, Supabase resources, or deployments were accessed or changed.

## Confirmed tenant-scoping patterns

The following paths consistently apply the active organization boundary in their principal list/detail lookups:

- Employee directory list filters employees by the active membership organization. Employee profile lookup verifies the employee organization against the active membership before returning profile data.
- Leave application lists and decisions filter through `employee__organization=membership.organization`. The updated decision path additionally denies self-approval and limits MANAGER / TEAM_LEADER decisions to direct reports.
- Onboarding lists, employee selection, workflow selection, task updates, and onboarding status updates are scoped to the active organization.
- Reports scope attendance, leave, payroll records, and payroll periods to the active organization.
- Attendance management and imports resolve employees by employee ID or employee number **and** active organization. Attendance logs and private photo routes are organization-scoped.
- Payroll lists and record mutations scope both employee and payroll period to the active organization.
- Talent recruiting, performance, benefits, and offboarding list/detail lookups scope their records through the active organization. Cross-tenant model relationship validation was added in this PR.
- HR Operations lists, document acknowledgements, projects, approvals, profile requests, and timesheets use organization-scoped querysets. Cross-organization model relationship validation was added for key operations models.

These are positive source-review findings; they do not replace cross-tenant IDOR tests against every route and role.

## Confirmed release blockers

### 1. Offboarding clearance evidence is client-trusted and not persistent

In `apps/talent/views.py`, `offboarding_status` allows a request to transition a record to COMPLETED when the client submits truthy values in `payload.clearances` for each required clearance. Those booleans are not independently verified or persisted as evidence. The record stores the required clearance names, but not who verified each clearance, when it was verified, or what evidence supports it.

**Required correction before production use:**

- Add a persistent clearance-evidence model linked to the offboarding record.
- Store clearance key, verification state, verifier (active member of the same organization), timestamp, notes, and a private evidence reference where applicable.
- Ignore/reject client-supplied completion booleans.
- Require every configured clearance to have a persisted verified evidence record before completion.
- Make completion and evidence writes transactional and audit each verification.
- Enforce an explicit transition graph; prevent reopening or regressing a completed record without a separately authorized, audited reversal workflow.
- Add tests for missing evidence, unverified evidence, cross-tenant verifier, unauthorized verifier, tampered client booleans, duplicate evidence, concurrent completion, and invalid state transitions.

### 2. Timesheet approval scope is broader than the leave manager scope

In `apps/operations/views.py`, `_can_approve_timesheets` grants approval to anyone with `manage_employees` or `manage_attendance`. The decision endpoint scopes the timesheet to the active organization and prevents self-approval, but it does not restrict MANAGER / TEAM_LEADER to their direct reports. This differs from the leave decision path and can allow a manager with organization-wide attendance permission to approve a peer's or unrelated team's timesheet.

**Required correction before production use:**

- Define an explicit organization-wide approver role set (for example, HR / ADMIN / CEO / OWNER / SUPER_USER) and a direct-report approver set (MANAGER / TEAM_LEADER).
- For direct-report roles, require the employee's manager relationship to point to the approver's employee profile.
- Do not infer approval scope solely from a broad permission flag.
- Add tests for own timesheet denial, direct report allowed, indirect report denied, peer denied, cross-tenant denied, inactive membership denied, and HR organization-wide approval.

### 3. SME attendance visibility and approval must remain distinct

The PR separates SME scheduling permission from attendance-record editing. Keep that separation through all timesheet and attendance decision endpoints. SME may manage shifts and view attendance where granted, but must not inherit timesheet approval or attendance write authority unless an explicit business policy grants it.

## Additional test coverage required

- Cross-tenant object IDs for every GET / POST / PATCH / DELETE endpoint in employees, leave, onboarding, attendance, reports, payroll, talent, and operations.
- Multi-organization user with no selected tenant: protected APIs must deny access rather than choose an arbitrary organization.
- Multi-organization user with a selected tenant: switching the active organization must not leak cached/queryset data from the previous tenant.
- Inactive organization and inactive membership: deny access consistently.
- Verify no serializer, template, export, report, file URL, or error response leaks another tenant's employee identifiers or private fields.
- Verify permission boundaries separately from tenant boundaries (same tenant but wrong role).
- Verify manager/team-leader scope for leave, timesheets, performance reviews, goals, and offboarding where applicable.

## Release status

- PR #42 remains draft and unmerged.
- No production deploy or infrastructure change is authorized by this review.
- Offboarding evidence and timesheet approval scope remain release blockers.
- Supabase staging verification, private-bucket ACL/restore checks, database backup/restore drill, SMTP configuration, malware scanning/quarantine, payroll statutory validation, and browser E2E / IDOR testing remain outstanding.


## Implementation update — 25 Nov 2026

The two workflow authorization gaps identified above have now been addressed on this audit branch:

- Added persistent `OffboardingClearanceEvidence` records with a unique record/clearance key, active same-organization verifier validation, server-generated verification timestamps, required notes, and an optional private evidence identifier (public URLs are rejected).
- Added a tenant-scoped clearance verification endpoint and exposed verification status to authorized HR users.
- Offboarding completion no longer trusts request-body clearance booleans. It requires stored evidence for every configured clearance and retains the employee separation-date and required-document checks.
- Added a locked forward-only transition graph: PLANNED → IN_PROGRESS → COMPLETED. Completed records cannot be reopened through the normal API.
- Timesheet decisions now permit organization-wide approval only for OWNER, SUPER_USER, ADMIN, and HR. MANAGER and TEAM_LEADER are restricted to direct reports. SME and employee roles cannot approve timesheets. Decisions use row locking and audit within the transaction.
- Added regression tests for the clearance bypass, persisted clearance evidence, invalid transitions, direct-report and peer decisions, HR organization-wide approval, self-approval, and employee denial.

**Verification:** GitHub Actions run #152 passed Django system checks, migration drift detection, and the full automated test suite for the implementation including the offboarding GET response. A follow-up run #154 is checking the final model validation that rejects public URLs in evidence references; its automated test step is still running at the time of this update.

These application-level fixes do not complete the external production release gates: Supabase staging and restore verification, SMTP setup, malware scanning, payroll statutory validation, browser E2E/IDOR coverage, and production change approval remain outstanding.
