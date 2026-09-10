from django.test import TestCase
from apps.organization.billing_service import subscription_allows_operations
from apps.organization.models import Organization


class BillingInactiveOrgTests(TestCase):
    def test_inactive_organization_is_blocked(self):
        org = Organization.objects.create(name='Acme', slug='acme', is_active=False, subscription_status=Organization.SubscriptionStatus.ACTIVE)
        self.assertFalse(subscription_allows_operations(org))
