# SaaS plans and subscription boundaries

The HRIS uses an organization-level subscription state so billing can be integrated without coupling payment-provider logic to HR workflows.

| Plan | Monthly price | Included employees | Default overage |
| --- | ---: | ---: | ---: |
| Free | PHP 0 | 5 | PHP 50/employee |
| Starter | PHP 499 | 10 | PHP 50/employee |
| Growth | PHP 1,499 | 30 | PHP 40/employee |
| Business | PHP 2,999 | 75 | PHP 30/employee |

Existing employees are never disabled solely because an organization changes plan. Employee activation enforcement should be applied at the point where an employee becomes operationally active.

`GET /api/subscription/` exposes the current plan, subscription status, active employee usage, remaining slots, and over-limit state to authorized organization users.

The billing customer ID is intentionally opaque; payment-provider integration and payment processing are not part of this milestone.
