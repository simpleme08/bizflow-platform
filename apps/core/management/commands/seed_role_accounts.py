import os
from datetime import date, time

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.employees.models import Employee, EmployeeAssignment
from apps.organization.models import Organization, OrganizationMembership
from apps.workforce.models import ShiftTemplate


class Command(BaseCommand):
    help = 'Create demo accounts for every BizFlow role except programmer.'

    password = 'DemoRole2026!'
    role_accounts = (
        ('demo_owner', OrganizationMembership.Role.OWNER, 'Demo Owner'),
        ('demo_admin', OrganizationMembership.Role.ADMIN, 'Demo Admin'),
        ('demo_ceo', OrganizationMembership.Role.CEO, 'Demo CEO'),
        ('demo_hr', OrganizationMembership.Role.HR, 'Demo HR'),
        ('demo_sme', OrganizationMembership.Role.SME, 'Demo SME'),
        ('demo_team_leader', OrganizationMembership.Role.TEAM_LEADER, 'Demo Team Leader'),
        ('demo_manager', OrganizationMembership.Role.MANAGER, 'Demo Manager'),
        ('demo_employee', OrganizationMembership.Role.EMPLOYEE, 'Demo Employee'),
    )

    def handle(self, *args, **options):
        if os.getenv('DJANGO_ENV', '').lower() == 'production':
            raise CommandError('Demo account seeding is disabled in production.')

        organization = Organization.objects.filter(is_active=True).order_by('created_at').first()
        if organization is None:
            organization = Organization.objects.create(name='Default Organization', slug='default')
        shift, _ = ShiftTemplate.objects.get_or_create(
            name='Demo Day Shift',
            defaults={'start_time': time(8), 'end_time': time(17)},
        )
        user_model = get_user_model()
        for username, role, display_name in self.role_accounts:
            first_name, last_name = display_name.split(' ', 1)
            user, _ = user_model.objects.get_or_create(
                username=username,
                defaults={'first_name': first_name, 'last_name': last_name},
            )
            user.set_password(self.password)
            user.is_active = True
            user.save(update_fields=('password', 'is_active', 'first_name', 'last_name'))
            OrganizationMembership.objects.update_or_create(
                organization=organization,
                user=user,
                defaults={'role': role, 'is_active': True},
            )
            if role == OrganizationMembership.Role.EMPLOYEE:
                employee, _ = Employee.objects.update_or_create(
                    user=user,
                    defaults={
                        'employee_number': 'DEMO-EMPLOYEE',
                        'organization': organization,
                        'first_name': first_name,
                        'last_name': last_name,
                        'is_active': True,
                    },
                )
                EmployeeAssignment.objects.update_or_create(
                    employee=employee,
                    shift_template=shift,
                    start_date=date(2026, 1, 1),
                    defaults={'is_primary': True},
                )
        self.stdout.write(self.style.SUCCESS(f'Created or updated {len(self.role_accounts)} demo role accounts.'))
        self.stdout.write('Username pattern: demo_<role> | Password: <demo credential configured in source>')
