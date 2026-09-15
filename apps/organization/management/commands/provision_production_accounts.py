import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.organization.models import Organization, OrganizationMembership


class Command(BaseCommand):
    help = 'Provision production HRIS accounts from deployment environment variables without storing credentials in source control.'

    ROLE_SPECS = (
        ('HR', 'HR'),
        ('SME', 'SME'),
        ('SUPER_USER', 'SUPER_USER'),
    )

    @transaction.atomic
    def handle(self, *args, **options):
        if os.getenv('DJANGO_ENV', '').lower() != 'production':
            raise CommandError('This command is production-only.')

        organization_slug = self._required('BIZFLOW_PRODUCTION_ORG_SLUG')
        organization_name = os.getenv('BIZFLOW_PRODUCTION_ORG_NAME', '').strip()
        if not organization_name:
            organization_name = organization_slug.replace('-', ' ').title()

        organization, created = Organization.objects.get_or_create(
            slug=organization_slug,
            defaults={
                'name': organization_name,
                'is_active': True,
                'plan_code': Organization.Plan.FREE,
                'subscription_status': Organization.SubscriptionStatus.TRIALING,
            },
        )
        if not organization.is_active:
            raise CommandError(
                f"Production organization '{organization_slug}' exists but is inactive; refusing to reactivate it."
            )

        User = get_user_model()
        for role, prefix in self.ROLE_SPECS:
            self._provision_account(User, organization, role, prefix)

        self.stdout.write(self.style.SUCCESS(
            f"Production account provisioning complete for '{organization.name}' ({organization.slug})."
        ))
        if created:
            self.stdout.write('Created the production organization as FREE/TRIALING.')

    def _provision_account(self, User, organization, role, prefix):
        username = self._required(f'BIZFLOW_PRODUCTION_{prefix}_USERNAME')
        password = self._required(f'BIZFLOW_PRODUCTION_{prefix}_PASSWORD')
        email = os.getenv(f'BIZFLOW_PRODUCTION_{prefix}_EMAIL', '').strip()
        first_name = os.getenv(f'BIZFLOW_PRODUCTION_{prefix}_FIRST_NAME', '').strip()
        last_name = os.getenv(f'BIZFLOW_PRODUCTION_{prefix}_LAST_NAME', '').strip()

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
                raise CommandError(f"Configured production user '{username}' is inactive; refusing to reactivate it.")
            update_fields = []
            for field, value in (
                ('email', email),
                ('first_name', first_name),
                ('last_name', last_name),
            ):
                if value and getattr(user, field) != value:
                    setattr(user, field, value)
                    update_fields.append(field)
            if update_fields:
                user.save(update_fields=update_fields)

        membership, created = OrganizationMembership.objects.get_or_create(
            organization=organization,
            user=user,
            defaults={'role': role, 'is_active': True},
        )
        if not created:
            changed = membership.role != role or not membership.is_active
            if changed:
                membership.role = role
                membership.is_active = True
                membership.save(update_fields=('role', 'is_active', 'updated_at'))

        self.stdout.write(f"Provisioned configured {role} account '{username}'.")

    @staticmethod
    def _required(name):
        value = os.getenv(name, '').strip()
        if not value:
            raise CommandError(f'Missing required production environment variable: {name}')
        return value
