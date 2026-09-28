import csv
from datetime import datetime
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.attendance.models import AttendanceRecord
from apps.employees.models import Employee
from apps.payroll.models import PayrollPeriod, PayrollRecord


class Command(BaseCommand):
    help = 'Import customer opening data from CSV files. Always validates tenant and supports dry-run.'

    def add_arguments(self, parser):
        parser.add_argument('--organization', required=True, help='Organization UUID')
        parser.add_argument('--employees')
        parser.add_argument('--attendance')
        parser.add_argument('--payroll-opening', help='CSV of opening payroll records')
        parser.add_argument('--period-id', help='Payroll period UUID for payroll opening balances')
        parser.add_argument('--dry-run', action='store_true')

    @transaction.atomic
    def handle(self, *args, **opts):
        from apps.organization.models import Organization
        try:
            organization = Organization.objects.get(pk=opts['organization'])
        except Organization.DoesNotExist:
            raise CommandError('Organization not found.')
        created = {'employees': 0, 'attendance': 0, 'payroll': 0}
        if opts['employees']:
            with open(opts['employees'], newline='', encoding='utf-8-sig') as handle:
                for row in csv.DictReader(handle):
                    user = __import__('django.contrib.auth', fromlist=['get_user_model']).get_user_model().objects.create_user(
                        username=row['email'].strip().lower(), email=row['email'].strip().lower(),
                        first_name=row.get('first_name','').strip(), last_name=row.get('last_name','').strip(),
                    )
                    Employee.objects.create(
                        employee_number=row['employee_number'].strip(), user=user, organization=organization,
                        first_name=row['first_name'].strip(), last_name=row['last_name'].strip(),
                        work_email=row.get('email','').strip(), status=row.get('status', Employee.Status.ONBOARDING),
                    )
                    created['employees'] += 1
        if opts['attendance']:
            with open(opts['attendance'], newline='', encoding='utf-8-sig') as handle:
                for row in csv.DictReader(handle):
                    employee = Employee.objects.get(employee_number=row['employee_number'].strip(), organization=organization)
                    AttendanceRecord.objects.create(
                        employee=employee, attendance_date=datetime.strptime(row['attendance_date'], '%Y-%m-%d').date(),
                        time_in=datetime.fromisoformat(row['time_in']) if row.get('time_in') else None,
                        time_out=datetime.fromisoformat(row['time_out']) if row.get('time_out') else None,
                        status=row.get('status', AttendanceRecord.Status.PRESENT),
                        clock_in_mode=AttendanceRecord.ClockInMode.UNSCHEDULED if row.get('clock_in_mode') == 'UNSCHEDULED' else AttendanceRecord.ClockInMode.SCHEDULED,
                        segment_number=int(row.get('segment_number') or 1),
                    )
                    created['attendance'] += 1
        if opts['payroll_opening']:
            if not opts['period_id']:
                raise CommandError('--period-id is required with --payroll-opening.')
            period = PayrollPeriod.objects.get(pk=opts['period_id'], organization=organization)
            with open(opts['payroll_opening'], newline='', encoding='utf-8-sig') as handle:
                for row in csv.DictReader(handle):
                    employee = Employee.objects.get(employee_number=row['employee_number'].strip(), organization=organization)
                    PayrollRecord.objects.create(
                        employee=employee, payroll_period=period,
                        basic_pay=Decimal(row.get('basic_pay','0')), gross_pay=Decimal(row.get('gross_pay','0')),
                        net_pay=Decimal(row.get('net_pay','0')), status=row.get('status', PayrollRecord.Status.DRAFT),
                    )
                    created['payroll'] += 1
        if opts['dry_run']:
            transaction.set_rollback(True)
        self.stdout.write(self.style.SUCCESS(f"Import {'validated' if opts['dry_run'] else 'completed'}: {created}"))
