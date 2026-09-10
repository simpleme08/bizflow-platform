import base64
import json
import urllib.error
import urllib.request

from django.conf import settings


class PayMongoError(Exception):
    pass


class PayMongoClient:
    base_url = 'https://api.paymongo.com/v1'

    def __init__(self):
        self.secret_key = getattr(settings, 'PAYMONGO_SECRET_KEY', '')
        if not self.secret_key:
            raise PayMongoError('PAYMONGO_SECRET_KEY is not configured.')

    def request(self, method, path, payload=None):
        token = base64.b64encode(f'{self.secret_key}:'.encode()).decode()
        body = None if payload is None else json.dumps(payload).encode()
        request = urllib.request.Request(
            f'{self.base_url}{path}',
            data=body,
            method=method,
            headers={
                'Authorization': f'Basic {token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json',
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors='replace')
            raise PayMongoError(f'PayMongo API error ({exc.code}): {detail}') from exc
        except urllib.error.URLError as exc:
            raise PayMongoError(f'PayMongo connection error: {exc.reason}') from exc

    def create_customer(self, *, email, first_name, last_name=''):
        return self.request('POST', '/customers', {'data': {'attributes': {
            'email': email,
            'first_name': first_name or 'HRIS',
            'last_name': last_name or 'Customer',
        }}})

    def create_plan(self, *, name, amount, description, metadata=None):
        return self.request('POST', '/subscriptions/plans', {'data': {'attributes': {
            'type': 'scheduled',
            'amount': int(amount),
            'currency': 'PHP',
            'interval': 'monthly',
            'interval_count': 1,
            'name': name,
            'description': description,
            'metadata': metadata or {},
        }}})

    def create_subscription(self, *, plan_id, customer_id):
        return self.request('POST', '/subscriptions', {'data': {'attributes': {
            'plan_id': plan_id,
            'customer_id': customer_id,
        }}})

    def update_subscription_plan(self, subscription_id, plan_id):
        return self.request('PUT', f'/subscriptions/{subscription_id}/plan', {'data': {'attributes': {'plan_id': plan_id}}})

    def cancel_subscription(self, subscription_id):
        return self.request('POST', f'/subscriptions/{subscription_id}/cancel', {'data': {'attributes': {}}})

    def retrieve_invoice(self, invoice_id):
        return self.request('GET', f'/subscriptions/invoices/{invoice_id}')
