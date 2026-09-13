from django.db.models import Q

from apps.attendance.models import AttendanceRecord
from apps.employees.models import Employee

from .models import PayrollWageRate


class PayrollConfidenceEngine:
    """Operational safety gate for payroll source data and reconciliation."""

    READY = 'READY'
    REVIEW = 'REVIEW'
    BLOCKED = 'BLOCKED'

    @classmethod
    def preflight(cls, period, organization):
        employees = Employee.objects.filter(organization=organization, is_active=True).select_related('payroll_profile', 'salary')
        errors = []
        warnings = []

        if period.organization_id != organization.id:
            return {'ok': False, 'status': cls.BLOCKED, 'checks': [], 'errors': ['Payroll period belongs to another organization.'], 'warnings': []}

        for employee in employees:
            salary = employee.salary_history.filter(effective_date__lte=period.end_date).order_by('-effective_date').first() or getattr(employee, 'salary', None)
            if salary is None:
                errors.append(f'{employee.employee_number}: salary is missing.')
                continue

            profile = getattr(employee, 'payroll_profile', None)
            if profile is None:
                warnings.append(f'{employee.employee_number}: payroll profile is missing; statutory and tax classifications require review.')
            elif profile.minimum_wage_earner:
                if not profile.wage_region or not profile.wage_category:
                    errors.append(f'{employee.employee_number}: minimum-wage earner requires wage region and category.')
                else:
                    wage_rate = PayrollWageRate.objects.filter(
                        is_active=True,
                        region_code__iexact=profile.wage_region,
                        category=profile.wage_category,
                        effective_from__lte=period.end_date,
                    ).filter(Q(effective_to__isnull=True) | Q(effective_to__gte=period.end_date)).filter(
                        Q(organization=organization) | Q(organization__isnull=True)
                    ).order_by('-effective_from', '-created_at').first()
                    if wage_rate is None:
                        errors.append(f'{employee.employee_number}: no effective wage rate exists for {profile.wage_region}/{profile.wage_category}.')

            attendance = AttendanceRecord.objects.filter(employee=employee, attendance_date__range=(period.start_date, period.end_date))
            for record in attendance:
                if record.time_in and not record.time_out:
                    errors.append(f'{employee.employee_number} {record.attendance_date}: open attendance punch must be resolved.')
                if record.clock_in_mode in (AttendanceRecord.ClockInMode.COVER, AttendanceRecord.ClockInMode.UNSCHEDULED):
                    warnings.append(f'{employee.employee_number} {record.attendance_date}: {record.clock_in_mode.lower()} punch requires schedule reconciliation.')
                if record.status == AttendanceRecord.Status.ABSENT:
                    warnings.append(f'{employee.employee_number} {record.attendance_date}: ABSENT record requires payroll treatment review; it is not automatically unpaid.')

        checks = [
            {'name': 'Employee salary', 'status': 'PASS' if not any('salary is missing' in x for x in errors) else 'FAIL'},
            {'name': 'Payroll profile / statutory classification', 'status': 'REVIEW' if any('payroll profile' in x for x in warnings) else 'PASS'},
            {'name': 'Wage-rate coverage', 'status': 'FAIL' if any('wage rate' in x for x in errors) else 'PASS'},
            {'name': 'Attendance reconciliation', 'status': 'REVIEW' if any('attendance' in x.lower() or 'punch' in x.lower() for x in warnings + errors) else 'PASS'},
        ]
        status = cls.BLOCKED if errors else (cls.REVIEW if warnings else cls.READY)
        return {'ok': status != cls.BLOCKED, 'status': status, 'checks': checks, 'errors': errors, 'warnings': warnings, 'employee_count': employees.count()}
