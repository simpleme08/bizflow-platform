from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from apps.organization.models import Organization, OrganizationMembership


class SubscriptionEndpointExtraTests(TestCase):
    def test_report_viewer_can_read_subscription(self):
        org = Organization.objects.create(name='Acme', slug='acme', plan_code=Organization.Plan.GROWTH)
        user = get_user_model().objects.create_user(username='ceo')
        OrganizationMembership.objects.create(organization=org, user=user, role=OrganizationMembership.Role.CEO)
        client = Client(); client.force_login(user)
        response = client.get('/api/subscription/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['plan']['code'], 'GROWTH')
