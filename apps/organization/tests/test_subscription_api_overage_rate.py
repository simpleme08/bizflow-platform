from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from apps.organization.models import Organization, OrganizationMembership


class SubscriptionOverageApiTests(TestCase):
    def test_configured_overage_rate_is_exposed(self):
        org = Organization.objects.create(name='Acme', slug='acme', overage_rate=Decimal('42.00'))
        user = get_user_model().objects.create_user(username='owner')
        OrganizationMembership.objects.create(organization=org, user=user, role=OrganizationMembership.Role.OWNER)
        client = Client(); client.force_login(user)
        self.assertEqual(client.get('/api/subscription/').json()['plan']['overage_per_employee'], '42.00')
