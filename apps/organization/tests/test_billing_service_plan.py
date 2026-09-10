from django.test import TestCase
from apps.organization.billing_service import activation_allowed
from apps.organization.models import Organization


class BillingPlanCapacityTests(TestCase):
    def test_free_plan_allows_activation_when_empty(self):
        org = Organization.objects.create(name='Acme', slug='acme', subscription_status=Organization.SubscriptionStatus.ACTIVE)
        self.assertTrue(activation_allowed(org))
