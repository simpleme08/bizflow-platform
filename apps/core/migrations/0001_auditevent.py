import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
	initial = True
	dependencies = [('organization', '0003_costcenter_department_employmenttype_position'), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
	operations = [migrations.CreateModel(name='AuditEvent', fields=[('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)), ('created_at', models.DateTimeField(auto_now_add=True)), ('updated_at', models.DateTimeField(auto_now=True)), ('action', models.CharField(max_length=80)), ('entity_type', models.CharField(max_length=80)), ('entity_id', models.CharField(max_length=80)), ('details', models.JSONField(blank=True, default=dict)), ('actor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='audit_events', to=settings.AUTH_USER_MODEL)), ('organization', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='audit_events', to='organization.organization'))], options={'ordering': ('-created_at',), 'indexes': [models.Index(fields=['organization', '-created_at'], name='audit_org_created_idx')]})]