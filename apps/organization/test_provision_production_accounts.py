import os
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command, CommandError
from django.test import TestCase

from .models import Organization, OrganizationMembership


class ProvisionProductionAccountsCommandTests(TestCase):
    def setUp(self):
        self.env = {
            'DJANGO_ENV': 'production',
            'BIZFLOW_PRODUCTION_ORG_SLUG': 'hsis',
            'BIZFLOW_PRODUCTION_ORG_NAME': 'High Speed Internet Support',
            'BIZFLOW_PRODUCTION_HR_USERNAME': 'production-hr',
            'BIZFLOW_PRODUCTION_HR_PASSWORD': 'hr-test-password',
            'BIZFLOW_PRODUCTION_SME_USERNAME': 'production-sme',
            'BIZFLOW_PRODUCTION_SME_PASSWORD': 'sme-test-password',
            'BIZFLOW_PRODUCTION_SUPER_USER_USERNAME': 'production-super-user',
            'BIZFLOW_PRODUCTION_SUPER_USER_PASSWORD': 'super-test-password',
        }

    def test_provisions_all_configured_roles(self):
        with patch.dict(os.environ, self.env, clear=False):
            call_command('provision_production_accounts')

        organization = Organization.objects.get(slug='hsis')
        for username, role, password in (
            ('production-hr', OrganizationMembership.Role.HR, 'hr-test-password'),
            ('production-sme', OrganizationMembership.Role.SME, 'sme-test-password'),
            ('production-super-user', OrganizationMembership.Role.SUPER_USER, 'super-test-password'),
        ):
            user = get_user_model().objects.get(username=username)
            membership = OrganizationMembership.objects.get(user=user, organization=organization)
            self.assertEqual(membership.role, role)
            self.assertTrue(membership.is_active)
            self.assertTrue(user.check_password(password))

    def test_existing_password_is_not_overwritten(self):
        user = get_user_model().objects.create_user(
            username='production-hr', password='original-password'
        )
        with patch.dict(os.environ, self.env, clear=False):
            call_command('provision_production_accounts')
        user.refresh_from_db()
        self.assertTrue(user.check_password('original-password'))
        self.assertFalse(user.check_password('hr-test-password'))

    def test_inactive_user_is_not_reactivated(self):
        user = get_user_model().objects.create_user(
            username='production-hr', password='original-password', is_active=False
        )
        with patch.dict(os.environ, self.env, clear=False):
            with self.assertRaisesMessage(CommandError, 'is inactive; refusing to reactivate'):
                call_command('provision_production_accounts')
        user.refresh_from_db()
        self.assertFalse(user.is_active)

    def test_inactive_organization_is_not_reactivated(self):
        Organization.objects.create(
            name='HSIS', slug='hsis', is_active=False
        )
        with patch.dict(os.environ, self.env, clear=False):
            with self.assertRaisesMessage(CommandError, 'exists but is inactive'):
                call_command('provision_production_accounts')
