from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.attendance.models import AttendanceRecord
from apps.employees.models import Employee, EmployeeAssignment
from apps.organization.models import Department, EmploymentType, Organization, OrganizationMembership, Position
from apps.payroll.models import EmployeeSalary, EmployeeSalaryHistory, PayrollPeriod, PayrollProfile, PayrollRecord
from apps.workforce.models import Client, ClientSite, ShiftTemplate


class Command(BaseCommand):
    help = 'Create an idempotent HSIS client demo with Parañaque and Davao operations.'

    people = (
        ('HSIS-P001', 'Angela', 'Reyes', 'hsis.angela', 'VFDA', 'HSIS-VFDA-1', 'Parañaque', 'Day', Decimal('26000.00')),
        ('HSIS-P002', 'Bea', 'Santos', 'hsis.bea', 'VFDA', 'HSIS-VFDA-1', 'Parañaque', 'Night', Decimal('27000.00')),
        ('HSIS-P003', 'Carla', 'Mendoza', 'hsis.carla', 'Technical Support', 'HSIS-TECH-1', 'Parañaque', 'Day', Decimal('30000.00')),
        ('HSIS-P004', 'Daniel', 'Garcia', 'hsis.daniel', 'Technical Support', 'HSIS-TECH-1', 'Parañaque', 'Night', Decimal('32000.00')),
        ('HSIS-P005', 'Ella', 'Navarro', 'hsis.ella', 'VFDA', 'HSIS-VFDA-1', 'Parañaque', 'Day', Decimal('25500.00')),
        ('HSIS-P006', 'Faith', 'Cruz', 'hsis.faith', 'VFDA', 'HSIS-VFDA-1', 'Parañaque', 'Night', Decimal('26500.00')),
        ('HSIS-P007', 'Gino', 'Torres', 'hsis.gino', 'Technical Support', 'HSIS-TECH-1', 'Parañaque', 'Day', Decimal('30500.00')),
        ('HSIS-P008', 'Hannah', 'Lim', 'hsis.hannah', 'Technical Support', 'HSIS-TECH-1', 'Parañaque', 'Night', Decimal('32500.00')),
        ('HSIS-D001', 'Ivy', 'Flores', 'hsis.ivy', 'VFDA', 'HSIS-VFDA-1', 'Davao', 'Day', Decimal('25000.00')),
        ('HSIS-D002', 'Jessa', 'Rivera', 'hsis.jessa', 'VFDA', 'HSIS-VFDA-1', 'Davao', 'Night', Decimal('26000.00')),
        ('HSIS-D003', 'Kevin', 'Dela Cruz', 'hsis.kevin', 'Technical Support', 'HSIS-TECH-1', 'Davao', 'Day', Decimal('29500.00')),
        ('HSIS-D004', 'Lara', 'Villanueva', 'hsis.lara', 'Technical Support', 'HSIS-TECH-1', 'Davao', 'Night', Decimal('31500.00')),
        ('HSIS-D005', 'Mia', 'Ramos', 'hsis.mia', 'VFDA', 'HSIS-VFDA-1', 'Davao', 'Day', Decimal('25500.00')),
        ('HSIS-D006', 'Nico', 'Aquino', 'hsis.nico', 'VFDA', 'HSIS-VFDA-1', 'Davao', 'Night', Decimal('26500.00')),
        ('HSIS-D007', 'Olivia', 'Tan', 'hsis.olivia', 'Technical Support', 'HSIS-TECH-1', 'Davao', 'Day', Decimal('30000.00')),
        ('HSIS-D008', 'Paolo', 'Mercado', 'hsis.paolo', 'Technical Support', 'HSIS-TECH-1', 'Davao', 'Night', Decimal('32000.00')),
    )

    def handle(self, *args, **options):
        today = timezone.localdate()
        organization, _ = Organization.objects.update_or_create(
            slug='high-speed-internet-support',
            defaults={
                'name': 'High Speed Internet Support',
                'is_active': True,
                'plan_code': Organization.Plan.BUSINESS,
                'subscription_status': Organization.SubscriptionStatus.ACTIVE,
                'overage_rate': Decimal('30.00'),
            },
        )
        client, _ = Client.objects.update_or_create(
            organization=organization,
            code='HSIS',
            defaults={'name': 'High Speed Internet Support', 'is_active': True},
        )
        sites = {
            'Parañaque': ClientSite.objects.update_or_create(
                client=client,
                name='Parañaque Operations Center',
                defaults={'address': '2nd Floor, 35 Doña Soledad Ave, Betterliving Subdivision, Barangay Don Bosco, Parañaque City, Philippines', 'is_active': True},
            )[0],
            'Davao': ClientSite.objects.update_or_create(
                client=client,
                name='Davao Operations Center',
                defaults={'address': 'Davao City, Philippines', 'is_active': True},
            )[0],
        }
        departments = {}
        for code, name in (('VFDA', 'Virtual Front Desk Assistance'), ('TECH', 'Technical Support')):
            departments[code] = Department.objects.update_or_create(
                organization=organization, code=code, defaults={'name': name}
            )[0]
        positions = {}
        for code, title in (
            ('HSIS-VFDA-1', 'Virtual Front Desk Agent'),
            ('HSIS-TECH-1', 'Technical Support Agent'),
        ):
            positions[code] = Position.objects.update_or_create(
                organization=organization, code=code, defaults={'title': title}
            )[0]
        employment_types = {
            'REG': EmploymentType.objects.update_or_create(
                organization=organization, code='REG',
                defaults={'name': 'Regular', 'eligible_for_overtime': True},
            )[0],
        }
        shifts = {
            'Day': ShiftTemplate.objects.update_or_create(
                name='HSIS Day Shift', defaults={'start_time': time(8, 0), 'end_time': time(17, 0)}
            )[0],
            'Night': ShiftTemplate.objects.update_or_create(
                name='HSIS Night Shift', defaults={'start_time': time(22, 0), 'end_time': time(7, 0)}
            )[0],
        }
        self.seed_admin_accounts(organization, shifts['Day'], today)
        employees = [
            self.create_employee(organization, departments, positions, employment_types, client, sites, shifts, today, person)
            for person in self.people
        ]
        self.seed_attendance(employees, today)
        self.seed_payroll(employees, organization, today)
        self.stdout.write(self.style.SUCCESS(
            'HSIS demo ready: 16 agents, 2 sites (Parañaque/Davao), VFDA + Technical Support, shift assignments, '
            'attendance history, salary history, and a payroll period ready for approval.'
        ))
        self.stdout.write('HSIS employee password: DemoHSIS2026!')
        self.stdout.write('HSIS HR login: hsis_hr / DemoHSISRole2026!')
        self.stdout.write('HSIS manager login: hsis_manager / DemoHSISRole2026!')

    def seed_admin_accounts(self, organization, day_shift, today):
        accounts = (
            ('hsis_hr', OrganizationMembership.Role.HR, 'HSIS', 'HR'),
            ('hsis_manager', OrganizationMembership.Role.MANAGER, 'HSIS', 'Manager'),
        )
        User = get_user_model()
        for username, role, first_name, last_name in accounts:
            user, _ = User.objects.get_or_create(
                username=username, defaults={'first_name': first_name, 'last_name': last_name}
            )
            user.set_password('DemoHSISRole2026!')
            user.is_active = True
            user.save(update_fields=('password', 'is_active', 'first_name', 'last_name'))
            OrganizationMembership.objects.update_or_create(
                organization=organization, user=user,
                defaults={'role': role, 'is_active': True},
            )
        user, _ = User.objects.get_or_create(
            username='hsis.employee', defaults={'first_name': 'Demo', 'last_name': 'Employee'}
        )
        user.set_password('DemoHSIS2026!')
        user.is_active = True
        user.save(update_fields=('password', 'is_active', 'first_name', 'last_name'))
        OrganizationMembership.objects.update_or_create(
            organization=organization, user=user,
            defaults={'role': OrganizationMembership.Role.EMPLOYEE, 'is_active': True},
        )
        employee, _ = Employee.objects.update_or_create(
            employee_number='HSIS-DEMO-EMP',
            defaults={
                'user': user, 'organization': organization,
                'first_name': 'Demo', 'last_name': 'Employee', 'is_active': True,
            },
        )
        EmployeeAssignment.objects.update_or_create(
            employee=employee, shift_template=day_shift,
            start_date=date(today.year, 1, 1), defaults={'is_primary': True},
        )

    def create_employee(self, organization, departments, positions, employment_types, client, sites, shifts, today, person):
        number, first_name, last_name, username, department_code, position_code, site_name, shift_name, salary = person
        User = get_user_model()
        user, _ = User.objects.get_or_create(
            username=username, defaults={'first_name': first_name, 'last_name': last_name}
        )
        user.set_password('DemoHSIS2026!')
        user.is_active = True
        user.save(update_fields=('password', 'is_active', 'first_name', 'last_name'))
        OrganizationMembership.objects.update_or_create(
            organization=organization, user=user,
            defaults={'role': OrganizationMembership.Role.EMPLOYEE, 'is_active': True},
        )
        # The people table uses the human-readable department name for clarity,
        # while the lookup dictionary is keyed by stable department code.
        department_key = {'Technical Support': 'TECH', 'VFDA': 'VFDA'}[department_code]
        employee, _ = Employee.objects.update_or_create(
            employee_number=number,
            defaults={
                'user': user,
                'organization': organization,
                'department': departments[department_key],
                'position': positions[position_code],
                'employment_type': employment_types['REG'],
                'first_name': first_name,
                'last_name': last_name,
                'is_active': True,
            },
        )
        assignment, _ = EmployeeAssignment.objects.update_or_create(
            employee=employee,
            shift_template=shifts[shift_name],
            start_date=date(today.year, 1, 1),
            defaults={'client': client, 'client_site': sites[site_name], 'is_primary': True},
        )
        EmployeeSalary.objects.update_or_create(
            employee=employee, defaults={'basic_salary': salary, 'effective_date': date(today.year, 1, 1)}
        )
        EmployeeSalaryHistory.objects.update_or_create(
            employee=employee, effective_date=date(today.year - 1, 1, 1),
            defaults={'basic_salary': salary - Decimal('1500.00'), 'reason': 'Prior-year demo salary'},
        )
        EmployeeSalaryHistory.objects.update_or_create(
            employee=employee, effective_date=date(today.year, 1, 1),
            defaults={'basic_salary': salary, 'reason': 'Annual salary adjustment'},
        )
        PayrollProfile.objects.update_or_create(
            employee=employee,
            defaults={
                'sss_number': f'34-000{number[-3:]}-0',
                'philhealth_number': f'12-000{number[-3:]}-0',
                'pagibig_number': f'12-000{number[-3:]}-0',
                'tin': f'900-000-{number[-3:]}',
                'minimum_wage_earner': False,
                'wage_region': 'NCR' if site_name == 'Parañaque' else 'XI',
                'wage_category': 'NON_AGRICULTURE',
            },
        )
        return employee

    def business_days(self, end_date, count):
        dates = []
        cursor = end_date - timedelta(days=1)
        while len(dates) < count:
            if cursor.weekday() < 5:
                dates.append(cursor)
            cursor -= timedelta(days=1)
        return list(reversed(dates))

    def seed_attendance(self, employees, today):
        for index, employee in enumerate(employees):
            assignment = employee.assignments.filter(is_primary=True).select_related('shift_template').first()
            if not assignment:
                continue
            for day_index, attendance_date in enumerate(self.business_days(today, 10)):
                if assignment.shift_template.name == 'HSIS Night Shift':
                    time_in = timezone.make_aware(datetime.combine(attendance_date, time(22, 0)))
                    time_out = timezone.make_aware(datetime.combine(attendance_date + timedelta(days=1), time(7, 0)))
                else:
                    time_in = timezone.make_aware(datetime.combine(attendance_date, time(8, 0)))
                    time_out = timezone.make_aware(datetime.combine(attendance_date, time(17, 0)))
                AttendanceRecord.objects.update_or_create(
                    employee=employee, attendance_date=attendance_date,
                    defaults={
                        'assignment': assignment, 'time_in': time_in, 'time_out': time_out,
                        'late_minutes': 10 if (index + day_index) % 7 == 0 else 0,
                        'overtime_minutes': 60 if (index + day_index) % 6 == 0 else 0,
                        'status': AttendanceRecord.Status.PRESENT,
                    },
                )
            if employee.employee_number == 'HSIS-P001':
                AttendanceRecord.objects.filter(employee=employee, attendance_date=today).delete()
                continue
            if assignment.shift_template.name == 'HSIS Night Shift':
                time_in = timezone.make_aware(datetime.combine(today, time(22, 0)))
                time_out = None
            else:
                time_in = timezone.make_aware(datetime.combine(today, time(8, 0)))
                time_out = timezone.make_aware(datetime.combine(today, time(17, 0)))
            AttendanceRecord.objects.update_or_create(
                employee=employee, attendance_date=today,
                defaults={'assignment': assignment, 'time_in': time_in, 'time_out': time_out, 'status': AttendanceRecord.Status.PRESENT},
            )

    def seed_payroll(self, employees, organization, today):
        periods = (
            ('HSIS Payroll July 1-15, 2026', date(2026, 7, 1), date(2026, 7, 15), PayrollPeriod.Status.APPROVED),
            ('HSIS Payroll July 16-31, 2026', date(2026, 7, 16), date(2026, 7, 31), PayrollPeriod.Status.APPROVED),
            ('HSIS Payroll August 1-15, 2026', date(2026, 8, 1), date(2026, 8, 15), PayrollPeriod.Status.APPROVED),
            ('HSIS Payroll September 1-15, 2026 - For Approval', date(2026, 9, 1), date(2026, 9, 15), PayrollPeriod.Status.CALCULATED),
        )
        for name, start_date, end_date, status in periods:
            period, _ = PayrollPeriod.objects.update_or_create(
                organization=organization, start_date=start_date, end_date=end_date,
                defaults={'name': name, 'status': status, 'frequency': PayrollPeriod.Frequency.SEMI_MONTHLY},
            )
            for employee in employees:
                salary = employee.salary.basic_salary
                basic = (salary / Decimal('2')).quantize(Decimal('0.01'))
                overtime = Decimal('500.00') if employee.employee_number[-1] in {'1', '4', '7'} else Decimal('0.00')
                late = Decimal('100.00') if employee.employee_number[-1] in {'2', '5'} else Decimal('0.00')
                gross = basic + overtime
                statutory = (gross * Decimal('0.08')).quantize(Decimal('0.01'))
                other = Decimal('250.00')
                net = gross - statutory - late - other
                record_status = PayrollRecord.Status.DRAFT if status == PayrollPeriod.Status.CALCULATED else PayrollRecord.Status.APPROVED
                PayrollRecord.objects.update_or_create(
                    employee=employee, payroll_period=period,
                    defaults={
                        'basic_pay': basic,
                        'overtime_pay': overtime,
                        'gross_pay': gross,
                        'sss_employee': (gross * Decimal('0.05')).quantize(Decimal('0.01')),
                        'philhealth_employee': (gross * Decimal('0.025')).quantize(Decimal('0.01')),
                        'pagibig_employee': (gross * Decimal('0.005')).quantize(Decimal('0.01')),
                        'withholding_tax': Decimal('0.00'),
                        'late_deduction': late,
                        'undertime_deduction': Decimal('0.00'),
                        'leave_without_pay': Decimal('0.00'),
                        'loan_deductions': Decimal('0.00'),
                        'other_deductions': other,
                        'net_pay': net,
                        'status': record_status,
                    },
                )
