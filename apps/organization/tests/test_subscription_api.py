from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from apps.organization.models import Organization, OrganizationMembership


class SubscriptionApiTests(TestCase):
    def test_authorized_user_can_view_usage(self):
        org = Organization.objects.create(name='Acme', slug='acme')
        user = get_user_model().objects.create_user(username='owner')
        OrganizationMembership.objects.create(organization=org, user=user, role=OrganizationMembership.Role.OWNER)
        client = Client()
        client.force_login(user)
        response = client.get('/api/subscription/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['plan']['employee_limit'], 5)
        self.assertEqual(response.json()['usage']['active_employees'], 0)

    def test_unauthenticated_is_rejected(self):
        response = Client().get('/api/subscription/')
        self.assertEqual(response.status_code, 401)
