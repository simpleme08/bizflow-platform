from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from apps.organization.models import Organization, OrganizationMembership


class SubscriptionHrVisibilityTests(TestCase):
    def test_hr_can_view_subscription(self):
        org = Organization.objects.create(name='Acme', slug='acme')
        user = get_user_model().objects.create_user(username='hr')
        OrganizationMembership.objects.create(organization=org, user=user, role=OrganizationMembership.Role.HR)
        client = Client(); client.force_login(user)
        self.assertEqual(client.get('/api/subscription/').status_code, 200)
