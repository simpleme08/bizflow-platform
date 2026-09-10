from django.test import TestCase
from apps.organization.models import Organization


class SubscriptionPlanSwitchTests(TestCase):
    def test_downgrade_does_not_disable_organization(self):
        org = Organization.objects.create(name='Acme', slug='acme', plan_code=Organization.Plan.BUSINESS)
        org.plan_code = Organization.Plan.FREE
        org.save(update_fields=['plan_code'])
        org.refresh_from_db()
        self.assertTrue(org.is_active)
        self.assertEqual(org.plan_code, Organization.Plan.FREE)
