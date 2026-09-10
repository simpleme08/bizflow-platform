import hashlib
import hmac
import json
import time

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.organization.billing_models import BillingSubscription, BillingWebhookEvent
from apps.organization.models import Organization, OrganizationMembership


@override_settings(PAYMONGO_WEBHOOK_SECRET='test-webhook-secret', PAYMONGO_LIVEMODE=False)
class PayMongoWebhookTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name='Acme', slug='acme')
        self.subscription = BillingSubscription.objects.create(
            organization=self.organization,
            provider_subscription_id='subs_test_123',
            provider_customer_id='cus_test_123',
            provider_plan_id='plan_growth',
            plan_code='GROWTH',
            status='active',
        )

    def _post(self, payload, secret='test-webhook-secret'):
        raw = json.dumps(payload, separators=(',', ':')).encode()
        timestamp = str(int(time.time()))
        signature = hmac.new(secret.encode(), f'{timestamp}.{raw.decode()}'.encode(), hashlib.sha256).hexdigest()
        return self.client.post(
            reverse('paymongo-webhook'),
            data=raw,
            content_type='application/json',
            HTTP_PAYMONGO_SIGNATURE=f't={timestamp},te={signature},li=',
        )

    def test_invalid_signature_is_rejected(self):
        payload = {'data': {'id': 'evt_bad', 'attributes': {'type': 'subscription.activated', 'data': {}}}}
        response = self.client.post(
            reverse('paymongo-webhook'), data=json.dumps(payload), content_type='application/json',
            HTTP_PAYMONGO_SIGNATURE='t=1,te=bad,li=',
        )
        self.assertEqual(response.status_code, 400)

    def test_subscription_event_updates_org_and_is_idempotent(self):
        payload = {'data': {'id': 'evt_123', 'attributes': {
            'type': 'subscription.past_due', 'livemode': False,
            'data': {'id': 'subs_test_123', 'type': 'subscription', 'attributes': {
                'status': 'past_due', 'next_billing_schedule': '2026-10-10'
            }}
        }}}
        response = self._post(payload)
        self.assertEqual(response.status_code, 200)
        self.subscription.refresh_from_db()
        self.organization.refresh_from_db()
        self.assertEqual(self.subscription.status, 'past_due')
        self.assertEqual(self.organization.subscription_status, 'PAST_DUE')
        self.assertEqual(BillingWebhookEvent.objects.count(), 1)

        duplicate = self._post(payload)
        self.assertEqual(duplicate.status_code, 200)
        self.assertEqual(BillingWebhookEvent.objects.count(), 1)


class BillingTenantAccessTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username='admin', password='password', email='admin@example.com')
        self.org_a = Organization.objects.create(name='A', slug='org-a')
        self.org_b = Organization.objects.create(name='B', slug='org-b')
        OrganizationMembership.objects.create(organization=self.org_a, user=self.user, role='ADMIN')
        BillingSubscription.objects.create(organization=self.org_b, provider_subscription_id='subs_other', plan_code='GROWTH', status='active')
        self.client.login(username='admin', password='password')

    def test_invoice_endpoint_only_returns_current_org(self):
        response = self.client.get(reverse('billing-invoices'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['invoices'], [])
