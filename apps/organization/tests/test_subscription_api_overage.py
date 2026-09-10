from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from apps.organization.models import Organization, OrganizationMembership


class SubscriptionOverLimitTests(TestCase):
    def test_usage_reports_over_limit_state(self):
        org = Organization.objects.create(name='Acme', slug='acme', plan_code=Organization.Plan.FREE)
        user = get_user_model().objects.create_user(username='owner')
        OrganizationMembership.objects.create(organization=org, user=user, role=OrganizationMembership.Role.OWNER)
        client = Client(); client.force_login(user)
        response = client.get('/api/subscription/')
        self.assertEqual(response.json()['usage']['over_limit'], False)
