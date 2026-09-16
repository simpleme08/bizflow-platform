import os
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings

from apps.organization.models import Organization


@override_settings(ENVIRONMENT='production')
class ProductionAccountProvisioningTests(TestCase):
    def env(self):
        return {
            'DJANGO_ENV': 'production',
            'BIZFLOW_PRODUCTION_ORG_SLUG': 'hsis',
            'BIZFLOW_PRODUCTION_ORG_NAME': 'High Speed Internet Support',
            'BIZFLOW_PRODUCTION_HR_USERNAME': 'hsis_hr', 'BIZFLOW_PRODUCTION_HR_PASSWORD': 'test-hr-password',
            'BIZFLOW_PRODUCTION_HR_EMAIL': 'hr@example.test', 'BIZFLOW_PRODUCTION_HR_FIRST_NAME': 'HR', 'BIZFLOW_PRODUCTION_HR_LAST_NAME': 'User',
            'BIZFLOW_PRODUCTION_SME_USERNAME': 'hsis_sme', 'BIZFLOW_PRODUCTION_SME_PASSWORD': 'test-sme-password',
            'BIZFLOW_PRODUCTION_SME_EMAIL': 'sme@example.test', 'BIZFLOW_PRODUCTION_SME_FIRST_NAME': 'SME', 'BIZFLOW_PRODUCTION_SME_LAST_NAME': 'User',
            'BIZFLOW_PRODUCTION_SUPER_USER_USERNAME': 'hsis_superuser', 'BIZFLOW_PRODUCTION_SUPER_USER_PASSWORD': 'test-super-password',
            'BIZFLOW_PRODUCTION_SUPER_USER_EMAIL': 'super@example.test', 'BIZFLOW_PRODUCTION_SUPER_USER_FIRST_NAME': 'Super', 'BIZFLOW_PRODUCTION_SUPER_USER_LAST_NAME': 'User',
            'BIZFLOW_PROVISION_RESET_PASSWORDS': 'false',
        }

    def test_provisions_configured_roles_idempotently(self):
        with patch.dict(os.environ, self.env(), clear=False):
            call_command('provision_production_accounts', stdout=StringIO())
            call_command('provision_production_accounts', stdout=StringIO())
        organization = Organization.objects.get(slug='hsis')
        self.assertEqual(organization.name, 'High Speed Internet Support')
        self.assertEqual(set(organization.memberships.values_list('role', flat=True)), {'HR', 'SME', 'SUPER_USER'})
        self.assertTrue(get_user_model().objects.get(username='hsis_hr').check_password('test-hr-password'))

    def test_existing_password_is_not_reset_by_default(self):
        user = get_user_model().objects.create_user(username='hsis_hr', password='existing-password')
        with patch.dict(os.environ, self.env(), clear=False):
            call_command('provision_production_accounts', stdout=StringIO())
        user.refresh_from_db()
        self.assertTrue(user.check_password('existing-password'))

    def test_command_requires_production_environment(self):
        values = self.env()
        values['DJANGO_ENV'] = 'development'
        with patch.dict(os.environ, values, clear=False):
            with self.assertRaises(CommandError):
                call_command('provision_production_accounts', stdout=StringIO())
