# Payroll and Philippine compliance guide

## Scope

The payroll module provides payroll-period processing, employee salary/wage data, attendance-related inputs, adjustments, loans, final-pay workflow, approval controls, payslip generation and reporting/remittance exports.

## Payroll lifecycle

1. Maintain employee employment and salary data.
2. Configure the payroll period and applicable effective-dated wage/statutory inputs.
3. Review attendance, leave and adjustments.
4. Run payroll processing.
5. Review draft records and exceptions.
6. Approve records through the authorized workflow.
7. Mark paid when payment has actually occurred.
8. Provide employees their approved/paid payslips.
9. Generate reporting/remittance exports and perform the organization's filing/payment process.

## Controls

- Payroll periods are organization-scoped.
- Period dates must be valid and overlapping periods are rejected by payroll validation.
- Payroll records retain approval/payment state and controlled financial fields.
- Adjustments have approval/application state and idempotent application behavior.
- Loans track balances and settlement state.
- Final-pay preview supports separation workflows.
- Payslips are generated from the authorized payroll record and are tenant/employee scoped.

## Philippine rules

The codebase contains a Philippine compliance foundation for statutory contributions, withholding-tax handling and premium/holiday/night-differential concepts. These rules must be maintained with effective dates and verified against current official sources before a production payroll run.

Do not treat a hard-coded rate in documentation as permanently current. SSS, PhilHealth, Pag-IBIG, BIR, DOLE/NWPC and regional wage rules can change.

## Wage rates

Minimum-wage rules are regional and effective-date specific. The system must not assume a single nationwide minimum wage. Production configuration should identify the employee's applicable region and effective period and should be reviewed by payroll/HR personnel.

## Remittance exports

The payroll module provides organization/period reporting exports for SSS, PhilHealth, Pag-IBIG and BIR-related calculations. These exports are reporting aids unless the implementation explicitly matches the current agency submission specification. Filing, payment and government portal submission remain operational responsibilities until a verified integration exists.

## Payroll review checklist

Before approval:

- employee status and assignment are correct
- salary and effective dates are correct
- attendance exceptions are resolved
- leave deductions/credits are correct
- approved adjustments are intentional
- loan deductions and remaining balances reconcile
- statutory deductions are reviewed
- tax/withholding treatment is reviewed
- gross-to-net totals reconcile
- final-pay cases are separately reviewed
- output is suitable for the organization's filing/payment process

## Legal/compliance boundary

This application is software, not a payroll law firm, tax adviser, or government filing service. Customers remain responsible for confirming the rules applicable to their workforce and payroll period. Obtain qualified Philippine payroll, tax, employment and privacy review before production use.
