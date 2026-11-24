# Architecture Decision Record: BizFlow platform direction

**Decision date:** 24 November 2026  
**Status:** Accepted direction; production rollout remains gated  
**Decision:** Use the existing Django application in `simpleme08/bizflow-platform`, deployed on Render, as the sole canonical BizFlow HRIS implementation. Floot remains a disposable UI/prototype environment and is not a second production codebase.

## Context

BizFlow is intended to become a multi-tenant HRIS with employee self-service, attendance and scheduling, leave, payroll, onboarding/offboarding, talent management, benefits, reporting, audit trails, and role-scoped access. It processes highly sensitive employee, compensation, identity, and attendance data. Correctness, tenant isolation, authorization, auditability, data ownership, testability, and recoverability matter more than rapid UI generation.

The existing Render implementation is a Django application backed by a GitHub repository, with domain models, migrations, established workflows, and a CI test suite. The latest reviewed CI run passed Django checks, migration drift checks, and 237 tests. A separate Floot project has its own implementation and database; it is not automatically synchronized with the Django repository or Render database.

## Options considered

### Render + existing Django repository — selected

- Preserves the existing application, business logic, schema, migrations, and test investment.
- Provides full control over authorization, transactions, audit trails, background jobs, statutory calculations, data exports, and infrastructure.
- GitHub provides version history, reviewable changes, CI, and a clear release trail.
- Supports incremental infrastructure choices and portability; the application is not locked to a visual app builder.
- Requires more disciplined engineering and deployment operations.

### Floot as the primary implementation — rejected for this project

- Excellent for rapid UI prototypes and lightweight app development.
- Would require rebuilding or reconciling existing Django workflows and business rules.
- Its independent data store and codebase create a second source of truth and migration/synchronization risk.
- Free plan limitations include no recurring hosting allowance, no custom domains, and saved scheduled jobs that do not run. Those are material constraints for a real HRIS with scheduled notices, retention, and payroll operations.
- The existing Floot preview is useful for experiments, but must not become a parallel production HRIS.

## Cost decision

- Keep the GitHub repository as the source of truth and use the existing Render deployment for development/demo while the budget is zero.
- Do not add paid Render workers, cron jobs, databases, storage, or workspace subscriptions until their requirements and recurring cost are approved.
- Do not use a free Render web service or free Render Postgres as a production system of record: free web services can spin down/restart and have no persistent disk; free Postgres expires after 30 days and has no backups.
- Before real employee/payroll data or a production launch, budget for always-on application compute, durable managed PostgreSQL with backups/PITR, shared cache/queue if required, private object storage, monitoring, and scheduled jobs. Obtain current quotes from the provider dashboard before purchase.
- Floot subscription/hosting spend is not justified while it would only maintain a duplicate implementation.

## Non-negotiable architecture rules

1. One canonical codebase: `simpleme08/bizflow-platform`.
2. One authoritative production database; no manual copying of live data between Render and Floot.
3. All changes go through feature branches, pull requests, CI, reviewed migrations, and an explicit release.
4. Never run destructive migrations, seed commands, retention jobs, or payroll processing against production without a backup, dry-run, and explicit release procedure.
5. No real payroll use until the statutory engine uses effective-dated executable rulesets, agency-specific contribution bases, validated tax classifications, and payroll-professional-reviewed golden fixtures.
6. No production employee data until tenant isolation, IDOR, role scope, employee document access, offboarding evidence, audit retention/legal hold, and backup/restore gates pass.
7. Floot may be used to explore UI concepts only. Any approved design is reimplemented in the canonical Django frontend; no Floot business logic or data is treated as authoritative.

## Immediate implementation plan

1. Freeze feature development in the Floot duplicate; preserve it as a reference prototype only.
2. Continue the existing Django hardening work in PR #42 and extend its audit backlog in small, test-backed PRs.
3. Reconcile the actual Render service configuration with the repository Blueprint only after confirming the correct Render workspace and reviewing all environment dependencies.
4. Keep the current live service untouched until database, cache, object-storage, backup, health-check, scheduled-job, and rollback gates are verified.
5. Establish a zero-cost development/demo phase, then a paid production-readiness budget before handling real employee data.

## Consequences

This decision avoids maintaining two implementations and protects the investment in Django. It does not mean the current free Render deployment is production-safe. Render is the chosen engineering and deployment path; production operation remains blocked until the infrastructure and security gates are met.
