from django.test import TestCase

from apps.organization.models import Organization

from .models import Client, ClientSite


class WorkforceStructureTests(TestCase):
	def test_client_site_belongs_to_client(self):
		organization = Organization.objects.create(name='Acme', slug='acme')
		client = Client.objects.create(organization=organization, code='ACME-CLIENT', name='Acme Client')
		site = ClientSite.objects.create(client=client, name='Main Site')

		self.assertEqual(client.sites.get(), site)
		self.assertEqual(str(site), 'Acme Client - Main Site')
