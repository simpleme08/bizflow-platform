from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from apps.organization.models import Organization, OrganizationMembership


class SubscriptionInactiveMembershipTests(TestCase):
    def test_inactive_membership_is_rejected(self):
        org = Organization.objects.create(name='Acme', slug='acme')
        user = get_user_model().objects.create_user(username='admin')
        OrganizationMembership.objects.create(organization=org, user=user, role=OrganizationMembership.Role.OWNER, is_active=False)
        client = Client(); client.force_login(user)
        self.assertEqual(client.get('/api/subscription/').status_code, 403)
