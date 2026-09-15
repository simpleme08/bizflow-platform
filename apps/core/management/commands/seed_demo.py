import os
from datetime import date, datetime, time
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.attendance.models import AttendanceRecord
from apps.employees.models import Employee, EmployeeAssignment
from apps.leave.models import EmployeeLeaveBalance, LeaveType
from apps.organization.models import Department, EmploymentType, Organization, Position
from apps.payroll.models import EmployeeSalary, PayrollPeriod, PayrollRecord
from apps.workforce.models import Client, ClientSite, ShiftTemplate
from apps.organization.models import OrganizationMembership
from apps.onboarding.models import EmployeeOnboarding, OnboardingTask, OnboardingTaskTemplate, OnboardingWorkflow
from apps.talent.models import BenefitEnrollment, BenefitPlan, Candidate, EmployeeGoal, JobApplication, JobOpening, OffboardingRecord, PerformanceCycle, PerformanceReview
from apps.operations.models import Announcement, ApprovalRequest, EmployeeDocument, ExternalConnector, OffboardingTask, Project, TimesheetEntry


class Command(BaseCommand):
    help = 'Create a realistic, idempotent BizFlow demo organization.'

    people = (
        ('EMP-000001', 'Juan', 'Cruz', 'demo.juan', 'Operations', 'OPS-LEAD', 'REG', 'Day Shift', Decimal('32000.00'), 5, 60, 'PRESENT'),
        ('EMP-000002', 'Maria', 'Santos', 'demo.maria', 'Human Resources', 'HR-OFFICER', 'REG', 'Day Shift', Decimal('38000.00'), 0, 0, 'PRESENT'),
        ('EMP-000003', 'Carlo', 'Reyes', 'demo.carlo', 'Finance', 'FIN-ANALYST', 'REG', 'Day Shift', Decimal('42000.00'), 20, 0, 'PRESENT'),
        ('EMP-000004', 'Liza', 'Garcia', 'demo.liza', 'Customer Support', 'CSR-II', 'REG', 'Night Shift', Decimal('28000.00'), 0, 0, 'PRESENT'),
        ('EMP-000005', 'Paolo', 'Dela Cruz', 'demo.paolo', 'Operations', 'OPS-ASSOC', 'PROB', 'Day Shift', Decimal('24000.00'), 0, 0, 'PRESENT'),
        ('EMP-000006', 'Nina', 'Villanueva', 'demo.nina', 'Customer Support', 'CSR-I', 'REG', 'Night Shift', Decimal('26000.00'), 0, 0, 'ABSENT'),
        ('EMP-000007', 'Ramon', 'Mendoza', 'demo.ramon', 'IT Services', 'IT-SME', 'REG', 'Day Shift', Decimal('55000.00'), 0, 120, 'PRESENT'),
        ('EMP-000008', 'Sofia', 'Navarro', 'demo.sofia', 'Operations', 'OPS-ASSOC', 'PROB', 'Day Shift', Decimal('24000.00'), 0, 0, 'LEAVE'),
    )

    def handle(self, *args, **options):
        if getattr(settings, 'ENVIRONMENT', '').lower() == 'production':
            raise CommandError('seed_demo is disabled in production.')
        self.demo_password = os.environ.get('BIZFLOW_DEMO_PASSWORD')
        if not self.demo_password:
            raise CommandError('Set BIZFLOW_DEMO_PASSWORD before running seed_demo.')
        organization, _ = Organization.objects.get_or_create(slug='default', defaults={'name': 'Default Organization', 'is_active': True})
        if not organization.is_active:
            organization.is_active = True
            organization.save(update_fields=('is_active', 'updated_at'))
        departments = {name: Department.objects.get_or_create(organization=organization, code=code, defaults={'name': name})[0] for name, code in {'Operations': 'OPS', 'Human Resources': 'HR', 'Finance': 'FIN', 'Customer Support': 'CS', 'IT Services': 'IT'}.items()}
        positions = {}
        for _, _, _, _, _, code, _, _, _, _, _, _ in self.people:
            title = code.replace('-', ' ').title()
            positions[code] = Position.objects.get_or_create(organization=organization, code=code, defaults={'title': title})[0]
        employment_types = {code: EmploymentType.objects.get_or_create(organization=organization, code=code, defaults={'name': name})[0] for code, name in (('REG', 'Regular'), ('PROB', 'Probationary'))}
        client, _ = Client.objects.get_or_create(organization=organization, code='BIZFLOW', defaults={'name': 'BizFlow Service Operations'})
        site, _ = ClientSite.objects.get_or_create(client=client, name='Manila Operations Center', defaults={'address': 'Makati City, Metro Manila'})
        shifts = {
            'Day Shift': ShiftTemplate.objects.get_or_create(name='Day Shift', defaults={'start_time': time(8), 'end_time': time(17)})[0],
            'Night Shift': ShiftTemplate.objects.get_or_create(name='Night Shift', defaults={'start_time': time(22), 'end_time': time(7)})[0],
        }
        leave_types = {code: LeaveType.objects.get_or_create(code=code, defaults={'name': name, 'annual_credits': credits})[0] for code, name, credits in (('VL', 'Vacation Leave', Decimal('15.00')), ('SL', 'Sick Leave', Decimal('10.00')), ('EL', 'Emergency Leave', Decimal('5.00')))}
        today = timezone.localdate()
        for person in self.people:
            self.create_person(organization, departments, positions, employment_types, client, site, shifts, leave_types, today, person)
        PayrollPeriod.objects.get_or_create(organization=organization, name='Demo August 1-15, 2026', start_date=date(2026, 8, 1), end_date=date(2026, 8, 15))
        self.seed_roles(organization, shifts['Day Shift'], today)
        self.seed_full_demo(organization, departments, today)
        self.stdout.write(self.style.SUCCESS(f'Full demo ready: {len(self.people)} employees, role accounts, payroll, talent, operations, and ESS data.'))

    def seed_roles(self, organization, shift, today):
        accounts = (
            ('demo_superuser', OrganizationMembership.Role.SUPER_USER, 'System', 'Administrator'),
            ('demo_hr', OrganizationMembership.Role.HR, 'Helen', 'Rivera'),
            ('demo_manager', OrganizationMembership.Role.MANAGER, 'Miguel', 'Torres'),
            ('demo_employee', OrganizationMembership.Role.EMPLOYEE, 'Emma', 'Reyes'),
        )
        for username, role, first_name, last_name in accounts:
            user, _ = get_user_model().objects.get_or_create(username=username, defaults={'first_name': first_name, 'last_name': last_name})
            user.set_password(self.demo_password); user.is_active = True
            if username == 'demo_superuser': user.is_staff = True; user.is_superuser = True
            user.save()
            OrganizationMembership.objects.update_or_create(organization=organization, user=user, defaults={'role': role, 'is_active': True})
            if role == OrganizationMembership.Role.EMPLOYEE:
                employee, _ = Employee.objects.update_or_create(user=user, defaults={'employee_number': 'DEMO-EMPLOYEE', 'organization': organization, 'first_name': first_name, 'last_name': last_name, 'is_active': True})
                EmployeeAssignment.objects.update_or_create(employee=employee, shift_template=shift, start_date=date(today.year, 1, 1), defaults={'is_primary': True})

    def seed_full_demo(self, organization, departments, today):
        employees = list(organization.employees.filter(is_active=True).select_related('user'))
        hr_user = get_user_model().objects.get(username='demo_hr')
        manager_user = get_user_model().objects.get(username='demo_manager')
        period, _ = PayrollPeriod.objects.get_or_create(organization=organization, name='Demo August 1-15, 2026', start_date=date(2026, 8, 1), end_date=date(2026, 8, 15))
        for employee in employees:
            salary = getattr(employee, 'salary', None)
            basic = salary.basic_salary / Decimal('2') if salary else Decimal('15000.00')
            PayrollRecord.objects.update_or_create(employee=employee, payroll_period=period, defaults={'basic_pay': basic, 'overtime_pay': Decimal('500.00'), 'gross_pay': basic + Decimal('500.00'), 'late_deduction': Decimal('100.00'), 'undertime_deduction': Decimal('0.00'), 'other_deductions': Decimal('200.00'), 'net_pay': basic + Decimal('200.00'), 'status': PayrollRecord.Status.APPROVED})
        workflow, _ = OnboardingWorkflow.objects.get_or_create(organization=organization, name='Standard New Hire')
        task_template, _ = OnboardingTaskTemplate.objects.get_or_create(workflow=workflow, title='Read employee handbook', defaults={'order': 1})
        if employees:
            onboarding, _ = EmployeeOnboarding.objects.get_or_create(employee=employees[0], defaults={'workflow': workflow, 'start_date': today, 'expected_completion_date': today})
            OnboardingTask.objects.get_or_create(onboarding=onboarding, template=task_template, defaults={'title': task_template.title})
        cycle, _ = PerformanceCycle.objects.get_or_create(organization=organization, name=f'{today.year} Annual Review', defaults={'start_date': date(today.year, 1, 1), 'end_date': date(today.year, 12, 31), 'status': PerformanceCycle.Status.ACTIVE})
        if employees:
            EmployeeGoal.objects.get_or_create(employee=employees[0], cycle=cycle, title='Improve customer response time', defaults={'progress': 55, 'status': EmployeeGoal.Status.ON_TRACK})
            PerformanceReview.objects.get_or_create(cycle=cycle, employee=employees[0], defaults={'reviewer': manager_user, 'rating': 4, 'comments': 'Strong performance.', 'status': PerformanceReview.Status.SUBMITTED})
        plan, _ = BenefitPlan.objects.get_or_create(organization=organization, name='Demo Medical Plan', defaults={'provider': 'Demo Health', 'employee_cost': Decimal('1000.00'), 'employer_cost': Decimal('2500.00')})
        for employee in employees[:3]: BenefitEnrollment.objects.get_or_create(employee=employee, plan=plan, effective_date=date(today.year, 1, 1))
        job, _ = JobOpening.objects.get_or_create(organization=organization, title='HR Coordinator', defaults={'department': departments['Human Resources'], 'status': JobOpening.Status.OPEN})
        candidate, _ = Candidate.objects.get_or_create(organization=organization, email='candidate@example.com', defaults={'first_name': 'Alex', 'last_name': 'Morgan', 'source': 'Career page'})
        JobApplication.objects.get_or_create(job=job, candidate=candidate, defaults={'stage': JobApplication.Stage.INTERVIEW, 'rating': 4})
        if len(employees) > 1:
            exit_record, _ = OffboardingRecord.objects.get_or_create(employee=employees[-1], defaults={'last_working_day': today, 'reason': 'Demo transition'})
            OffboardingTask.objects.get_or_create(offboarding=exit_record, title='Collect company assets', defaults={'assigned_to': hr_user, 'due_date': today})
        EmployeeDocument.objects.get_or_create(organization=organization, title='Employee Handbook', defaults={'category': 'Policy', 'body': 'Demo employee handbook and code of conduct.', 'requires_acknowledgement': True, 'status': EmployeeDocument.Status.PUBLISHED})
        Announcement.objects.get_or_create(organization=organization, title='Welcome to BizFlow', defaults={'message': 'Explore your self-service tools and keep your profile current.', 'is_published': True, 'published_at': timezone.now()})
        project, _ = Project.objects.get_or_create(organization=organization, code='INTERNAL', defaults={'name': 'Internal Operations', 'is_billable': False})
        if employees: TimesheetEntry.objects.get_or_create(employee=employees[0], project=project, work_date=today, defaults={'hours': Decimal('8.00'), 'status': TimesheetEntry.Status.APPROVED, 'approver': manager_user})
        ApprovalRequest.objects.get_or_create(organization=organization, requester=hr_user, title='Demo compensation change', defaults={'approver': manager_user, 'category': 'COMPENSATION', 'payload': {'note': 'Sample approval workflow'}})
        for name, kind in (('Supabase Postgres', ExternalConnector.Kind.PAYROLL), ('E-signature Provider', ExternalConnector.Kind.ESIGN), ('Benefits Carrier', ExternalConnector.Kind.BENEFITS)):
            ExternalConnector.objects.get_or_create(organization=organization, name=name, defaults={'kind': kind, 'is_enabled': False})

    def create_person(self, organization, departments, positions, employment_types, client, site, shifts, leave_types, today, person):
        number, first_name, last_name, username, department, position_code, employment_code, shift_name, salary, late_minutes, overtime_minutes, status = person
        user, _ = get_user_model().objects.get_or_create(username=username, defaults={'first_name': first_name, 'last_name': last_name})
        user.set_password(self.demo_password)
        user.is_active = True
        user.save(update_fields=('password', 'is_active', 'first_name', 'last_name'))
        OrganizationMembership.objects.update_or_create(organization=organization, user=user, defaults={'role': OrganizationMembership.Role.EMPLOYEE, 'is_active': True})
        employee, _ = Employee.objects.update_or_create(employee_number=number, defaults={'user': user, 'organization': organization, 'department': departments[department], 'position': positions[position_code], 'employment_type': employment_types[employment_code], 'first_name': first_name, 'last_name': last_name, 'is_active': True})
        assignment, _ = EmployeeAssignment.objects.update_or_create(employee=employee, shift_template=shifts[shift_name], start_date=date(today.year, 1, 1), defaults={'client': client, 'client_site': site, 'is_primary': True})
        EmployeeSalary.objects.update_or_create(employee=employee, defaults={'basic_salary': salary, 'effective_date': date(today.year, 1, 1)})
        time_in = timezone.make_aware(datetime.combine(today, time(8, 0) if shift_name == 'Day Shift' else time(22, 0))) if status == 'PRESENT' else None
        time_out = timezone.make_aware(datetime.combine(today, time(17, 0))) if status == 'PRESENT' else None
        AttendanceRecord.objects.update_or_create(employee=employee, attendance_date=today, defaults={'assignment': assignment, 'time_in': time_in, 'time_out': time_out, 'late_minutes': late_minutes, 'overtime_minutes': overtime_minutes, 'status': status})
        for leave_type in leave_types.values():
            EmployeeLeaveBalance.objects.update_or_create(employee=employee, leave_type=leave_type, year=today.year, defaults={'credits': leave_type.annual_credits, 'used': Decimal('0.00')})
