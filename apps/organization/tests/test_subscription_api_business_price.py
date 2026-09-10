from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from apps.organization.models import Organization, OrganizationMembership


class BusinessPlanPriceApiTests(TestCase):
    def test_business_plan_price(self):
        org = Organization.objects.create(name='Acme', slug='acme', plan_code=Organization.Plan.BUSINESS)
        user = get_user_model().objects.create_user(username='owner')
        OrganizationMembership.objects.create(organization=org, user=user, role=OrganizationMembership.Role.OWNER)
        client = Client(); client.force_login(user)
        self.assertEqual(client.get('/api/subscription/').json()['plan']['monthly_price'], '2999.00')
