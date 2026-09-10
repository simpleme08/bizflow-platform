from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from apps.organization.models import Organization, OrganizationMembership


class SubscriptionEndpointFinalTests(TestCase):
    def test_response_contains_usage_contract(self):
        org = Organization.objects.create(name='Acme', slug='acme')
        user = get_user_model().objects.create_user(username='owner')
        OrganizationMembership.objects.create(organization=org, user=user, role=OrganizationMembership.Role.OWNER)
        client = Client(); client.force_login(user)
        payload = client.get('/api/subscription/').json()
        self.assertEqual(set(payload['usage']), {'active_employees', 'remaining_employee_slots', 'over_limit'})
