from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction

from .loan_models import EmployeeLoan
from .models import PayrollAdjustment, PayrollRecord
from .services import PhilippinePayrollRules, PhilippineWithholdingTax

ZERO = Decimal('0.00')


def money(value):
    return Decimal(value).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def loan_deduction_for_record(record):
    """Return scheduled loan deductions without changing loan balances."""
    loans = EmployeeLoan.objects.filter(
        employee=record.employee,
        status=EmployeeLoan.Status.ACTIVE,
        start_date__lte=record.payroll_period.end_date,
        end_date__gte=record.payroll_period.start_date,
    )
    total = ZERO
    for loan in loans:
        total += min(loan.installment_amount, loan.balance)
    return money(total)


def settle_loans_for_record(record):
    """Apply the already-deducted installment to active loans after payment."""
    total = ZERO
    with transaction.atomic():
        loans = EmployeeLoan.objects.select_for_update().filter(
            employee=record.employee,
            status=EmployeeLoan.Status.ACTIVE,
            start_date__lte=record.payroll_period.end_date,
            end_date__gte=record.payroll_period.start_date,
        ).order_by('start_date', 'created_at')
        remaining = money(record.loan_deductions)
        for loan in loans:
            if remaining <= ZERO:
                break
            deduction = min(loan.installment_amount, loan.balance, remaining)
            loan.balance = money(loan.balance - deduction)
            if loan.balance == ZERO:
                loan.status = EmployeeLoan.Status.PAID
            loan.save(update_fields=('balance', 'status', 'updated_at'))
            remaining -= deduction
            total += deduction
    return money(total)


def apply_record_adjustments(record):
    """Apply approved draft adjustments to a payroll record before approval.

    This deliberately recalculates only the incremental withholding caused by
    taxable earnings; statutory deductions are not silently altered by an
    adjustment because those rules require the full period/month context.
    """
    if record.status != PayrollRecord.Status.DRAFT:
        raise ValueError('Only draft payroll records can be adjusted.')
    adjustments = list(record.adjustments.filter(approved=True))
    earnings = sum((a.amount for a in adjustments if a.kind == PayrollAdjustment.Kind.EARNING), ZERO)
    deductions = sum((a.amount for a in adjustments if a.kind == PayrollAdjustment.Kind.DEDUCTION), ZERO)
    taxable_earnings = sum((a.amount for a in adjustments if a.kind == PayrollAdjustment.Kind.EARNING and a.taxable), ZERO)
    original_taxable = money(record.basic_pay + record.allowances + record.commissions + record.bonuses + record.overtime_pay + record.holiday_pay + record.night_differential - record.statutory_deductions)
    original_tax = record.withholding_tax
    new_tax = PhilippineWithholdingTax.calculate(original_taxable + taxable_earnings, record.payroll_period.frequency)
    incremental_tax = max(ZERO, money(new_tax - original_tax))
    loan_due = loan_deduction_for_record(record)
    record.loan_deductions = loan_due
    record.taxable_supplementary = money(record.taxable_supplementary + taxable_earnings)
    record.gross_pay = money(record.gross_pay + earnings)
    record.withholding_tax = money(original_tax + incremental_tax)
    record.net_pay = money(record.gross_pay - record.total_deductions - deductions)
    if record.net_pay < ZERO:
        raise ValueError('Adjustments would result in negative net pay.')
    record.other_deductions = money(record.other_deductions + deductions)
    record.net_pay = money(record.gross_pay - record.total_deductions)
    record.save()
    return record


def final_pay_preview(employee, separation_date, basic_salary, thirteenth_month=ZERO, accrued_leave_pay=ZERO, other_earnings=ZERO, other_deductions=ZERO, loan_balance=ZERO):
    """Calculate a transparent final-pay preview; does not mutate employee/payroll data."""
    salary = Decimal(basic_salary)
    day_rate = salary / Decimal('22')
    days_in_period = Decimal(separation_date.day)
    prorated_salary = money(day_rate * days_in_period)
    thirteenth = money(thirteenth_month)
    earnings = money(prorated_salary + Decimal(accrued_leave_pay) + Decimal(other_earnings) + thirteenth)
    deductions = money(Decimal(other_deductions) + Decimal(loan_balance))
    net = money(earnings - deductions)
    if net < ZERO:
        raise ValueError('Final pay would result in negative net pay.')
    return {
        'prorated_salary': prorated_salary,
        'accrued_leave_pay': money(accrued_leave_pay),
        'other_earnings': money(other_earnings),
        'thirteenth_month': thirteenth,
        'loan_balance': money(loan_balance),
        'other_deductions': money(other_deductions),
        'gross_final_pay': earnings,
        'net_final_pay': net,
    }
