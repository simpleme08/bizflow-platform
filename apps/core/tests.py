from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.organization.models import Organization

from .models import AuditEvent
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
