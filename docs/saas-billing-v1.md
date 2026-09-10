# SaaS billing foundation

This milestone establishes the application-side subscription model for the HRIS.

## Plans

| Plan | Monthly price | Included employees |
| --- | ---: | ---: |
| Free | ₱0 | 5 |
| Starter | ₱499 | 10 |
| Growth | ₱1,499 | 30 |
| Business | ₱2,999 | 75 |

The foundation exposes subscription state and active-employee usage through `/api/subscription/` and prevents reactivation when the organization is at its plan capacity or has a canceled/expired trial subscription.

Payment processor checkout, recurring collection, invoices, and provider webhooks are intentionally deferred to the payment integration milestone.
