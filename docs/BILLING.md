# SaaS billing and PayMongo

## Commercial plans

| Plan | Monthly price | Included active employees | Overage |
| --- | ---: | ---: | ---: |
| Free | ₱0 | 5 | ₱50/employee |
| Starter | ₱499 | 10 | ₱50/employee |
| Growth | ₱1,499 | 30 | ₱40/employee |
| Business | ₱2,999 | 75 | ₱30/employee |

These are application defaults. Final commercial terms, taxes, invoices and customer agreements must be established by the business.

## Subscription states

The application stores its own subscription status and PayMongo identifiers. Provider state is synchronized through verified webhooks. A canceled subscription or expired trial is not allowed to continue protected operational flows that require an active subscription.

## Employee limits

Usage is based on active employees. Activation/reactivation is blocked when the organization cannot activate another employee under its current subscription/plan policy. The server calculates usage; the client cannot raise its own limit.

## PayMongo flow

The production billing integration uses PayMongo for recurring subscriptions.

1. Organization administrator starts checkout.
2. The application maps the selected internal plan to the configured PayMongo plan identifier.
3. PayMongo creates the customer/subscription/payment flow.
4. The initial payment must complete within PayMongo's required checkout window.
5. PayMongo emits subscription/invoice events.
6. The webhook endpoint verifies the signature before processing.
7. The application records/synchronizes subscription and invoice state.
8. Duplicate webhook delivery must not repeat a business effect.

## Configuration

Required deployment values include:

```dotenv
PAYMONGO_SECRET_KEY=
PAYMONGO_PUBLIC_KEY=
PAYMONGO_WEBHOOK_SECRET=
PAYMONGO_LIVEMODE=False
PAYMONGO_PLAN_STARTER=
PAYMONGO_PLAN_GROWTH=
PAYMONGO_PLAN_BUSINESS=
```

Never expose the secret key or webhook secret to browser JavaScript or commit them to Git.

## Billing endpoints

- `POST /api/billing/checkout/`
- `POST /api/billing/change-plan/`
- `POST /api/billing/cancel/`
- `GET /api/billing/invoices/`
- `POST /api/billing/webhook/paymongo/`

## Webhook requirements

The webhook receiver must preserve the raw request body, validate the PayMongo signature with the configured endpoint secret, reject invalid signatures, and only then parse/process the event. Production operators should configure the live webhook URL and live signing secret in the deployment platform.

## Plan changes and cancellation

Plan changes and cancellations are provider operations as well as local application state changes. The application should treat provider responses/webhooks as the authoritative confirmation of external state and keep an audit trail of billing actions.

## Invoice handling

Invoices displayed by the HRIS are billing records synchronized from the payment provider. They are not a replacement for accounting records, tax invoices, or legal documentation unless the business has explicitly implemented and validated those requirements.

## Billing failure operations

Monitor `past_due`, `unpaid`, failed invoice/payment events and webhook failures. Do not manually mark an organization paid merely because a browser returned from checkout. Resolve billing state through the provider and verified synchronization.

## Test checklist

- test-mode checkout succeeds
- active subscription is reflected locally
- plan change is synchronized
- cancellation is synchronized
- invoice appears for the correct organization
- invalid webhook signature is rejected
- duplicate webhook is harmless
- event for another organization cannot alter local tenant state
- failed payment produces the expected subscription state
- live credentials are never present in source control
