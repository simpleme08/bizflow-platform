from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction

from .loan_models import EmployeeLoan
from .models import PayrollAdjustment, PayrollRecord
from .services import PhilippineWithholdingTax

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
    """Apply the already-deducted installment to active loans atomically."""
    with transaction.atomic():
        total = ZERO
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
        if remaining > ZERO:
            raise ValueError('Loan deductions exceed the active loan balances available for settlement.')
        return money(total)


def apply_record_adjustments(record):
    """Apply approved, unapplied draft adjustments exactly once."""
    with transaction.atomic():
        record = PayrollRecord.objects.select_for_update().select_related('employee', 'payroll_period').get(pk=record.pk)
        if record.status != PayrollRecord.Status.DRAFT:
            raise ValueError('Only draft payroll records can be adjusted.')

        adjustments = list(record.adjustments.select_for_update().filter(approved=True, applied=False))
        if not adjustments:
            record.loan_deductions = loan_deduction_for_record(record)
            record.save()
            return record

        earnings = sum((a.amount for a in adjustments if a.kind == PayrollAdjustment.Kind.EARNING), ZERO)
        deductions = sum((a.amount for a in adjustments if a.kind == PayrollAdjustment.Kind.DEDUCTION), ZERO)
        taxable_earnings = sum((a.amount for a in adjustments if a.kind == PayrollAdjustment.Kind.EARNING and a.taxable), ZERO)
        original_taxable = money(
            record.basic_pay
            + record.allowances
            + record.commissions
            + record.bonuses
            + record.overtime_pay
            + record.holiday_pay
            + record.night_differential
            - record.statutory_deductions
        )
        original_tax = record.withholding_tax
        new_tax = PhilippineWithholdingTax.calculate(original_taxable + taxable_earnings, record.payroll_period.frequency)
        incremental_tax = max(ZERO, money(new_tax - original_tax))

        record.loan_deductions = loan_deduction_for_record(record)
        record.taxable_supplementary = money(record.taxable_supplementary + taxable_earnings)
        record.gross_pay = money(record.gross_pay + earnings)
        record.withholding_tax = money(original_tax + incremental_tax)
        record.other_deductions = money(record.other_deductions + deductions)
        record.net_pay = money(record.gross_pay - record.total_deductions)
        if record.net_pay < ZERO:
            raise ValueError('Adjustments would result in negative net pay.')
        record.save()

        for adjustment in adjustments:
            adjustment.applied = True
            adjustment.save(update_fields=('applied', 'updated_at'))

    return record


def final_pay_preview(employee, separation_date, basic_salary, worked_days, thirteenth_month=ZERO, accrued_leave_pay=ZERO, other_earnings=ZERO, other_deductions=ZERO, loan_balance=ZERO):
    """Calculate a transparent final-pay preview using explicitly supplied worked days.

    The function deliberately does not infer payable days from the separation date.
    Final-pay proration depends on the employer's payroll calendar and actual payable
    days, so the caller must provide the validated number of worked/payable days.
    """
    salary = Decimal(basic_salary)
    payable_days = Decimal(worked_days)
    if salary < ZERO:
        raise ValueError('Basic salary cannot be negative.')
    if payable_days < ZERO or payable_days > Decimal('31'):
        raise ValueError('Worked days must be between 0 and 31.')
    values = [thirteenth_month, accrued_leave_pay, other_earnings, other_deductions, loan_balance]
    if any(Decimal(value) < ZERO for value in values):
        raise ValueError('Final-pay amounts cannot be negative.')
    day_rate = salary / Decimal('22')
    prorated_salary = money(day_rate * payable_days)
    thirteenth = money(thirteenth_month)
    earnings = money(prorated_salary + Decimal(accrued_leave_pay) + Decimal(other_earnings) + thirteenth)
    deductions = money(Decimal(other_deductions) + Decimal(loan_balance))
    net = money(earnings - deductions)
    if net < ZERO:
        raise ValueError('Final pay would result in negative net pay.')
    return {
        'worked_days': payable_days,
        'prorated_salary': prorated_salary,
        'accrued_leave_pay': money(accrued_leave_pay),
        'other_earnings': money(other_earnings),
        'thirteenth_month': thirteenth,
        'loan_balance': money(loan_balance),
        'other_deductions': money(other_deductions),
        'gross_final_pay': earnings,
        'net_final_pay': net,
    }
