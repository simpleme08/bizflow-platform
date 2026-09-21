import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.organization.models import Organization, OrganizationMembership


class Command(BaseCommand):
    help = 'Provision explicitly configured production HRIS accounts without reactivating disabled records.'

    ACCOUNT_ENV = (
        ('HR', OrganizationMembership.Role.HR, 'BIZFLOW_PRODUCTION_HR'),
        ('SME', OrganizationMembership.Role.SME, 'BIZFLOW_PRODUCTION_SME'),
        ('SUPER_USER', OrganizationMembership.Role.SUPER_USER, 'BIZFLOW_PRODUCTION_SUPER_USER'),
    )

    @staticmethod
    def _value(key, required=True):
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
            organization = Organization.objects.filter(slug=slug).first()
            if organization is None:
                organization = Organization.objects.create(
                    slug=slug,
                    name=name,
                    is_active=True,
                    plan_code=Organization.Plan.FREE,
                    subscription_status=Organization.SubscriptionStatus.TRIALING,
                )
                self.stdout.write('Created the production organization as FREE/TRIALING.')
            elif not organization.is_active:
                raise CommandError(
                    f"Production organization '{slug}' exists but is inactive; refusing to reactivate it."
                )

            for label, role, username, password, email, first_name, last_name in accounts:
                user = User.objects.filter(username=username).first()
                if user is None:
                    user = User(
                        username=username,
                        email=email,
                        first_name=first_name,
                        last_name=last_name,
                        is_active=True,
                    )
                    user.set_password(password)
                    user.save()
                else:
                    if not user.is_active:
                        raise CommandError(
                            f"Configured production user '{username}' is inactive; refusing to reactivate it."
                        )
                    changed = []
                    for field, value in (
                        ('email', email),
                        ('first_name', first_name),
                        ('last_name', last_name),
                    ):
                        if value and getattr(user, field) != value:
                            setattr(user, field, value)
                            changed.append(field)
                    if reset_passwords:
                        user.set_password(password)
                        changed.append('password')
                    if changed:
                        user.save(update_fields=sorted(set(changed)))

                membership, created = OrganizationMembership.objects.get_or_create(
                    organization=organization,
                    user=user,
                    defaults={'role': role, 'is_active': True},
                )
                if not created:
                    if not membership.is_active:
                        raise CommandError(
                            f"Configured membership for '{username}' is inactive; refusing to reactivate it."
                        )
                    if membership.role != role:
                        membership.role = role
                        membership.save(update_fields=('role', 'updated_at'))
                self.stdout.write(f'{label}: provisioned {username}')

        self.stdout.write(self.style.SUCCESS(f'Production accounts ready for organization {slug}.'))
