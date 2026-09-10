# Payroll completion scope

This document is the implementation checklist for the production payroll workflow.

## Core calculation
- Salary history and effective-dated pay
- Attendance, overtime, undertime, late and unpaid leave
- Holiday and night differential foundations
- SSS, PhilHealth, Pag-IBIG and BIR withholding foundations
- 13th-month and annualization foundations
- Regional wage-rate configuration and MWE foundation

## Remaining production workflow
- Payroll adjustments integrated into gross/tax/net calculations
- Employee loan schedules and automatic deductions
- Final-pay workflow for separated employees
- Complete year-end tax reconciliation and certificates
- Government remittance/export reports using current official agency layouts
- Bank payout export architecture
- Complete payroll review/approval/payment audit trail

## Definition of done
A payroll period is complete when it can be prepared from employee data and timekeeping, reviewed, adjusted, approved, paid, represented by a payslip, reconciled for statutory/tax obligations, and included in year-end/final-pay workflows without bypassing organization isolation or lifecycle locks.
