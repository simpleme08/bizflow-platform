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



class Notification(BaseModel):
    class Channel(models.TextChoices):
        EMAIL = 'EMAIL', 'Email'
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        SENT = 'SENT', 'Sent'
        FAILED = 'FAILED', 'Failed'

    organization = models.ForeignKey('organization.Organization', on_delete=models.CASCADE, related_name='notifications')
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    event = models.CharField(max_length=80)
    subject = models.CharField(max_length=200)
    body = models.TextField()
    channel = models.CharField(max_length=20, choices=Channel.choices, default=Channel.EMAIL)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    attempts = models.PositiveIntegerField(default=0)
    last_error = models.TextField(blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=('status', 'created_at'), name='notification_status_created_idx')]
