from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from apps.organization.models import Organization, OrganizationMembership


class SubscriptionInactiveOrganizationTests(TestCase):
    def test_inactive_org_has_no_active_membership(self):
        org = Organization.objects.create(name='Acme', slug='acme', is_active=False)
        user = get_user_model().objects.create_user(username='owner')
        OrganizationMembership.objects.create(organization=org, user=user, role=OrganizationMembership.Role.OWNER)
        client = Client(); client.force_login(user)
        self.assertEqual(client.get('/api/subscription/').status_code, 403)
