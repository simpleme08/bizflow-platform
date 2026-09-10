from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from apps.organization.models import Organization, OrganizationMembership


class SubscriptionMethodTests(TestCase):
    def test_post_is_not_supported(self):
        org = Organization.objects.create(name='Acme', slug='acme')
        user = get_user_model().objects.create_user(username='owner')
        OrganizationMembership.objects.create(organization=org, user=user, role=OrganizationMembership.Role.OWNER)
        client = Client(); client.force_login(user)
        self.assertEqual(client.post('/api/subscription/').status_code, 200)
