import hashlib
import hmac
import json
from datetime import datetime, timezone as dt_timezone

from django.conf import settings
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from apps.core.models import AuditEvent
from apps.organization.billing import get_plan
from apps.organization.billing_models import BillingInvoice, BillingSubscription, BillingWebhookEvent
from apps.organization.context import current_membership
from apps.organization.paymongo import PayMongoClient, PayMongoError


def _membership(request):
    return current_membership(request)


def _authorized(request, permission='manage_organization'):
    membership = _membership(request)
    if membership is None or not membership.has_permission(permission):
        return None
    return membership


def _plan_id(plan_code):
    return getattr(settings, f'PAYMONGO_PLAN_{plan_code}', '')


def _invoice_from_provider(organization, subscription, invoice):
    data = invoice.get('data', {})
    attrs = data.get('attributes', {})
    payment_intent = attrs.get('payment_intent') or {}
    payment_intent_id = payment_intent.get('id', '') if isinstance(payment_intent, dict) else payment_intent
    obj, _ = BillingInvoice.objects.update_or_create(
        provider_invoice_id=data.get('id', ''),
        defaults={
            'organization': organization,
            'subscription': subscription,
            'provider': 'paymongo',
            'provider_payment_intent_id': payment_intent_id or '',
            'amount': (attrs.get('amount') or 0) / 100,
            'currency': attrs.get('currency', 'PHP'),
            'status': attrs.get('status', 'open'),
            'due_date': attrs.get('due_date'),
            'description': attrs.get('description', ''),
            'metadata': attrs,
        },
    )
    return obj, payment_intent


def billing_checkout(request):
    if request.method != 'POST':
        return JsonResponse({'detail': 'Method not allowed.'}, status=405)
    membership = _authorized(request)
    if membership is None:
        return JsonResponse({'detail': 'Permission denied.'}, status=403)
    try:
        payload = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'detail': 'Invalid JSON.'}, status=400)

    plan_code = str(payload.get('plan_code', '')).upper()
    if plan_code not in {'STARTER', 'GROWTH', 'BUSINESS'}:
        return JsonResponse({'detail': 'Only paid plans can be checked out.'}, status=400)
    plan = get_plan(plan_code)
    plan_id = _plan_id(plan_code)
    if not plan_id:
        return JsonResponse({'detail': f'PayMongo plan is not configured for {plan_code}.'}, status=503)

    organization = membership.organization
    try:
        client = PayMongoClient()
        user = request.user
        first_name = getattr(user, 'first_name', '') or organization.name
        last_name = getattr(user, 'last_name', '') or 'Admin'
        customer_id = organization.billing_customer_id
        if not customer_id:
            customer = client.create_customer(email=user.email, first_name=first_name, last_name=last_name)
            customer_id = customer['data']['id']
            organization.billing_customer_id = customer_id
            organization.save(update_fields=['billing_customer_id', 'updated_at'])

        existing = BillingSubscription.objects.filter(
            organization=organization,
            status__in=['incomplete', 'active', 'past_due', 'unpaid'],
        ).order_by('-created_at').first()
        if existing and existing.plan_code == plan_code:
            subscription_id = existing.provider_subscription_id
            provider_subscription = {'data': {'id': subscription_id, 'attributes': {'status': existing.status}}}
        elif existing:
            provider_subscription = client.update_subscription_plan(existing.provider_subscription_id, plan_id)
            subscription_id = provider_subscription['data']['id']
        else:
            provider_subscription = client.create_subscription(plan_id=plan_id, customer_id=customer_id)
            subscription_id = provider_subscription['data']['id']

        attrs = provider_subscription['data'].get('attributes', {})
        status = attrs.get('status', 'incomplete')
        subscription, _ = BillingSubscription.objects.update_or_create(
            provider_subscription_id=subscription_id,
            defaults={
                'organization': organization,
                'provider_customer_id': customer_id,
                'provider_plan_id': plan_id,
                'plan_code': plan_code,
                'status': status,
                'current_period_end': attrs.get('next_billing_schedule'),
                'canceled_at': None,
                'metadata': attrs,
            },
        )
        latest_invoice = attrs.get('latest_invoice') or {}
        if latest_invoice.get('id'):
            invoice, payment_intent = _invoice_from_provider(organization, subscription, {'data': {'id': latest_invoice['id'], 'attributes': latest_invoice}})
            client_key = payment_intent.get('attributes', {}).get('client_key') if isinstance(payment_intent, dict) else None
            payment_intent_id = payment_intent.get('id') if isinstance(payment_intent, dict) else payment_intent
        else:
            invoice = None
            client_key = None
            payment_intent_id = None

        AuditEvent.objects.create(
            organization=organization,
            actor=request.user,
            action='BILLING_CHECKOUT_STARTED',
            entity_type='BillingSubscription',
            entity_id=subscription.id,
            details={'plan_code': plan_code, 'provider': 'paymongo', 'provider_subscription_id': subscription_id},
        )
        return JsonResponse({
            'provider': 'paymongo',
            'plan_code': plan_code,
            'amount_php': str(plan.monthly_price),
            'subscription_id': subscription_id,
            'subscription_status': status,
            'invoice_id': invoice.provider_invoice_id if invoice else None,
            'payment_intent_id': payment_intent_id,
            'payment_intent_client_key': client_key,
            'public_key': getattr(settings, 'PAYMONGO_PUBLIC_KEY', ''),
            'next_step': 'Complete the first invoice payment using the returned payment intent client key.' if client_key else 'Complete payment using the latest PayMongo invoice/payment flow.',
        })
    except (PayMongoError, KeyError) as exc:
        return JsonResponse({'detail': str(exc)}, status=502)


def billing_change_plan(request):
    if request.method != 'POST':
        return JsonResponse({'detail': 'Method not allowed.'}, status=405)
    membership = _authorized(request)
    if membership is None:
        return JsonResponse({'detail': 'Permission denied.'}, status=403)
    try:
        payload = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'detail': 'Invalid JSON.'}, status=400)
    plan_code = str(payload.get('plan_code', '')).upper()
    if plan_code not in {'STARTER', 'GROWTH', 'BUSINESS'} or not _plan_id(plan_code):
        return JsonResponse({'detail': 'A configured paid plan is required.'}, status=400)
    subscription = BillingSubscription.objects.filter(
        organization=membership.organization,
        status__in=['incomplete', 'active', 'past_due', 'unpaid'],
    ).order_by('-created_at').first()
    if subscription is None:
        return JsonResponse({'detail': 'No active provider subscription found.'}, status=404)
    try:
        result = PayMongoClient().update_subscription_plan(subscription.provider_subscription_id, _plan_id(plan_code))
        attrs = result['data'].get('attributes', {})
        subscription.plan_code = plan_code
        subscription.provider_plan_id = _plan_id(plan_code)
        subscription.status = attrs.get('status', subscription.status)
        subscription.metadata = attrs
        subscription.save(update_fields=['plan_code', 'provider_plan_id', 'status', 'metadata', 'updated_at'])
        AuditEvent.objects.create(organization=membership.organization, actor=request.user, action='BILLING_PLAN_CHANGED', entity_type='BillingSubscription', entity_id=subscription.id, details={'plan_code': plan_code})
        return JsonResponse({'subscription_status': subscription.status, 'plan_code': plan_code})
    except PayMongoError as exc:
        return JsonResponse({'detail': str(exc)}, status=502)


def billing_cancel(request):
    if request.method != 'POST':
        return JsonResponse({'detail': 'Method not allowed.'}, status=405)
    membership = _authorized(request)
    if membership is None:
        return JsonResponse({'detail': 'Permission denied.'}, status=403)
    subscription = BillingSubscription.objects.filter(
        organization=membership.organization,
        status__in=['incomplete', 'active', 'past_due', 'unpaid'],
    ).order_by('-created_at').first()
    if subscription is None:
        return JsonResponse({'detail': 'No cancellable subscription found.'}, status=404)
    try:
        result = PayMongoClient().cancel_subscription(subscription.provider_subscription_id)
        attrs = result['data'].get('attributes', {})
        subscription.status = attrs.get('status', 'cancelled')
        subscription.canceled_at = timezone.now()
        subscription.metadata = attrs
        subscription.save(update_fields=['status', 'canceled_at', 'metadata', 'updated_at'])
        AuditEvent.objects.create(organization=membership.organization, actor=request.user, action='BILLING_SUBSCRIPTION_CANCELED', entity_type='BillingSubscription', entity_id=subscription.id, details={})
        return JsonResponse({'status': subscription.status})
    except PayMongoError as exc:
        return JsonResponse({'detail': str(exc)}, status=502)


def billing_invoices(request):
    membership = _authorized(request, 'view_reports')
    if membership is None:
        return JsonResponse({'detail': 'Permission denied.'}, status=403)
    invoices = BillingInvoice.objects.filter(organization=membership.organization).select_related('subscription')[:100]
    return JsonResponse({'invoices': [
        {
            'id': str(item.id), 'provider_invoice_id': item.provider_invoice_id,
            'subscription_id': item.subscription.provider_subscription_id if item.subscription else None,
            'amount': str(item.amount), 'currency': item.currency, 'status': item.status,
            'due_date': item.due_date.isoformat() if item.due_date else None,
            'paid_at': item.paid_at.isoformat() if item.paid_at else None,
            'description': item.description,
        } for item in invoices
    ]})


def _verify_webhook(request):
    secret = getattr(settings, 'PAYMONGO_WEBHOOK_SECRET', '')
    signature = request.headers.get('Paymongo-Signature', '')
    if not secret or not signature:
        return False
    parts = dict(item.split('=', 1) for item in signature.split(',') if '=' in item)
    timestamp = parts.get('t')
    provided = parts.get('li') if getattr(settings, 'PAYMONGO_LIVEMODE', False) else parts.get('te')
    if not timestamp or not provided:
        return False
    try:
        if abs(int(datetime.now(dt_timezone.utc).timestamp()) - int(timestamp)) > 300:
            return False
    except ValueError:
        return False
    signed = f'{timestamp}.{request.body.decode()}'
    expected = hmac.new(secret.encode(), signed.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, provided)


@csrf_exempt
def paymongo_webhook(request):
    if request.method != 'POST':
        return JsonResponse({'detail': 'Method not allowed.'}, status=405)
    if not _verify_webhook(request):
        return JsonResponse({'detail': 'Invalid webhook signature.'}, status=400)
    try:
        payload = json.loads(request.body)
        event = payload['data']
        attrs = event['attributes']
        event_id = event['id']
        event_type = attrs['type']
    except (ValueError, KeyError, TypeError):
        return JsonResponse({'detail': 'Invalid webhook payload.'}, status=400)

    with transaction.atomic():
        webhook, created = BillingWebhookEvent.objects.get_or_create(
            provider_event_id=event_id,
            defaults={'event_type': event_type, 'livemode': bool(attrs.get('livemode')), 'payload': payload},
        )
        if not created and webhook.processed_at:
            return JsonResponse({'received': True, 'duplicate': True})

        resource = attrs.get('data') or {}
        resource_attrs = resource.get('attributes') or {}
        subscription_id = resource.get('id') if resource.get('type') == 'subscription' else resource_attrs.get('resource_id')
        subscription = BillingSubscription.objects.filter(provider_subscription_id=subscription_id).select_related('organization').first() if subscription_id else None

        if subscription:
            status_map = {
                'subscription.activated': 'active',
                'subscription.past_due': 'past_due',
                'subscription.unpaid': 'unpaid',
                'subscription.updated': resource_attrs.get('status'),
            }
            new_status = status_map.get(event_type)
            if new_status:
                subscription.status = new_status
                subscription.metadata = resource_attrs
                subscription.current_period_end = resource_attrs.get('next_billing_schedule') or subscription.current_period_end
                if new_status == 'cancelled':
                    subscription.canceled_at = timezone.now()
                subscription.save(update_fields=['status', 'metadata', 'current_period_end', 'canceled_at', 'updated_at'])
                org = subscription.organization
                org.subscription_status = {
                    'active': 'ACTIVE', 'past_due': 'PAST_DUE', 'unpaid': 'PAST_DUE', 'cancelled': 'CANCELED',
                }.get(new_status, org.subscription_status)
                if new_status == 'active':
                    org.plan_code = subscription.plan_code
                org.save(update_fields=['subscription_status', 'plan_code', 'updated_at'])
                AuditEvent.objects.create(organization=org, actor=None, action='BILLING_WEBHOOK_PROCESSED', entity_type='BillingSubscription', entity_id=subscription.id, details={'event_type': event_type, 'status': new_status})

            if event_type.startswith('subscription.invoice.'):
                invoice, _ = BillingInvoice.objects.update_or_create(
                    provider_invoice_id=resource.get('id', ''),
                    defaults={
                        'organization': subscription.organization,
                        'subscription': subscription,
                        'provider': 'paymongo',
                        'provider_payment_intent_id': (resource_attrs.get('payment_intent') or {}).get('id', ''),
                        'amount': (resource_attrs.get('amount') or 0) / 100,
                        'currency': resource_attrs.get('currency', 'PHP'),
                        'status': resource_attrs.get('status', 'open'),
                        'due_date': resource_attrs.get('due_date'),
                        'description': resource_attrs.get('description', ''),
                        'metadata': resource_attrs,
                    },
                )
                if event_type == 'subscription.invoice.paid':
                    invoice.paid_at = timezone.now()
                    invoice.save(update_fields=['paid_at', 'updated_at'])

        webhook.processed_at = timezone.now()
        webhook.payload = payload
        webhook.save(update_fields=['processed_at', 'payload', 'updated_at'])
    return JsonResponse({'received': True})
