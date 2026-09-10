from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from apps.organization.billing_service import activation_allowed
from apps.organization.models import Organization


class BillingTrialTests(TestCase):
    def test_expired_trial_cannot_activate(self):
        org = Organization.objects.create(name='Acme', slug='acme', subscription_status=Organization.SubscriptionStatus.TRIALING, trial_ends_at=timezone.now() - timedelta(seconds=1))
        self.assertFalse(activation_allowed(org))
