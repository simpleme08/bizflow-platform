from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from apps.organization.models import Organization, OrganizationMembership


class SubscriptionStatusApiTests(TestCase):
    def test_active_status_is_exposed(self):
        org = Organization.objects.create(name='Acme', slug='acme', subscription_status=Organization.SubscriptionStatus.ACTIVE)
        user = get_user_model().objects.create_user(username='owner')
        OrganizationMembership.objects.create(organization=org, user=user, role=OrganizationMembership.Role.OWNER)
        client = Client(); client.force_login(user)
        self.assertEqual(client.get('/api/subscription/').json()['subscription']['status'], 'ACTIVE')
