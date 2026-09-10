from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from apps.organization.models import Organization, OrganizationMembership


class SubscriptionPermissionTests(TestCase):
    def test_manager_without_report_permission_is_denied(self):
        org = Organization.objects.create(name='Acme', slug='acme')
        user = get_user_model().objects.create_user(username='manager')
        OrganizationMembership.objects.create(organization=org, user=user, role=OrganizationMembership.Role.MANAGER)
        client = Client(); client.force_login(user)
        self.assertEqual(client.get('/api/subscription/').status_code, 403)
