# BizFlow domain architecture

BizFlow uses a public marketing surface and a separate HRIS application boundary.

## Recommended production topology

- `https://bizflow.com` — public BizFlow marketing, product, pricing, demos, and sales content.
- `https://app.bizflow.com` — authenticated HRIS application for administrators, HR, payroll users, and employees.
- Customer public websites remain owned and hosted by the customer. They link to BizFlow rather than embedding private HRIS pages.

## Customer integration

A customer website may expose links such as:

- Employee login → `https://app.bizflow.com/login/`
- Employee self-service → `https://app.bizflow.com/ess/`
- Attendance clock → `https://app.bizflow.com/clock/`

Future integrations should use an explicit API/SSO contract. Do not expose payroll, employee records, documents, or other private HRIS endpoints directly from a customer's public website.

## Django configuration

Set `BIZFLOW_APP_URL=https://app.bizflow.com` in the production environment. The public website and client-site preview use this value when generating HRIS links.

For a deployment where the marketing site and HRIS are served by separate Django instances, deploy the same codebase with different hostnames and responsibilities. The HRIS instance should only accept its configured application hostname(s).

## Security boundary

The domain split is a product and deployment boundary, not a substitute for authorization. Tenant isolation, explicit organization selection, object-level authorization, CSRF protection, private media handling, and payroll maker/checker controls remain mandatory inside the HRIS.

## Customer website rule

Do not require customers to move their public website to BizFlow. A customer's existing domain can remain unchanged while its employee/admin login links point to the BizFlow application.
