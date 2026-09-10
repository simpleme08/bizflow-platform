from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from apps.organization.models import Organization, OrganizationMembership


class SubscriptionPastDueTests(TestCase):
    def test_past_due_owner_can_view_state(self):
        org = Organization.objects.create(name='Acme', slug='acme', subscription_status=Organization.SubscriptionStatus.PAST_DUE)
        user = get_user_model().objects.create_user(username='owner')
        OrganizationMembership.objects.create(organization=org, user=user, role=OrganizationMembership.Role.OWNER)
        client = Client(); client.force_login(user)
        response = client.get('/api/subscription/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['subscription']['status'], 'PAST_DUE')
