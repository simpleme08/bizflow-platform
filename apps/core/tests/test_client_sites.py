from django.test import TestCase

from apps.organization.models import Organization


class ClientWebsiteTests(TestCase):
    def test_hsis_landing_page_is_public(self):
        response = self.client.get('/client/high-speed-internet-support/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'High Speed Internet Support')
        self.assertContains(response, 'Parañaque')
        self.assertContains(response, 'Davao')
        self.assertContains(response, 'Sign in to HRIS')
        self.assertContains(response, 'Open Time Clock')

    def test_unknown_client_is_not_exposed(self):
        response = self.client.get('/client/does-not-exist/')
        self.assertEqual(response.status_code, 404)

    def test_tenant_profile_can_override_generic_content(self):
        Organization.objects.create(name='Demo Client', slug='demo-client')
        response = self.client.get('/client/demo-client/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Demo Client')
