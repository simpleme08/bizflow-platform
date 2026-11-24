# BizFlow HRIS — Render/Django Investigator Audit

**Audit date:** 24 November 2026  
**Repository:** `simpleme08/bizflow-platform`  
**Production branch:** `release/production-hardening`  
**Render service:** `hris` — `https://hris-r2zt.onrender.com`  
**Status:** Source, deployment configuration, service metadata, and workflow review. Not a penetration test or production certification.

## Executive verdict

The Render-hosted Django app and Floot project are **not the same running application**. Render runs the Django repository implementation. Floot is a parallel rebuild with its own frontend, endpoints, and managed database. They share the originating repository and product scope, but changes to either environment do not automatically synchronize to the other.

Render is currently running the exact HEAD commit of its configured production branch at the time of this audit:
- Commit: `26cb40782f0c63bbfc45e214aabb7cb0872c6d5b`
- Message: `Polish shared HRIS components and responsive accessibility`
- Render latest deploy status: `live`

**Do not treat the application as payroll-production-certified.** The audit found security gaps and statutory payroll calculation defects. Fixes are prepared in draft PR #42 and intentionally have not been merged or deployed to the live Render service.

## Confirmed fixes prepared in draft PR #42

Branch: `audit/leave-authorization-hardening-2026-11-24`

1. **Leave approval authorization**
   - MANAGER and TEAM_LEADER can now decide leave only for their direct reports.
   - Any user is blocked from approving or rejecting their own leave.
   - The decision, audit event, and notification are wrapped in one transaction.
   - Regression tests cover direct-report approval, unrelated employee approval/rejection, and self-approval.

2. **Login brute-force protection**
   - The public time-clock login previously authenticated directly without a rate limiter.
   - It now uses a five-attempt / 15-minute IP-and-username throttle.
   - Both the main login and time-clock login fail closed with HTTP 503 in production if the shared throttle cache cannot be read or updated. Development fallback remains available.
   - Regression tests cover rate-limit and cache-failure behavior.

3. **Scheduling decision validation**
   - Schedule-exception and cover-shift decisions now require a real JSON boolean. The string `"false"` can no longer be coerced to truthy and accidentally approve.
   - Row-locked decisions now execute inside a database transaction.
   - Cover shifts can only be decided while PENDING.
   - Regression tests cover malformed booleans and repeated cover-shift decisions.

4. **Philippine statutory payroll**
   - SSS MSC calculation previously rounded the raw salary upward to the next ₱500, overstating the contribution bracket for salaries within the lower portion of each official band. The new calculation follows the official half-step compensation brackets.
   - Pag-IBIG maximum fund salary was capped at ₱5,000 even though Circular No. 460 increased it to ₱10,000 effective February 2024. The cap and regression expectations are corrected.
   - Regression tests cover SSS bracket boundaries and the Pag-IBIG ceiling.

5. **SME permission separation**
   - Added a dedicated `manage_scheduling` permission and moved SME shift-management endpoints to it.
   - SME can retain attendance viewing without inheriting attendance record edit permissions. Regression tests cover both behaviors.

6. **Automated test workflow**
   - Added a GitHub Actions workflow for Django checks, migration drift detection, and the full test suite.
   - The first PR-triggered CI run is still in progress; the final test result is not yet known. The fixes must not be merged until CI passes.

## Deployment and infrastructure findings

### Confirmed deployment configuration drift — HIGH

The live Render service is configured with:
- Build: `pip install -r requirements.txt && python manage.py collectstatic --noinput`
- Start: `python manage.py migrate --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`
- Health-check path: empty
- Plan: Free
- Auto-deploy: enabled
- Region: Singapore

The repository's `render.yaml` describes a service named `bizflow-hris`, while the live service is named `hris`. It specifies a different build command, including `manage.py check --deploy` and `makemigrations --check --dry-run`, and a `/ready/` health check. Those checks are not present in the actual Render service configuration. The Blueprint also defines a `bizflow-hris-maintenance` cron job on the paid Starter plan, but the Render workspace service listing showed only the web service. The Blueprint's start command optionally provisions production accounts; the live service's configured start command does not.

**Impact:** the production deployment can skip configuration and migration-drift checks; Render is not using the intended readiness endpoint; scheduled retention, document-expiry notification, and notification-delivery jobs are not confirmed deployed.

**Remediation:** reconcile the actual service with the reviewed Blueprint, add the maintenance cron service, and verify each job's schedule and logs before enabling it.

### External infrastructure not verified — HIGH

The workspace contained no Render-managed PostgreSQL or Redis resource. The production Django settings require PostgreSQL, Redis, and S3-compatible private storage. These may be external services referenced by environment variables; their existence, connectivity, backup policies, and access controls were not exposed by the service metadata inspection.

**Required verification:** confirm the configured external database, shared cache, object storage bucket, encryption, private ACLs, short-lived signed URLs, backups, and restore drills. Do not paste secret values into tickets or chat.

### Operational visibility — MEDIUM

- Latest Render deploy is marked live.
- No error-level logs were returned for the queried recent window.
- Metrics returned empty time series, so latency, traffic, CPU, and memory health could not be assessed.
- The public `/ready/` and `/health/` endpoints could not be independently reached through the available inspection channel.

A live deploy status alone does not prove end-to-end application readiness.

## Remaining security and business-logic findings

### 1. SME/manager permission granularity — PARTIALLY FIXED IN THIS PR
The role matrix previously gave SME `manage_attendance`, which also authorized attendance record creation/correction because scheduling and attendance editing shared one permission. PR #42 introduces a separate `manage_scheduling` permission, grants it to SME, and removes `manage_attendance` from SME. Scheduling endpoints and dashboard visibility now use the dedicated permission. Regression tests verify SME can access scheduling and view attendance while attendance record writes remain forbidden.

**Still outstanding:** MANAGER and TEAM_LEADER scheduling operations remain organization-wide rather than restricted to their assigned teams/direct reports. Attendance corrections for those roles also need an explicit policy decision.

### 2. Schedule-exception state model — HIGH
`ScheduleException` stores only an `approved` boolean. A rejected exception is indistinguishable from a pending exception, and the decision endpoint can toggle the boolean repeatedly. It needs explicit PENDING/APPROVED/REJECTED states, an approver, decision timestamp, reason, and transition checks.

### 3. Shift assignment deletion audit — MEDIUM
`delete_assignment` deletes a shift assignment without recording an audit event. Deletion should be a transactional, permission-checked, audited operation, ideally preserving historical assignment evidence instead of hard-deleting records used by attendance/payroll.

### 4. Offboarding evidence and transition controls — HIGH
Offboarding completion checks required clearances using booleans supplied in the request payload. Those attestations are not persisted as independent clearance records with a responsible approver, timestamp, evidence, and audit event. Status transitions are not constrained to a defined state machine, so a caller with `manage_offboarding` can skip intermediate states.

**Remediation:** persist each clearance and asset return, require the correct authorized owner, validate transitions, verify final pay and access revocation, and perform final separation in one audited transaction.

### 5. Payroll rule-set provenance is not yet executable — CRITICAL
`PayrollConfidence` selects an effective-dated `PayrollRuleSet` and records its version/hash, but the actual calculator uses hard-coded constants in `PhilippinePayrollRules` and `PhilippineWithholdingTax`. The selected rule-set payload is not passed into the calculation. Therefore, a new rule-set version can be recorded without changing the calculations.

**Remediation:** make the effective-dated rule set the actual calculation input, or remove the claim that the rule-set version controls the calculation. Store the exact source circular, effective date, formula version, inputs, outputs, and hashes for each record. Add golden tests against agency/BIR examples and require payroll-professional approval for every ruleset update.

### 6. Statutory contribution bases are not yet agency-specific — CRITICAL
The calculator currently passes the same `monthly_basic` value to SSS, PhilHealth, and Pag-IBIG. That is not a safe universal base: SSS uses the employee's actual remuneration subject to its statutory rules, Pag-IBIG Fund Salary includes basic salary and other allowances, while PhilHealth's employee basis is Monthly Basic Salary. The calculator therefore needs separate, component-aware contribution bases rather than a single basic-pay input. The SSS bracket and Pag-IBIG ceiling corrections in this PR do not solve this broader classification issue.

**Remediation:** classify every pay component by agency contribution treatment and effective date; calculate each agency base independently; add golden fixtures for basic pay, COLA, allowances, commissions, absences, and maximum bases; validate with official schedules and a Philippine payroll professional before live use.

### 7. Payroll absence recalculation needs MWE/tax-classification parity — HIGH
The absence-deduction adjustment path recomputes withholding tax separately from the main calculator and does not visibly reuse the main minimum-wage-earner exemption path. It can produce a different withholding result after an absence adjustment.

**Remediation:** route all recalculations through one shared tax-classification and withholding service; add regression fixtures for minimum-wage earners, non-taxable benefits, 13th-month thresholds, and retroactive adjustments.

### 8. Attendance anti-fraud controls — MEDIUM
Geofence coordinates and device IDs are supplied by the client. They can be spoofed by a modified client and should not be treated as strong device/location attestation. Clock photos are useful evidence but do not prove physical presence by themselves.

**Remediation:** describe these controls accurately, use managed-device attestation where supported, apply anomaly detection, preserve correction reasons, and require supervisor review for exceptions. Do not rely on GPS alone for payroll approval.

### 9. Document access policy — HIGH, requires policy confirmation
The employee-document file endpoint checks organization membership and PUBLISHED status, but does not check whether the requester owns the employee record or has an HR/document-management permission. This is safe only if PUBLISHED documents are intentionally organization-wide documents. If employee-specific files can reach this state, any member of the tenant could retrieve them.

**Remediation:** distinguish organization policy documents from confidential employee documents; enforce employee-self or HR/document permission for employee-specific files; avoid exposing raw storage URLs; log downloads.

### 10. Audit retention and legal hold — HIGH
The scheduled retention command permanently deletes old audit events and archived documents based on organization-configured retention values. No legal-hold or immutable export mechanism was confirmed. Audit deletion may conflict with an investigation, employment dispute, or statutory retention requirement.

**Remediation:** add legal holds, retention policy approval, deletion audit events, immutable export/archive, and documented retention schedules. Run the command in dry-run mode before any policy change.

### 11. Notification delivery idempotency — MEDIUM
The notification delivery command selects pending/failed records without row locking or a delivery claim. Concurrent workers or overlapping cron runs could send the same notification more than once.

**Remediation:** claim notifications atomically, use idempotency keys, persist provider message IDs, and retry with bounded exponential backoff.

### 12. Benefit lifecycle — MEDIUM
Benefit enrollment creation checks tenant ownership but does not visibly prevent overlapping active enrollments, validate plan eligibility, or reconcile employee deductions against payroll. End-date/status changes and dependent coverage need a complete lifecycle.

### 13. Backups, disaster recovery, and release controls — HIGH
No completed database restore drill, object-storage restore test, incident runbook, or tested rollback procedure was confirmed. The Free web-service plan and external dependency configuration need explicit availability expectations.

## Required release gates

1. Merge PR #42 only after the new CI workflow passes.
2. Verify Render's real environment variable *presence* without disclosing secret values; test PostgreSQL, Redis, S3, and SMTP connectivity.
3. Reconcile Render's actual service configuration with `render.yaml`; deploy and verify `/ready/`.
4. Deploy the maintenance cron and prove notification delivery and retention dry-run behavior.
5. Complete SME permission separation, schedule-exception state machine, offboarding evidence, and document-access authorization.
6. Make payroll rulesets executable and validate statutory payroll with current official circulars and a Philippine payroll professional.
7. Run tenant-isolation, IDOR, manager-scope, self-approval, race-condition, file-access, payroll golden-fixture, and browser end-to-end tests.
8. Perform backup restore and rollback exercises before live employee/payroll data is used.

## Evidence and limitations

The Render service metadata and deployment list were read from the connected Render workspace. The production branch reference was checked against the latest Render deployment commit. Django source files and tests were reviewed from the same Git branch. Render service logs and metrics were queried; the logs returned no errors for the selected window and metrics returned empty data. No live database contents or secret environment values were read. The public web endpoints could not be independently reached by the available inspection channel.

This report is a source/configuration audit, not a certified penetration test. The fixes in PR #42 are isolated from the production branch; they have not been merged or deployed.
