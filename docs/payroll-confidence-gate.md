# Payroll confidence gate

Payroll is **not considered production-ready merely because the calculator tests pass**. A production payroll run must have an effective, versioned rule set with provenance and an applicable wage-rate table.

## Current gate

`python manage.py payroll_confidence_check --date YYYY-MM-DD --organization <slug>` validates:

- an active organization exists;
- an organization-specific or global effective-dated payroll rule set exists;
- the selected rule set has a version, source name, and source URL;
- an effective wage-rate table exists for the organization or global scope.

A missing rule set is **BLOCKED**. Missing wage rates produce **REVIEW** because minimum-wage validation cannot be completed safely.

## Remaining production confidence work

The calculation engine still needs explicit, source-backed configuration for the exact payroll period before a live payroll is processed. In particular:

1. Load and maintain the applicable SSS schedule and effective dates.
2. Load and maintain the applicable PhilHealth schedule and effective dates.
3. Load and maintain the applicable Pag-IBIG schedule and effective dates.
4. Load the applicable regional wage orders and categories.
5. Maintain BIR compensation withholding rules and their provenance.
6. Classify taxable/non-taxable/de minimis compensation explicitly rather than relying only on broad payroll fields.
7. Validate holiday, rest-day, overtime, and night-differential stacking against the applicable DOLE rules for the payroll period.
8. Reconcile statutory totals and rounding at the monthly/remittance level.
9. Require a reviewed payroll result before approval/payment and retain the calculation input/output hashes already produced by the confidence layer.

## Official reference starting points

- SSS contribution schedules: https://www.sss.gov.ph/pay-contribution/
- SSS contribution table: https://www.sss.gov.ph/sss-contribution-table/
- BIR Form 1601-C compensation withholding fields: https://efps.bir.gov.ph/efps-war/forms/1601C/1601c_v3.xhtml

These URLs are reference provenance, not a substitute for maintaining effective-dated rule data in the application. Before a production payroll is approved, the organization should verify the applicable agency issuance and effective date for that payroll period.
