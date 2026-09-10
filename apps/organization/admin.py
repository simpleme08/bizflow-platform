from django.contrib import admin

from .models import CostCenter, Department, EmploymentType, Organization, OrganizationMembership, Position


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('name', 'plan_code', 'subscription_status', 'is_active', 'overage_rate')
    list_filter = ('plan_code', 'subscription_status', 'is_active')
    search_fields = ('name', 'slug', 'billing_customer_id')


admin.site.register(OrganizationMembership)
admin.site.register(Department)
admin.site.register(Position)
admin.site.register(EmploymentType)
admin.site.register(CostCenter)
