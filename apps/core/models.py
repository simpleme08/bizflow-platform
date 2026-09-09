import uuid

from django.conf import settings
from django.db import models


class BaseModel(models.Model):
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		abstract = True


class AuditEvent(BaseModel):
	organization = models.ForeignKey('organization.Organization', on_delete=models.PROTECT, related_name='audit_events')
	actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='audit_events')
	action = models.CharField(max_length=80)
	entity_type = models.CharField(max_length=80)
	entity_id = models.CharField(max_length=80)
	details = models.JSONField(default=dict, blank=True)

	class Meta:
		ordering = ('-created_at',)
		indexes = [models.Index(fields=('organization', '-created_at'), name='audit_org_created_idx')]

	def __str__(self):
		return f'{self.action} {self.entity_type} {self.entity_id}'
