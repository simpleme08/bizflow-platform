from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction

from apps.attendance.models import AttendanceRecord

from .models import PayrollRecord


ZERO = Decimal('0.00')


class PhilippinePayrollRules:
    """Centralized 2025+ Philippine payroll rules."""

    SSS_EMPLOYEE_RATE = Decimal('0.05')
    SSS_EMPLOYER_RATE = Decimal('0.10')
    SSS_MIN_MSC = Decimal('5000.00')
    SSS_MAX_MSC = Decimal('35000.00')
    SSS_MSC_STEP = Decimal('500.00')
    SSS_EC_LOW = Decimal('10.00')
    SSS_EC_HIGH = Decimal('30.00')
    PHILHEALTH_RATE = Decimal('0.05')
    PHILHEALTH_MIN_BASE = Decimal('10000.00')
    PHILHEALTH_MAX_BASE = Decimal('100000.00')
    PAGIBIG_THRESHOLD = Decimal('1500.00')
    PAGIBIG_EMPLOYEE_RATE_LOW = Decimal('0.01')
    PAGIBIG_EMPLOYEE_RATE_HIGH = Decimal('0.02')
    PAGIBIG_EMPLOYER_RATE = Decimal('0.02')
    PAGIBIG_MAX_BASE = Decimal('5000.00')

    @staticmethod
    def money(value):
        return Decimal(value).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    @classmethod
    def monthly_msc(cls, monthly_basic):
        if monthly_basic <= cls.SSS_MIN_MSC:
            return cls.SSS_MIN_MSC
        msc = (monthly_basic / cls.SSS_MSC_STEP).to_integral_value(rounding='ROUND_CEILING') * cls.SSS_MSC_STEP
        return min(msc, cls.SSS_MAX_MSC)

    @classmethod
    def sss(cls, monthly_basic):
        msc = cls.monthly_msc(monthly_basic)
        employee = cls.money(msc * cls.SSS_EMPLOYEE_RATE)
        employer = cls.money(msc * cls.SSS_EMPLOYER_RATE)
        ec = cls.SSS_EC_LOW if msc <= Decimal('14500') else cls.SSS_EC_HIGH
        return employee, employer + ec

    @classmethod
    def philhealth(cls, monthly_basic):
        base = min(max(monthly_basic, cls.PHILHEALTH_MIN_BASE), cls.PHILHEALTH_MAX_BASE)
        total = cls.money(base * cls.PHILHEALTH_RATE)
        return cls.money(total / 2), cls.money(total / 2)

    @classmethod
    def pagibig(cls, monthly_basic):
        base = min(max(monthly_basic, ZERO), cls.PAGIBIG_MAX_BASE)
        rate = cls.PAGIBIG_EMPLOYEE_RATE_LOW if base <= cls.PAGIBIG_THRESHOLD else cls.PAGIBIG_EMPLOYEE_RATE_HIGH
        return cls.money(base * rate), cls.money(base * cls.PAGIBIG_EMPLOYER_RATE)

    @classmethod
    def statutory(cls, monthly_basic, periods_per_month=2):
        sss_ee, sss_er = cls.sss(monthly_basic)
        ph_ee, ph_er = cls.philhealth(monthly_basic)
        pi_ee, pi_er = cls.pagibig(monthly_basic)
        divisor = Decimal(periods_per_month)
        return {
            'sss_employee': cls.money(sss_ee / divisor),
            'sss_employer': cls.money(sss_er / divisor),
            'philhealth_employee': cls.money(ph_ee / divisor),
            'philhealth_employer': cls.money(ph_er / divisor),
            'pagibig_employee': cls.money(pi_ee / divisor),
            'pagibig_employer': cls.money(pi_er / divisor),
        }


class PhilippineWithholdingTax:
    """BIR Annex E withholding tables, effective January 1, 2023 onward."""

    SEMI_MONTHLY = (
        (Decimal('10417'), ZERO, Decimal('0'), Decimal('0')),
        (Decimal('16666'), ZERO, Decimal('10417'), Decimal('0.15')),
        (Decimal('33332'), Decimal('937.50'), Decimal('16667'), Decimal('0.20')),
        (Decimal('83332'), Decimal('4270.70'), Decimal('33333'), Decimal('0.25')),
        (Decimal('333332'), Decimal('16770.70'), Decimal('83333'), Decimal('0.30')),
        (None, Decimal('91770.70'), Decimal('333333'), Decimal('0.35')),
    )
    MONTHLY = (
        (Decimal('20833'), ZERO, Decimal('0'), Decimal('0')),
        (Decimal('33332'), ZERO, Decimal('20833'), Decimal('0.15')),
        (Decimal('66666'), Decimal('1875.00'), Decimal('33333'), Decimal('0.20')),
        (Decimal('166666'), Decimal('8541.80'), Decimal('66667'), Decimal('0.25')),
        (Decimal('666666'), Decimal('33541.80'), Decimal('166667'), Decimal('0.30')),
        (None, Decimal('183541.80'), Decimal('666667'), Decimal('0.35')),
    )

    @classmethod
    def calculate(cls, taxable_regular_compensation, frequency='SEMI_MONTHLY', minimum_wage_earner=False):
        taxable = max(Decimal(taxable_regular_compensation), ZERO)
        if minimum_wage_earner:
            return ZERO
        table = cls.MONTHLY if frequency == 'MONTHLY' else cls.SEMI_MONTHLY
        for upper, base_tax, threshold, rate in table:
            if upper is None or taxable <= upper:
                if rate == ZERO:
                    return ZERO
                return max(ZERO, PhilippinePayrollRules.money(base_tax + (taxable - threshold) * rate))
        return ZERO


class PayrollCalculator:
    WORKING_DAYS = Decimal('22')
    WORKING_HOURS = Decimal('8')
    OVERTIME_MULTIPLIER = Decimal('1.25')

    @classmethod
    def calculate(cls, employee, period, other_deductions=ZERO):
        if employee.organization_id != period.organization_id:
            raise ValueError('Employee and payroll period must belong to the same organization.')
        salary = getattr(employee, 'salary', None)
        if salary is None:
            raise ValueError('Employee salary is required before payroll can be calculated.')

        attendance = AttendanceRecord.objects.filter(
            employee=employee,
            employee__organization=period.organization,
            attendance_date__range=(period.start_date, period.end_date),
        )
        late_minutes = sum((record.late_minutes for record in attendance), 0)
        undertime_minutes = sum((record.undertime_minutes for record in attendance), 0)
        overtime_minutes = sum((record.overtime_minutes for record in attendance), 0)

        daily_rate = salary.basic_salary / cls.WORKING_DAYS
        hourly_rate = daily_rate / cls.WORKING_HOURS
        minute_rate = hourly_rate / Decimal('60')
        money = PhilippinePayrollRules.money
        is_monthly = period.frequency == period.Frequency.MONTHLY
        periods_per_month = 1 if is_monthly else 2
        basic_pay = money(salary.basic_salary if is_monthly else salary.basic_salary / Decimal('2'))
        overtime_pay = money(Decimal(overtime_minutes) / Decimal('60') * hourly_rate * cls.OVERTIME_MULTIPLIER)
        late_deduction = money(Decimal(late_minutes) * minute_rate)
        undertime_deduction = money(Decimal(undertime_minutes) * minute_rate)
        other_deductions = money(other_deductions)
        gross_pay = money(basic_pay + overtime_pay)

        statutory = PhilippinePayrollRules.statutory(salary.basic_salary, periods_per_month=periods_per_month)
        taxable_regular = money(basic_pay - statutory['sss_employee'] - statutory['philhealth_employee'] - statutory['pagibig_employee'])
        profile = getattr(employee, 'payroll_profile', None)
        withholding_tax = PhilippineWithholdingTax.calculate(
            taxable_regular,
            frequency=period.frequency,
            minimum_wage_earner=bool(profile and profile.minimum_wage_earner),
        )
        net_pay = money(
            gross_pay - late_deduction - undertime_deduction
            - statutory['sss_employee'] - statutory['philhealth_employee']
            - statutory['pagibig_employee'] - withholding_tax - other_deductions
        )
        return {
            'basic_pay': basic_pay,
            'overtime_pay': overtime_pay,
            'late_deduction': late_deduction,
            'undertime_deduction': undertime_deduction,
            'sss_employee': statutory['sss_employee'],
            'sss_employer': statutory['sss_employer'],
            'philhealth_employee': statutory['philhealth_employee'],
            'philhealth_employer': statutory['philhealth_employer'],
            'pagibig_employee': statutory['pagibig_employee'],
            'pagibig_employer': statutory['pagibig_employer'],
            'withholding_tax': withholding_tax,
            'other_deductions': other_deductions,
            'gross_pay': gross_pay,
            'net_pay': net_pay,
        }

    @classmethod
    @transaction.atomic
    def process_period(cls, period, organization):
        period = type(period).objects.select_for_update().get(pk=period.pk, organization=organization)
        if period.status in (period.Status.APPROVED, period.Status.PAID):
            raise ValueError('Approved or paid payroll periods are locked and cannot be recalculated.')
        employees = organization.employees.filter(is_active=True).select_related('salary', 'payroll_profile')
        processed = 0
        for employee in employees:
            if getattr(employee, 'salary', None) is None:
                continue
            values = cls.calculate(employee, period)
            PayrollRecord.objects.update_or_create(employee=employee, payroll_period=period, defaults=values)
            processed += 1
        period.status = period.Status.CALCULATED
        period.save(update_fields=('status', 'updated_at'))
        return processed
