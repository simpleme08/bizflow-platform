from .models import AuditEvent


def record_audit(*, organization, actor, action, entity, details=None):
	return AuditEvent.objects.create(
		organization=organization,
		actor=actor,
		action=action,
		entity_type=entity.__class__.__name__,
		entity_id=str(entity.pk),
		details=details or {},
	)