from django.contrib import admin

from .models import Client, ClientSite, ShiftTemplate


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
	list_display = ('code', 'name', 'organization', 'is_active')
	list_filter = ('organization', 'is_active')
	search_fields = ('code', 'name')


@admin.register(ClientSite)
class ClientSiteAdmin(admin.ModelAdmin):
	list_display = ('name', 'client', 'is_active')
	list_filter = ('client', 'is_active')
	search_fields = ('name', 'client__name')


@admin.register(ShiftTemplate)
class ShiftTemplateAdmin(admin.ModelAdmin):
	list_display = ('name', 'start_time', 'end_time')
	search_fields = ('name',)
