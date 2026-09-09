from django.contrib import admin

from .models import AuditEvent


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
	list_display = ('created_at', 'action', 'entity_type', 'entity_id', 'actor', 'organization')
	list_filter = ('action', 'entity_type', 'organization')
	search_fields = ('entity_id', 'actor__username')
	readonly_fields = ('organization', 'actor', 'action', 'entity_type', 'entity_id', 'details', 'created_at', 'updated_at')
