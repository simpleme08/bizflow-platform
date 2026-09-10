from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from apps.organization.models import Organization, OrganizationMembership


class SubscriptionCustomerPrivacyTests(TestCase):
    def test_customer_id_is_boolean_only(self):
        org = Organization.objects.create(name='Acme', slug='acme', billing_customer_id='cus_private_123')
        user = get_user_model().objects.create_user(username='owner')
        OrganizationMembership.objects.create(organization=org, user=user, role=OrganizationMembership.Role.OWNER)
        client = Client(); client.force_login(user)
        payload = client.get('/api/subscription/').json()
        self.assertTrue(payload['subscription']['billing_customer_id'])
        self.assertNotIn('cus_private_123', str(payload))
