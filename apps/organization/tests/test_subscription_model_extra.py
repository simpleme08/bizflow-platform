from decimal import Decimal
from django.test import TestCase
from apps.organization.models import Organization


class SubscriptionConfigurationTests(TestCase):
    def test_overage_rate_is_configurable(self):
        org = Organization.objects.create(name='Acme', slug='acme', overage_rate=Decimal('37.50'))
        self.assertEqual(org.overage_rate, Decimal('37.50'))
