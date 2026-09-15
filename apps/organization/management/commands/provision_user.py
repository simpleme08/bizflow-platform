from getpass import getpass

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.organization.models import Organization, OrganizationMembership


class Command(BaseCommand):
    help = 'Provision a production user and organization role without exposing passwords in source control or command arguments.'

    def add_arguments(self, parser):
        parser.add_argument('--username', required=True, help='Django username for the account.')
        parser.add_argument('--organization', required=True, help='Active organization slug.')
        parser.add_argument(
            '--role',
            required=True,
            choices=[value for value, _label in OrganizationMembership.Role.choices],
            help='Organization role to assign.',
        )
        parser.add_argument('--email', default='', help='Optional email address.')
        parser.add_argument('--first-name', default='', help='Optional first name.')
        parser.add_argument('--last-name', default='', help='Optional last name.')
        parser.add_argument(
            '--set-password',
            action='store_true',
            help='Prompt for a new password even when the user already exists.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()
        username = options['username'].strip()
        organization_slug = options['organization'].strip()
        role = options['role']

        if not username:
            raise CommandError('Username is required.')
        if not organization_slug:
            raise CommandError('Organization slug is required.')

        try:
            organization = Organization.objects.get(slug=organization_slug, is_active=True)
        except Organization.DoesNotExist as exc:
            raise CommandError(
                f"Active organization '{organization_slug}' was not found. "
                'Use the organization slug, and do not provision users into inactive organizations.'
            ) from exc

        user = User.objects.filter(username=username).first()
        user_created = user is None

        if user is None:
            password = self._prompt_password()
            user = User(
                username=username,
                email=options['email'].strip(),
                first_name=options['first_name'].strip(),
                last_name=options['last_name'].strip(),
                is_active=True,
            )
            user.set_password(password)
            user.save()
        else:
            if not user.is_active:
                raise CommandError('The existing user is inactive; refusing to activate it automatically.')
            update_fields = []
            for field in ('email', 'first_name', 'last_name'):
                value = options[field].strip()
                if value and getattr(user, field) != value:
                    setattr(user, field, value)
                    update_fields.append(field)
            if update_fields:
                update_fields.append('updated_at') if hasattr(user, 'updated_at') else None
                user.save(update_fields=update_fields)
            if options['set_password']:
                user.set_password(self._prompt_password())
                user.save(update_fields=('password',))

        membership, membership_created = OrganizationMembership.objects.get_or_create(
            organization=organization,
            user=user,
            defaults={'role': role, 'is_active': True},
        )
        if not membership_created:
            membership.role = role
            membership.is_active = True
            membership.save(update_fields=('role', 'is_active', 'updated_at'))

        self.stdout.write(self.style.SUCCESS(
            f"Provisioned '{user.get_username()}' as {role} in '{organization.name}' ({organization.slug})."
        ))
        if user_created:
            self.stdout.write('Created a new active user account with the password entered securely at the prompt.')
        elif options['set_password']:
            self.stdout.write('Updated the existing user password securely at the prompt.')
        else:
            self.stdout.write('Existing password was left unchanged.')
        if membership_created:
            self.stdout.write('Created the organization membership.')
        else:
            self.stdout.write('Updated the existing organization membership.')
        if role == OrganizationMembership.Role.SUPER_USER:
            self.stdout.write(
                'Note: SUPER_USER is the HRIS organization role. It does not change Django is_staff/is_superuser. '
                'Use createsuperuser separately when a Django admin superuser is required.'
            )

    def _prompt_password(self):
        password = getpass('Password: ')
        confirmation = getpass('Password (again): ')
        if not password:
            raise CommandError('Password cannot be empty.')
        if password != confirmation:
            raise CommandError('Passwords do not match.')
        return password
