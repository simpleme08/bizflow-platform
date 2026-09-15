from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from .models import Organization, OrganizationMembership


class ProvisionUserCommandTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name='HSIS',
            slug='hsis',
            is_active=True,
            plan_code=Organization.Plan.FREE,
            subscription_status=Organization.SubscriptionStatus.TRIALING,
        )

    @patch('apps.organization.management.commands.provision_user.getpass', side_effect=['StrongPassword!2026', 'StrongPassword!2026'])
    def test_creates_user_and_hr_membership(self, mocked_getpass):
        call_command(
            'provision_user',
            username='production-hr',
            organization='hsis',
            role=OrganizationMembership.Role.HR,
            email='hr@example.com',
        )

        user = get_user_model().objects.get(username='production-hr')
        membership = OrganizationMembership.objects.get(user=user, organization=self.organization)
        self.assertTrue(user.is_active)
        self.assertTrue(user.check_password('StrongPassword!2026'))
        self.assertEqual(membership.role, OrganizationMembership.Role.HR)
        self.assertTrue(membership.is_active)
        mocked_getpass.assert_any_call('Password: ')
        mocked_getpass.assert_any_call('Password (again): ')

    @patch('apps.organization.management.commands.provision_user.getpass', side_effect=['StrongPassword!2026', 'StrongPassword!2026'])
    def test_creates_sme_membership(self, mocked_getpass):
        call_command(
            'provision_user',
            username='production-sme',
            organization='hsis',
            role=OrganizationMembership.Role.SME,
        )

        user = get_user_model().objects.get(username='production-sme')
        membership = OrganizationMembership.objects.get(user=user, organization=self.organization)
        self.assertEqual(membership.role, OrganizationMembership.Role.SME)
        self.assertTrue(user.check_password('StrongPassword!2026'))

    def test_existing_user_password_is_not_changed_by_default(self):
        User = get_user_model()
        user = User.objects.create_user(username='existing-user', password='OriginalPassword!2026')

        call_command(
            'provision_user',
            username='existing-user',
            organization='hsis',
            role=OrganizationMembership.Role.HR,
        )

        user.refresh_from_db()
        self.assertTrue(user.check_password('OriginalPassword!2026'))
        self.assertEqual(
            OrganizationMembership.objects.get(user=user, organization=self.organization).role,
            OrganizationMembership.Role.HR,
        )

    def test_existing_inactive_user_is_rejected(self):
        User = get_user_model()
        User.objects.create_user(username='inactive-user', password='password', is_active=False)

        with self.assertRaisesMessage(CommandError, 'existing user is inactive'):
            call_command(
                'provision_user',
                username='inactive-user',
                organization='hsis',
                role=OrganizationMembership.Role.HR,
            )

    def test_inactive_organization_is_rejected(self):
        self.organization.is_active = False
        self.organization.save(update_fields=('is_active', 'updated_at'))

        with self.assertRaisesMessage(CommandError, 'Active organization'):
            call_command(
                'provision_user',
                username='production-hr',
                organization='hsis',
                role=OrganizationMembership.Role.HR,
            )
