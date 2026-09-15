from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from apps.organization.models import Organization, OrganizationMembership


class Command(BaseCommand):
    help = 'Create or repair the first production organization membership for an existing superuser.'

    def add_arguments(self, parser):
        parser.add_argument('--username', required=True, help='Existing Django superuser username.')
        parser.add_argument('--organization-name', required=True, help='Organization display name.')
        parser.add_argument('--slug', help='Organization slug. Defaults to a slugified organization name.')

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()
        username = options['username'].strip()
        organization_name = options['organization_name'].strip()
        slug = (options.get('slug') or slugify(organization_name)).strip()

        if not username:
            raise CommandError('Username is required.')
        if not organization_name:
            raise CommandError('Organization name is required.')
        if not slug or len(slug) > 80:
            raise CommandError('Organization slug must be 1-80 characters and URL-safe.')

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist as exc:
            raise CommandError('The user does not exist. Run createsuperuser first.') from exc

        if not user.is_active or not user.is_superuser:
            raise CommandError('The specified user must be an active superuser. No ordinary user can bootstrap an organization.')

        organization, created = Organization.objects.get_or_create(
            slug=slug,
            defaults={'name': organization_name, 'is_active': True, 'plan_code': Organization.Plan.FREE, 'subscription_status': Organization.SubscriptionStatus.TRIALING},
        )
        if not organization.is_active:
            raise CommandError('The requested organization already exists but is inactive; refusing to reactivate it automatically.')

        membership, membership_created = OrganizationMembership.objects.get_or_create(
            organization=organization,
            user=user,
            defaults={'role': OrganizationMembership.Role.OWNER, 'is_active': True},
        )
        if membership.role != OrganizationMembership.Role.OWNER or not membership.is_active:
            membership.role = OrganizationMembership.Role.OWNER
            membership.is_active = True
            membership.save(update_fields=('role', 'is_active', 'updated_at'))

        self.stdout.write(self.style.SUCCESS(
            f"Bootstrap complete: user '{user.get_username()}' is OWNER of '{organization.name}' ({organization.slug})."
        ))
        if created:
            self.stdout.write('Created a new FREE/TRIALING organization.')
        if membership_created:
            self.stdout.write('Created the organization membership.')
