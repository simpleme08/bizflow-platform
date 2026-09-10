from datetime import datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.utils import timezone

from apps.attendance.models import AttendanceRecord
from apps.leave.models import LeaveApplication

from .models import PayrollHoliday, PayrollRecord

ZERO = Decimal('0.00')


class PhilippinePayrollRules:
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
    THIRTEENTH_MONTH_EXEMPTION = Decimal('90000.00')
    NIGHT_SHIFT_START = time(22, 0)
    NIGHT_SHIFT_END = time(6, 0)
    NIGHT_DIFFERENTIAL_RATE = Decimal('0.10')

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
        return {key: cls.money(value / divisor) for key, value in {
            'sss_employee': sss_ee, 'sss_employer': sss_er,
            'philhealth_employee': ph_ee, 'philhealth_employer': ph_er,
            'pagibig_employee': pi_ee, 'pagibig_employer': pi_er,
        }.items()}


class PhilippineWithholdingTax:
    SEMI_MONTHLY = (
        (Decimal('10417'), ZERO, Decimal('10417'), Decimal('0')),
        (Decimal('16666'), ZERO, Decimal('10417'), Decimal('.15')),
        (Decimal('33332'), Decimal('937.50'), Decimal('16667'), Decimal('.20')),
        (Decimal('83332'), Decimal('4270.70'), Decimal('33333'), Decimal('.25')),
        (Decimal('333332'), Decimal('16770.70'), Decimal('83333'), Decimal('.30')),
        (None, Decimal('91770.70'), Decimal('333333'), Decimal('.35')),
    )
    MONTHLY = (
        (Decimal('20833'), ZERO, Decimal('20833'), Decimal('0')),
        (Decimal('33332'), ZERO, Decimal('20833'), Decimal('.15')),
        (Decimal('66666'), Decimal('1875.00'), Decimal('33333'), Decimal('.20')),
        (Decimal('166666'), Decimal('8541.80'), Decimal('66667'), Decimal('.25')),
        (Decimal('666666'), Decimal('33541.80'), Decimal('166667'), Decimal('.30')),
        (None, Decimal('183541.80'), Decimal('666667'), Decimal('.35')),
    )
    ANNUAL = (
        (Decimal('250000'), ZERO, Decimal('250000'), Decimal('0')),
        (Decimal('400000'), ZERO, Decimal('250000'), Decimal('.15')),
        (Decimal('800000'), Decimal('22500.00'), Decimal('400000'), Decimal('.20')),
        (Decimal('2000000'), Decimal('102500.00'), Decimal('800000'), Decimal('.25')),
        (Decimal('8000000'), Decimal('402500.00'), Decimal('2000000'), Decimal('.30')),
        (None, Decimal('2202500.00'), Decimal('8000000'), Decimal('.35')),
    )

    @classmethod
    def _calculate_table(cls, taxable_compensation, table):
        taxable = max(Decimal(taxable_compensation), ZERO)
        for upper, base_tax, threshold, rate in table:
            if upper is None or taxable <= upper:
                if rate == ZERO:
                    return ZERO
                return max(ZERO, PhilippinePayrollRules.money(base_tax + (taxable - threshold) * rate))
        return ZERO

    @classmethod
    def calculate(cls, taxable_compensation, frequency='SEMI_MONTHLY', minimum_wage_earner=False):
        if minimum_wage_earner:
            return ZERO
        table = cls.MONTHLY if frequency == 'MONTHLY' else cls.SEMI_MONTHLY
        return cls._calculate_table(taxable_compensation, table)

    @classmethod
    def annual_tax(cls, taxable_compensation):
        return cls._calculate_table(taxable_compensation, cls.ANNUAL)


class PayrollCalculator:
    WORKING_DAYS = Decimal('22')
    WORKING_HOURS = Decimal('8')
    OVERTIME_MULTIPLIER = Decimal('1.25')

    @classmethod
    def periods_per_month(cls, period):
        return 1 if period.frequency == period.Frequency.MONTHLY else 2

    @staticmethod
    def _night_hours(time_in, time_out):
        if not time_in or not time_out or time_out <= time_in:
            return Decimal('0')
        start = timezone.localtime(time_in)
        end = timezone.localtime(time_out)
        total_seconds = Decimal('0')
        day = start.date() - timedelta(days=1)
        last_day = end.date()
        while day <= last_day:
            window_start = timezone.make_aware(datetime.combine(day, PhilippinePayrollRules.NIGHT_SHIFT_START), timezone.get_current_timezone())
            window_end = timezone.make_aware(datetime.combine(day + timedelta(days=1), PhilippinePayrollRules.NIGHT_SHIFT_END), timezone.get_current_timezone())
            overlap_start = max(start, window_start)
            overlap_end = min(end, window_end)
            if overlap_end > overlap_start:
                total_seconds += Decimal((overlap_end - overlap_start).total_seconds())
            day += timedelta(days=1)
        return total_seconds / Decimal('3600')

    @classmethod
    def _holiday_premium(cls, attendance, daily_rate):
        holiday = PayrollHoliday.objects.filter(holiday_date=attendance.attendance_date, is_active=True, organization=attendance.employee.organization).first()
        if holiday is None:
            holiday = PayrollHoliday.objects.filter(holiday_date=attendance.attendance_date, organization__isnull=True, is_active=True).first()
        if holiday is None or holiday.kind == PayrollHoliday.Kind.SPECIAL_WORKING or not attendance.time_in or not attendance.time_out:
            return ZERO
        if holiday.kind == PayrollHoliday.Kind.REGULAR:
            premium_multiplier = Decimal('2.00') if holiday.is_double else Decimal('1.00')
        else:
            premium_multiplier = Decimal('0.50') if holiday.is_double else Decimal('0.30')
        return cls_money(daily_rate * premium_multiplier)

    @classmethod
    def _unpaid_leave(cls, employee, period, daily_rate):
        applications = LeaveApplication.objects.filter(employee=employee, status=LeaveApplication.Status.APPROVED, leave_type__is_paid=False, start_date__lte=period.end_date, end_date__gte=period.start_date)
        total_days = sum((application.total_days for application in applications), ZERO)
        return cls_money(total_days * daily_rate)

    @classmethod
    def _taxable_thirteenth_for_period(cls, employee, period, thirteenth_month):
        if not thirteenth_month:
            return ZERO
        prior = PayrollRecord.objects.filter(
            employee=employee,
            payroll_period__end_date__year=period.end_date.year,
            payroll_period__end_date__lt=period.end_date,
        ).aggregate_total_thirteenth_month()
        cumulative = prior + thirteenth_month
        exempt_used = min(prior, PhilippinePayrollRules.THIRTEENTH_MONTH_EXEMPTION)
        exempt_after = min(cumulative, PhilippinePayrollRules.THIRTEENTH_MONTH_EXEMPTION)
        return PhilippinePayrollRules.money(max(ZERO, cumulative - exempt_after + exempt_used))

    @classmethod
    def calculate(cls, employee, period, other_deductions=ZERO, leave_without_pay=None, loan_deductions=ZERO, allowances=ZERO, commissions=ZERO, bonuses=ZERO, holiday_pay=None, night_differential=None, thirteenth_month=ZERO):
        if employee.organization_id != period.organization_id:
            raise ValueError('Employee and payroll period must belong to the same organization.')
        salary = getattr(employee, 'salary', None)
        if salary is None:
            raise ValueError('Employee salary is required before payroll can be calculated.')
        attendance = AttendanceRecord.objects.filter(employee=employee, employee__organization=period.organization, attendance_date__range=(period.start_date, period.end_date))
        late_minutes = sum((record.late_minutes for record in attendance), 0)
        undertime_minutes = sum((record.undertime_minutes for record in attendance), 0)
        overtime_minutes = sum((record.overtime_minutes for record in attendance), 0)
        daily_rate = salary.basic_salary / cls.WORKING_DAYS
        hourly_rate = daily_rate / cls.WORKING_HOURS
        minute_rate = hourly_rate / Decimal('60')
        money = PhilippinePayrollRules.money
        periods = cls.periods_per_month(period)
        basic_pay = money(salary.basic_salary / Decimal(periods))
        overtime_pay = money(Decimal(overtime_minutes) / Decimal('60') * hourly_rate * cls.OVERTIME_MULTIPLIER)
        late_deduction = money(Decimal(late_minutes) * minute_rate)
        undertime_deduction = money(Decimal(undertime_minutes) * minute_rate)
        leave_without_pay = cls._unpaid_leave(employee, period, daily_rate) if leave_without_pay is None else money(leave_without_pay)
        loan_deductions = money(loan_deductions)
        other_deductions = money(other_deductions)
        allowances, commissions, bonuses = map(money, (allowances, commissions, bonuses))
        calculated_holiday = sum((cls._holiday_premium(record, daily_rate) for record in attendance), ZERO)
        holiday_pay = calculated_holiday if holiday_pay is None else money(holiday_pay)
        calculated_night = sum((money(cls._night_hours(record.time_in, record.time_out) * hourly_rate * PhilippinePayrollRules.NIGHT_DIFFERENTIAL_RATE) for record in attendance), ZERO)
        night_differential = calculated_night if night_differential is None else money(night_differential)
        thirteenth_month = money(thirteenth_month)
        gross_pay = money(basic_pay + overtime_pay + holiday_pay + night_differential + allowances + commissions + bonuses + thirteenth_month)
        statutory = PhilippinePayrollRules.statutory(salary.basic_salary, periods_per_month=periods)
        taxable_regular = money(basic_pay + allowances - statutory['sss_employee'] - statutory['philhealth_employee'] - statutory['pagibig_employee'])
        taxable_supplementary = money(commissions + bonuses + overtime_pay + holiday_pay + night_differential + cls._taxable_thirteenth_for_period(employee, period, thirteenth_month))
        withholding_tax = PhilippineWithholdingTax.calculate(taxable_regular + taxable_supplementary, period.frequency, bool(getattr(getattr(employee, 'payroll_profile', None), 'minimum_wage_earner', False)))
        net_pay = money(gross_pay - late_deduction - undertime_deduction - leave_without_pay - loan_deductions - statutory['sss_employee'] - statutory['philhealth_employee'] - statutory['pagibig_employee'] - withholding_tax - other_deductions)
        if net_pay < ZERO:
            raise ValueError('Payroll would result in negative net pay; review deductions.')
        return {
            'basic_pay': basic_pay, 'overtime_pay': overtime_pay, 'holiday_pay': holiday_pay, 'night_differential': night_differential,
            'allowances': allowances, 'commissions': commissions, 'bonuses': bonuses, 'taxable_supplementary': taxable_supplementary,
            'thirteenth_month': thirteenth_month, 'late_deduction': late_deduction, 'undertime_deduction': undertime_deduction,
            'leave_without_pay': leave_without_pay, 'loan_deductions': loan_deductions, 'other_deductions': other_deductions,
            'sss_employee': statutory['sss_employee'], 'sss_employer': statutory['sss_employer'],
            'philhealth_employee': statutory['philhealth_employee'], 'philhealth_employer': statutory['philhealth_employer'],
            'pagibig_employee': statutory['pagibig_employee'], 'pagibig_employer': statutory['pagibig_employer'],
            'withholding_tax': withholding_tax, 'gross_pay': gross_pay, 'net_pay': net_pay,
        }

    @classmethod
    def thirteenth_month(cls, employee, year):
        records = PayrollRecord.objects.filter(employee=employee, payroll_period__end_date__year=year)
        basic = sum((record.basic_pay for record in records), ZERO)
        return PhilippinePayrollRules.money(basic / Decimal('12'))

    @classmethod
    def annual_tax_reconciliation(cls, employee, year):
        records = PayrollRecord.objects.filter(employee=employee, payroll_period__end_date__year=year).order_by('payroll_period__end_date')
        records_values = records.values(
            'basic_pay', 'allowances', 'commissions', 'bonuses', 'overtime_pay',
            'holiday_pay', 'night_differential', 'thirteenth_month',
            'sss_employee', 'philhealth_employee', 'pagibig_employee',
        )
        regular_and_supplementary = sum((
            row['basic_pay'] + row['allowances'] + row['commissions'] + row['bonuses'] +
            row['overtime_pay'] + row['holiday_pay'] + row['night_differential'] -
            row['sss_employee'] - row['philhealth_employee'] - row['pagibig_employee']
            for row in records_values
        ), ZERO)
        total_thirteenth_month = sum((row['thirteenth_month'] for row in records_values), ZERO)
        taxable_thirteenth_month = max(ZERO, total_thirteenth_month - PhilippinePayrollRules.THIRTEENTH_MONTH_EXEMPTION)
        taxable_income = PhilippinePayrollRules.money(regular_and_supplementary + taxable_thirteenth_month)
        tax_due = PhilippineWithholdingTax.annual_tax(taxable_income)
        tax_withheld = PhilippinePayrollRules.money(sum((record.withholding_tax for record in records), ZERO))
        adjustment = PhilippinePayrollRules.money(tax_due - tax_withheld)
        return {
            'year': year,
            'taxable_income': taxable_income,
            'taxable_thirteenth_month': PhilippinePayrollRules.money(taxable_thirteenth_month),
            'tax_due': tax_due,
            'tax_withheld': tax_withheld,
            'adjustment': adjustment,
        }

    @classmethod
    def preflight(cls, period, organization):
        errors, warnings = [], []
        employees = organization.employees.filter(is_active=True).select_related('salary', 'payroll_profile')
        for employee in employees:
            if getattr(employee, 'salary', None) is None:
                errors.append(f'{employee.employee_number}: missing salary')
                continue
            profile = getattr(employee, 'payroll_profile', None)
            if profile is None:
                warnings.append(f'{employee.employee_number}: payroll profile is missing')
            else:
                for field, label in (('sss_number', 'SSS'), ('philhealth_number', 'PhilHealth'), ('pagibig_number', 'Pag-IBIG'), ('tin', 'TIN')):
                    if not getattr(profile, field):
                        warnings.append(f'{employee.employee_number}: missing {label} number')
            try:
                cls.calculate(employee, period)
            except ValueError as exc:
                errors.append(f'{employee.employee_number}: {exc}')
        return {'ok': not errors, 'errors': errors, 'warnings': warnings, 'employee_count': employees.count()}

    @classmethod
    @transaction.atomic
    def process_period(cls, period, organization):
        period = type(period).objects.select_for_update().get(pk=period.pk, organization=organization)
        if period.status in (period.Status.APPROVED, period.Status.PAID):
            raise ValueError('Approved or paid payroll periods are locked and cannot be recalculated.')
        check = cls.preflight(period, organization)
        if not check['ok']:
            raise ValueError('Payroll preflight failed: ' + '; '.join(check['errors']))
        employees = organization.employees.filter(is_active=True).select_related('salary', 'payroll_profile')
        processed = 0
        for employee in employees:
            values = cls.calculate(employee, period)
            PayrollRecord.objects.update_or_create(employee=employee, payroll_period=period, defaults=values)
            processed += 1
        period.status = period.Status.CALCULATED
        period.save(update_fields=('status', 'updated_at'))
        return processed


def cls_money(value):
    return PhilippinePayrollRules.money(value)
