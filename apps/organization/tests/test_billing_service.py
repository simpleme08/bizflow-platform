from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

from apps.organization.billing_service import subscription_allows_operations
from apps.organization.models import Organization


class BillingServiceTests(TestCase):
    def test_active_and_past_due_allow_operations(self):
        org = Organization.objects.create(name='Acme', slug='acme', subscription_status=Organization.SubscriptionStatus.ACTIVE)
        self.assertTrue(subscription_allows_operations(org))
        org.subscription_status = Organization.SubscriptionStatus.PAST_DUE
        org.save(update_fields=['subscription_status'])
        self.assertTrue(subscription_allows_operations(org))

    def test_canceled_does_not_allow_operations(self):
        org = Organization.objects.create(name='Acme', slug='acme', subscription_status=Organization.SubscriptionStatus.CANCELED)
        self.assertFalse(subscription_allows_operations(org))
