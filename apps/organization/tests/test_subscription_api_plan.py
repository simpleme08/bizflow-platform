from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from apps.organization.models import Organization, OrganizationMembership


class StarterPlanApiTests(TestCase):
    def test_starter_limit_is_exposed(self):
        org = Organization.objects.create(name='Acme', slug='acme', plan_code=Organization.Plan.STARTER)
        user = get_user_model().objects.create_user(username='owner')
        OrganizationMembership.objects.create(organization=org, user=user, role=OrganizationMembership.Role.OWNER)
        client = Client(); client.force_login(user)
        self.assertEqual(client.get('/api/subscription/').json()['plan']['employee_limit'], 10)
