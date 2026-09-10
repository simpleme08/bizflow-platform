from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from apps.organization.models import Organization, OrganizationMembership


class SubscriptionShapeTests(TestCase):
    def test_plan_and_subscription_sections_exist(self):
        org = Organization.objects.create(name='Acme', slug='acme')
        user = get_user_model().objects.create_user(username='owner')
        OrganizationMembership.objects.create(organization=org, user=user, role=OrganizationMembership.Role.OWNER)
        client = Client(); client.force_login(user)
        payload = client.get('/api/subscription/').json()
        self.assertIn('plan', payload)
        self.assertIn('subscription', payload)
