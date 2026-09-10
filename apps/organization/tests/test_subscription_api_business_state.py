from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from apps.organization.models import Organization, OrganizationMembership


class BusinessSubscriptionStateTests(TestCase):
    def test_business_active_subscription(self):
        org = Organization.objects.create(name='Acme', slug='acme', plan_code=Organization.Plan.BUSINESS, subscription_status=Organization.SubscriptionStatus.ACTIVE)
        user = get_user_model().objects.create_user(username='owner')
        OrganizationMembership.objects.create(organization=org, user=user, role=OrganizationMembership.Role.OWNER)
        client = Client(); client.force_login(user)
        payload = client.get('/api/subscription/').json()
        self.assertEqual(payload['plan']['employee_limit'], 75)
        self.assertEqual(payload['subscription']['status'], 'ACTIVE')
