# SaaS billing v1

Organization subscription state is represented by plan, subscription status, trial end, opaque billing customer ID, and configurable overage rate.

Plans: Free PHP 0 / 5 employees; Starter PHP 499 / 10; Growth PHP 1,499 / 30; Business PHP 2,999 / 75. Default overage rates are PHP 50, PHP 50, PHP 40, and PHP 30 respectively.

The subscription endpoint reports active employee usage and remaining capacity. Existing employees are not disabled by plan changes. Payment-provider processing is intentionally deferred.
