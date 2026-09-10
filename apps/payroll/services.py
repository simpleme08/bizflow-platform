from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction

from apps.attendance.models import AttendanceRecord

from .models import PayrollRecord


class PayrollCalculator:
    WORKING_DAYS = Decimal('22')
    WORKING_HOURS = Decimal('8')
    OVERTIME_MULTIPLIER = Decimal('1.25')

    @classmethod
    def calculate(cls, employee, period, other_deductions=Decimal('0.00')):
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
        money = lambda value: value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        basic_pay = money(salary.basic_salary / Decimal('2'))
        overtime_pay = money(Decimal(overtime_minutes) / Decimal('60') * hourly_rate * cls.OVERTIME_MULTIPLIER)
        late_deduction = money(Decimal(late_minutes) * minute_rate)
        undertime_deduction = money(Decimal(undertime_minutes) * minute_rate)
        other_deductions = money(Decimal(other_deductions))
        gross_pay = money(basic_pay + overtime_pay)
        return {
            'basic_pay': basic_pay,
            'overtime_pay': overtime_pay,
            'late_deduction': late_deduction,
            'undertime_deduction': undertime_deduction,
            'other_deductions': other_deductions,
            'gross_pay': gross_pay,
            'net_pay': money(gross_pay - late_deduction - undertime_deduction - other_deductions),
        }

    @classmethod
    @transaction.atomic
    def process_period(cls, period, organization):
        period = type(period).objects.select_for_update().get(
            pk=period.pk,
            organization=organization,
        )
        if period.status in (period.Status.APPROVED, period.Status.PAID):
            raise ValueError('Approved or paid payroll periods are locked and cannot be recalculated.')

        employees = organization.employees.filter(is_active=True).select_related('salary')
        processed = 0
        for employee in employees:
            salary = getattr(employee, 'salary', None)
            if salary is None:
                continue
            values = cls.calculate(employee, period)
            PayrollRecord.objects.update_or_create(
                employee=employee,
                payroll_period=period,
                defaults=values,
            )
            processed += 1

        period.status = period.Status.CALCULATED
        period.save(update_fields=('status', 'updated_at'))
        return processed
