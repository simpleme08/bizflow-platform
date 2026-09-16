import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.organization.models import Organization, OrganizationMembership


class Command(BaseCommand):
    help = 'Idempotently provision the explicitly configured production HRIS role accounts.'

    ACCOUNT_ENV = (
        ('HR', OrganizationMembership.Role.HR, 'BIZFLOW_PRODUCTION_HR'),
        ('SME', OrganizationMembership.Role.SME, 'BIZFLOW_PRODUCTION_SME'),
        ('SUPER_USER', OrganizationMembership.Role.SUPER_USER, 'BIZFLOW_PRODUCTION_SUPER_USER'),
    )

    def _value(self, key, required=True):
        value = os.getenv(key, '').strip()
        if required and not value:
            raise CommandError(f'{key} must be configured for production account provisioning.')
        return value

    def handle(self, *args, **options):
        if os.getenv('DJANGO_ENV', '').lower() != 'production':
            raise CommandError('Production account provisioning is only available when DJANGO_ENV=production.')

        slug = self._value('BIZFLOW_PRODUCTION_ORG_SLUG')
        name = self._value('BIZFLOW_PRODUCTION_ORG_NAME')
        reset_passwords = os.getenv('BIZFLOW_PROVISION_RESET_PASSWORDS', 'false').lower() in ('1', 'true', 'yes')

        accounts = []
        for label, role, prefix in self.ACCOUNT_ENV:
            username = self._value(f'{prefix}_USERNAME')
            password = self._value(f'{prefix}_PASSWORD')
            email = self._value(f'{prefix}_EMAIL', required=False)
            first_name = self._value(f'{prefix}_FIRST_NAME', required=False)
            last_name = self._value(f'{prefix}_LAST_NAME', required=False)
            accounts.append((label, role, username, password, email, first_name, last_name))

        User = get_user_model()
        with transaction.atomic():
            organization, _ = Organization.objects.update_or_create(
                slug=slug,
                defaults={'name': name, 'is_active': True},
            )
            for label, role, username, password, email, first_name, last_name in accounts:
                user, created = User.objects.get_or_create(username=username)
                changed = []
                if email and user.email != email:
                    user.email = email
                    changed.append('email')
                if first_name and user.first_name != first_name:
                    user.first_name = first_name
                    changed.append('first_name')
                if last_name and user.last_name != last_name:
                    user.last_name = last_name
                    changed.append('last_name')
                if created or reset_passwords:
                    user.set_password(password)
                    changed.append('password')
                if not user.is_active:
                    user.is_active = True
                    changed.append('is_active')
                if changed:
                    user.save(update_fields=sorted(set(changed)))
                OrganizationMembership.objects.update_or_create(
                    organization=organization,
                    user=user,
                    defaults={'role': role, 'is_active': True},
                )
                self.stdout.write(f'{label}: provisioned {username}')

        self.stdout.write(self.style.SUCCESS(f'Production accounts ready for organization {organization.slug}.'))
