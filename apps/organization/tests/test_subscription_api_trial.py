from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.utils import timezone
from apps.organization.models import Organization, OrganizationMembership


class SubscriptionTrialApiTests(TestCase):
    def test_trial_end_is_exposed(self):
        end = timezone.now() + timedelta(days=14)
        org = Organization.objects.create(name='Acme', slug='acme', trial_ends_at=end)
        user = get_user_model().objects.create_user(username='owner')
        OrganizationMembership.objects.create(organization=org, user=user, role=OrganizationMembership.Role.OWNER)
        client = Client(); client.force_login(user)
        self.assertIsNotNone(client.get('/api/subscription/').json()['subscription']['trial_ends_at'])
