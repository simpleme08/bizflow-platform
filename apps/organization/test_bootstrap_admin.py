from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from .models import Organization, OrganizationMembership


class BootstrapAdminCommandTests(TestCase):
    def test_bootstrap_creates_owner_membership_for_superuser(self):
        user = get_user_model().objects.create_superuser(
            username='production-admin', email='admin@example.com', password='strong-test-password'
        )

        call_command('bootstrap_admin', username=user.username, organization_name='Acme Corporation', slug='acme')

        organization = Organization.objects.get(slug='acme')
        membership = OrganizationMembership.objects.get(user=user, organization=organization)
        self.assertEqual(membership.role, OrganizationMembership.Role.OWNER)
        self.assertTrue(membership.is_active)
        self.assertEqual(organization.plan_code, Organization.Plan.FREE)
        self.assertEqual(organization.subscription_status, Organization.SubscriptionStatus.TRIALING)

    def test_bootstrap_refuses_non_superuser(self):
        user = get_user_model().objects.create_user(username='ordinary-user', password='password')

        with self.assertRaisesMessage(Exception, 'active superuser'):
            call_command('bootstrap_admin', username=user.username, organization_name='Acme Corporation', slug='acme')

    def test_bootstrap_does_not_reactivate_inactive_organization(self):
        user = get_user_model().objects.create_superuser(username='admin2', password='password')
        Organization.objects.create(name='Inactive Co', slug='inactive-co', is_active=False)

        with self.assertRaisesMessage(Exception, 'already exists but is inactive'):
            call_command('bootstrap_admin', username=user.username, organization_name='Inactive Co', slug='inactive-co')
