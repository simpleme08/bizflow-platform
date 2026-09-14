from datetime import date, datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.attendance.models import AttendanceRecord
from apps.employees.models import Employee, EmployeeAssignment
from apps.organization.models import Organization, OrganizationMembership
from apps.payroll.models import EmployeeSalary, PayrollHoliday, PayrollPeriod, PayrollRecord
from apps.workforce.models import ShiftTemplate


class Command(BaseCommand):
    help = 'Seed deterministic BizFlow demo employees, August 2026 attendance, holidays, and draft payroll records.'

    DEMO_ORG_NAME = 'BizFlow Demo Company'
    DEMO_ORG_SLUG = 'bizflow-demo'
    START = date(2026, 8, 16)
    END = date(2026, 8, 31)
    HOLIDAYS = {
        date(2026, 8, 21): ('Ninoy Aquino Day', PayrollHoliday.Kind.SPECIAL_NON_WORKING, False),
        date(2026, 8, 31): ('National Heroes Day', PayrollHoliday.Kind.REGULAR, False),
    }
    EMPLOYEES = [
        ('DEMO-001', 'Demo', 'Normal', 22000),
        ('DEMO-002', 'Demo', 'Late', 24000),
        ('DEMO-003', 'Demo', 'Overtime', 26000),
        ('DEMO-004', 'Demo', 'Leave', 21000),
        ('DEMO-005', 'Demo', 'Special Holiday', 23000),
        ('DEMO-006', 'Demo', 'Regular Holiday', 25000),
    ]

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true', help='Delete existing demo attendance/payroll data before reseeding.')

    def aware(self, day, hour, minute=0):
        return timezone.make_aware(datetime.combine(day, time(hour, minute)), timezone.get_current_timezone())

    @transaction.atomic
    def handle(self, *args, **options):
        org, _ = Organization.objects.get_or_create(slug=self.DEMO_ORG_SLUG, defaults={'name': self.DEMO_ORG_NAME})
        org.name = self.DEMO_ORG_NAME
        org.is_active = True
        org.save(update_fields=('name', 'is_active', 'updated_at'))

        User = get_user_model()
        manager, _ = User.objects.get_or_create(username='demo-manager', defaults={'is_active': True})
        manager.is_active = True
        manager.set_unusable_password()
        manager.save(update_fields=('is_active', 'password'))
        OrganizationMembership.objects.update_or_create(
            organization=org, user=manager,
            defaults={'role': OrganizationMembership.Role.OWNER, 'is_active': True},
        )

        day_shift, _ = ShiftTemplate.objects.get_or_create(
            organization=org,
            name='Demo Day Shift',
            defaults={'start_time': time(8), 'end_time': time(17)},
        )

        if options['reset']:
            AttendanceRecord.objects.filter(employee__organization=org, attendance_date__range=(self.START, self.END)).delete()
            PayrollRecord.objects.filter(payroll_period__organization=org, payroll_period__start_date=self.START, payroll_period__end_date=self.END).delete()
            PayrollPeriod.objects.filter(organization=org, start_date=self.START, end_date=self.END).delete()

        for holiday_date, (name, kind, is_double) in self.HOLIDAYS.items():
            PayrollHoliday.objects.update_or_create(
                organization=org,
                holiday_date=holiday_date,
                defaults={'name': name, 'kind': kind, 'is_double': is_double, 'is_active': True},
            )

        employees = {}
        for number, first_name, last_name, salary in self.EMPLOYEES:
            username = f'demo-{number.lower()}'
            user, _ = User.objects.get_or_create(username=username, defaults={'is_active': True})
            user.is_active = True
            user.set_unusable_password()
            user.save(update_fields=('is_active', 'password'))
            OrganizationMembership.objects.update_or_create(
                organization=org, user=user,
                defaults={'role': OrganizationMembership.Role.EMPLOYEE, 'is_active': True},
            )
            employee, _ = Employee.objects.update_or_create(
                employee_number=number,
                defaults={
                    'user': user, 'organization': org, 'first_name': first_name, 'last_name': last_name,
                    'status': Employee.Status.REGULAR, 'is_active': True, 'hire_date': date(2025, 1, 1),
                },
            )
            EmployeeSalary.objects.update_or_create(
                employee=employee,
                defaults={'basic_salary': salary, 'effective_date': date(2026, 1, 1)},
            )
            EmployeeAssignment.objects.update_or_create(
                employee=employee, shift_template=day_shift, start_date=date(2026, 1, 1),
                defaults={'end_date': None, 'is_primary': True},
            )
            employees[number] = employee

        period, _ = PayrollPeriod.objects.update_or_create(
            organization=org, start_date=self.START, end_date=self.END,
            defaults={
                'name': 'Demo August 16-31, 2026',
                'frequency': PayrollPeriod.Frequency.SEMI_MONTHLY,
                'status': PayrollPeriod.Status.OPEN,
                'confidence_status': 'REVIEW',
                'confidence_summary': {'demo_seed': True, 'note': 'Demo payroll records are intentionally DRAFT and unapproved.'},
            },
        )

        for employee in employees.values():
            PayrollRecord.objects.update_or_create(
                employee=employee,
                payroll_period=period,
                defaults={
                    'status': PayrollRecord.Status.DRAFT,
                    'basic_pay': 0,
                    'gross_pay': 0,
                    'net_pay': 0,
                    'calculation_rule_version': '',
                    'calculation_input_hash': '',
                    'calculation_output_hash': '',
                    'calculation_snapshot': {'demo_seed': True, 'note': 'Run payroll processing before approval.'},
                },
            )

        attendance_count = 0
        day = self.START
        while day <= self.END:
            if day.weekday() < 5 and day not in self.HOLIDAYS:
                self.seed_present(employees['DEMO-001'], day)
                self.seed_late(employees['DEMO-002'], day)
                self.seed_overtime(employees['DEMO-003'], day)
                if day != date(2026, 8, 24):
                    self.seed_present(employees['DEMO-004'], day)
                attendance_count += 4 if day != date(2026, 8, 24) else 3
            day += timedelta(days=1)

        self.seed_leave(employees['DEMO-004'], date(2026, 8, 24))
        self.seed_holiday(employees['DEMO-005'], date(2026, 8, 21), 'Ninoy Aquino Day')
        self.seed_holiday(employees['DEMO-006'], date(2026, 8, 31), 'National Heroes Day')
        attendance_count += 3

        self.stdout.write(self.style.SUCCESS(
            f'Demo seed ready: {org.slug}; {len(employees)} employees; {attendance_count} attendance records; '
            f'{PayrollRecord.objects.filter(payroll_period=period, status=PayrollRecord.Status.DRAFT).count()} DRAFT payroll records; no payroll approval/payment performed.'
        ))
        self.stdout.write('Demo manager: demo-manager (password intentionally unset; assign a password before interactive use).')

    def save_record(self, employee, day, time_in=None, time_out=None, status=AttendanceRecord.Status.PRESENT, late=0, undertime=0, overtime=0, remarks=''):
        assignment = employee.assignments.filter(start_date__lte=day).filter(end_date__isnull=True).first()
        record, _ = AttendanceRecord.objects.update_or_create(
            employee=employee,
            attendance_date=day,
            defaults={
                'assignment': assignment,
                'clock_shift': assignment.shift_template if assignment else None,
                'clock_in_mode': AttendanceRecord.ClockInMode.SCHEDULED,
                'time_in': self.aware(day, *time_in) if time_in else None,
                'time_out': self.aware(day, *time_out) if time_out else None,
                'late_minutes': late,
                'undertime_minutes': undertime,
                'overtime_minutes': overtime,
                'status': status,
                'remarks': remarks,
            },
        )
        record.full_clean()
        record.save()

    def seed_present(self, employee, day):
        self.save_record(employee, day, (8, 0), (17, 0))

    def seed_late(self, employee, day):
        self.save_record(employee, day, (8, 20), (16, 30), late=20, undertime=30, remarks='Demo late and undertime case.')

    def seed_overtime(self, employee, day):
        self.save_record(employee, day, (8, 0), (18, 0), overtime=60, remarks='Demo overtime case.')

    def seed_leave(self, employee, day):
        self.save_record(employee, day, status=AttendanceRecord.Status.LEAVE, remarks='Demo leave case; payroll remains DRAFT.')

    def seed_holiday(self, employee, day, name):
        self.save_record(employee, day, (8, 0), (17, 0), overtime=60, remarks=f'Demo holiday work: {name}.')
