from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.organization.models import Organization

from .services import record_audit


class AuditEventTests(TestCase):
    def test_audit_event_records_actor_action_and_entity(self):
        organization = Organization.objects.create(name='Acme', slug='acme')
        actor = get_user_model().objects.create_user(username='auditor')

        event = record_audit(
            organization=organization,
            actor=actor,
            action='test.created',
            entity=organization,
            details={'source': 'test'},
        )

        self.assertEqual(event.actor, actor)
        self.assertEqual(event.entity_type, 'Organization')
        self.assertEqual(event.details, {'source': 'test'})


class HealthCheckTests(TestCase):
    def test_health_endpoint(self):
        response = self.client.get(reverse('health'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ok'})

    def test_readiness_endpoint_checks_database_and_cache(self):
        response = self.client.get(reverse('readiness'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ready', 'database': 'ok', 'cache': 'ok'})

    def test_legacy_client_site_route_is_removed(self):
        response = self.client.get('/client/high-speed-internet-support/')
        self.assertEqual(response.status_code, 404)
