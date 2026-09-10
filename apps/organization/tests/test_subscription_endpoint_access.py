from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from apps.organization.models import Organization, OrganizationMembership


class SubscriptionEndpointAccessTests(TestCase):
    def test_employee_cannot_view_billing_state(self):
        org = Organization.objects.create(name='Acme', slug='acme')
        user = get_user_model().objects.create_user(username='employee')
        OrganizationMembership.objects.create(organization=org, user=user, role=OrganizationMembership.Role.EMPLOYEE)
        client = Client(); client.force_login(user)
        self.assertEqual(client.get('/api/subscription/').status_code, 403)
