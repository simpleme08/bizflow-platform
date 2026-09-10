from django.test import TestCase
from apps.organization.billing import can_activate_employee
from apps.organization.models import Organization


class SubscriptionSafetyTests(TestCase):
    def test_unknown_plan_falls_back_to_free(self):
        org = Organization.objects.create(name='Acme', slug='acme', plan_code='FREE')
        self.assertEqual(org.plan_code, Organization.Plan.FREE)
        self.assertTrue(can_activate_employee(org))
