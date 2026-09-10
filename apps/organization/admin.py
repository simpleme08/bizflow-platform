from django.contrib import admin

from .billing_models import BillingInvoice, BillingSubscription, BillingWebhookEvent
from .models import CostCenter, Department, EmploymentType, Organization, OrganizationMembership, Position


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('name', 'plan_code', 'subscription_status', 'is_active', 'overage_rate')
    list_filter = ('plan_code', 'subscription_status', 'is_active')
    search_fields = ('name', 'slug', 'billing_customer_id')


@admin.register(BillingSubscription)
class BillingSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('organization', 'plan_code', 'status', 'provider_subscription_id', 'current_period_end')
    list_filter = ('provider', 'plan_code', 'status')
    search_fields = ('organization__name', 'provider_subscription_id', 'provider_customer_id')


@admin.register(BillingInvoice)
class BillingInvoiceAdmin(admin.ModelAdmin):
    list_display = ('organization', 'amount', 'currency', 'status', 'due_date', 'paid_at')
    list_filter = ('provider', 'currency', 'status')
    search_fields = ('organization__name', 'provider_invoice_id', 'provider_payment_intent_id')


@admin.register(BillingWebhookEvent)
class BillingWebhookEventAdmin(admin.ModelAdmin):
    list_display = ('provider_event_id', 'event_type', 'livemode', 'processed_at', 'created_at')
    list_filter = ('provider', 'event_type', 'livemode')
    search_fields = ('provider_event_id', 'event_type')


admin.site.register(OrganizationMembership)
admin.site.register(Department)
admin.site.register(Position)
admin.site.register(EmploymentType)
admin.site.register(CostCenter)
