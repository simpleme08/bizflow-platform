# PayMongo billing integration

The HRIS SaaS billing integration uses PayMongo Subscriptions for Philippine recurring billing. PayMongo currently supports recurring subscriptions on cards and Maya; subscription capability must be separately activated on the merchant account before live use.

## Environment variables

Set these server-side only:

- `PAYMONGO_SECRET_KEY`
- `PAYMONGO_PUBLIC_KEY`
- `PAYMONGO_WEBHOOK_SECRET`
- `PAYMONGO_LIVEMODE=True` for the live endpoint
- `PAYMONGO_PLAN_STARTER`
- `PAYMONGO_PLAN_GROWTH`
- `PAYMONGO_PLAN_BUSINESS`

The plan IDs are created/configured in PayMongo and mapped to the HRIS commercial plan codes. Never accept provider plan IDs directly from the browser.

## PayMongo account setup

1. Activate the PayMongo merchant account and the payment methods required by the business.
2. Request activation of PayMongo Subscriptions for the account.
3. Create one monthly PHP scheduled plan for each paid HRIS plan. The HRIS catalog remains authoritative for the commercial price; the provider plan IDs are configuration references.
4. Register a webhook endpoint at `/api/billing/webhook/paymongo/`.
5. Subscribe to the subscription lifecycle and invoice events used by this integration:
   - `subscription.activated`
   - `subscription.past_due`
   - `subscription.unpaid`
   - `subscription.updated`
   - `subscription.invoice.created`
   - `subscription.invoice.finalized`
   - `subscription.invoice.paid`
   - `subscription.invoice.payment_failed`
6. Store the webhook secret in `PAYMONGO_WEBHOOK_SECRET`.

## Checkout flow

An authorized organization administrator sends `POST /api/billing/checkout/` with a paid `plan_code` (`STARTER`, `GROWTH`, or `BUSINESS`). The server creates/reuses the PayMongo customer, creates or changes the provider subscription, stores the provider subscription/invoice reference, and returns the first payment intent client key when available.

The client completes the first invoice payment using PayMongo's client-side payment flow. Card details must never be sent to the HRIS backend. Production access changes are driven by verified webhook events, not by a browser redirect.

## Webhook security

PayMongo signs webhook requests with the `Paymongo-Signature` header. The HRIS endpoint verifies the timestamp, constructs `timestamp + '.' + raw_request_body`, computes HMAC-SHA256 using the webhook secret, and compares the appropriate test/live signature with a timing-safe comparison. Requests older than five minutes are rejected.

Webhook event IDs are unique and persisted. A previously processed event is acknowledged without being processed again, making retries idempotent.

## Billing state mapping

| PayMongo subscription state | HRIS organization state |
| --- | --- |
| `active` | `ACTIVE` |
| `past_due` | `PAST_DUE` |
| `unpaid` | `PAST_DUE` |
| `cancelled` | `CANCELED` |

A failed/canceled subscription changes operational access according to the existing authoritative subscription service; it does not delete or mutate HR/payroll records.

## API endpoints

- `POST /api/billing/checkout/`
- `POST /api/billing/change-plan/`
- `POST /api/billing/cancel/`
- `GET /api/billing/invoices/`
- `POST /api/billing/webhook/paymongo/`

All organization-facing billing endpoints are organization-scoped and require the appropriate existing organization permissions. Webhooks are provider-authenticated rather than user-authenticated.

## Production notes

Keep PayMongo secret keys and webhook secrets in the deployment secret manager. Use separate test and live webhook endpoints/secrets. PayMongo requires subscription capability activation before testing/live use for accounts where it is not already enabled. Confirm current supported payment methods and account capability status before production rollout.
