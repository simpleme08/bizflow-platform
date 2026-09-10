from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from apps.organization.models import Organization, OrganizationMembership


class GrowthPlanPriceApiTests(TestCase):
    def test_growth_plan_price(self):
        org = Organization.objects.create(name='Acme', slug='acme', plan_code=Organization.Plan.GROWTH)
        user = get_user_model().objects.create_user(username='owner')
        OrganizationMembership.objects.create(organization=org, user=user, role=OrganizationMembership.Role.OWNER)
        client = Client(); client.force_login(user)
        self.assertEqual(client.get('/api/subscription/').json()['plan']['monthly_price'], '1499.00')
