from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings

from apps.organization.models import Organization, OrganizationMembership


@override_settings(CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}})
class LoginHardeningTests(TestCase):
    def setUp(self):
        cache.clear()
        User = get_user_model()
        self.user = User.objects.create_user(username='login-user', password='correct-password')
        organization = Organization.objects.create(name='Login Test Co', slug='login-test')
        OrganizationMembership.objects.create(
            organization=organization,
            user=self.user,
            role=OrganizationMembership.Role.HR,
        )

    def tearDown(self):
        cache.clear()

    def test_failed_logins_are_throttled(self):
        for _ in range(5):
            response = self.client.post('/login/', {'username': 'login-user', 'password': 'wrong-password'})
            self.assertEqual(response.status_code, 401)
        response = self.client.post('/login/', {'username': 'login-user', 'password': 'wrong-password'})
        self.assertEqual(response.status_code, 429)

    def test_successful_login_clears_failed_attempts(self):
        for _ in range(4):
            response = self.client.post('/login/', {'username': 'login-user', 'password': 'wrong-password'})
            self.assertEqual(response.status_code, 401)
        response = self.client.post('/login/', {'username': 'login-user', 'password': 'correct-password'})
        self.assertEqual(response.status_code, 302)
        self.client.logout()
        for _ in range(5):
            response = self.client.post('/login/', {'username': 'login-user', 'password': 'wrong-password'})
            self.assertEqual(response.status_code, 401)
