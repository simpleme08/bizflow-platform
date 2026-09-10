from django.db import models

from apps.core.models import BaseModel


class BillingSubscription(BaseModel):
    organization = models.ForeignKey('organization.Organization', on_delete=models.PROTECT, related_name='billing_subscriptions')
    provider = models.CharField(max_length=30, default='paymongo')
    provider_subscription_id = models.CharField(max_length=120, unique=True)
    provider_customer_id = models.CharField(max_length=120, blank=True)
    provider_plan_id = models.CharField(max_length=120, blank=True)
    plan_code = models.CharField(max_length=20)
    status = models.CharField(max_length=40)
    current_period_end = models.DateField(null=True, blank=True)
    canceled_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ('-created_at',)
        indexes = [
            models.Index(fields=('organization', 'status'), name='billingsub_org_status_idx'),
        ]


class BillingInvoice(BaseModel):
    organization = models.ForeignKey('organization.Organization', on_delete=models.PROTECT, related_name='billing_invoices')
    subscription = models.ForeignKey(BillingSubscription, null=True, blank=True, on_delete=models.SET_NULL, related_name='invoices')
    provider = models.CharField(max_length=30, default='paymongo')
    provider_invoice_id = models.CharField(max_length=120, unique=True)
    provider_payment_intent_id = models.CharField(max_length=120, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='PHP')
    status = models.CharField(max_length=30)
    due_date = models.DateField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    description = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ('-created_at',)
        indexes = [
            models.Index(fields=('organization', '-created_at'), name='billinginv_org_created_idx'),
        ]


class BillingWebhookEvent(BaseModel):
    provider = models.CharField(max_length=30, default='paymongo')
    provider_event_id = models.CharField(max_length=120, unique=True)
    event_type = models.CharField(max_length=100)
    livemode = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)
    payload = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ('-created_at',)
        indexes = [
            models.Index(fields=('event_type', '-created_at'), name='billingwh_type_created_idx'),
        ]
