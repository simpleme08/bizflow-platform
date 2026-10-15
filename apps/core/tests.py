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


class InspectionDemoSeedSetupTests(TestCase):
    def test_seed_demo_runs_with_password_reset_enabled_and_restores_environment(self):
        import os
        from unittest.mock import patch
        from apps.core.management.commands.seed_inspection_demo import Command

        with patch.dict(os.environ, {'BIZFLOW_DEMO_RESET_PASSWORDS': 'false'}):
            with patch('apps.core.management.commands.seed_inspection_demo.call_command') as call_command:
                Command._seed_demo_with_synced_passwords()
                call_command.assert_called_once_with('seed_demo')
                self.assertEqual(os.environ.get('BIZFLOW_DEMO_RESET_PASSWORDS'), 'false')

    def test_seed_demo_removes_temporary_password_reset_flag_when_unset_before_call(self):
        import os
        from unittest.mock import patch
        from apps.core.management.commands.seed_inspection_demo import Command

        with patch.dict(os.environ):
            os.environ.pop('BIZFLOW_DEMO_RESET_PASSWORDS', None)
            with patch('apps.core.management.commands.seed_inspection_demo.call_command') as call_command:
                Command._seed_demo_with_synced_passwords()
                call_command.assert_called_once_with('seed_demo')
                self.assertNotIn('BIZFLOW_DEMO_RESET_PASSWORDS', os.environ)
