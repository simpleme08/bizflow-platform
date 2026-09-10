from decimal import Decimal
from django.test import TestCase
from apps.organization.models import Organization


class SubscriptionModelTests(TestCase):
    def test_subscription_defaults(self):
        org = Organization.objects.create(name='Acme', slug='acme')
        self.assertEqual(org.plan_code, Organization.Plan.FREE)
        self.assertEqual(org.subscription_status, Organization.SubscriptionStatus.TRIALING)
        self.assertEqual(org.overage_rate, Decimal('50.00'))
