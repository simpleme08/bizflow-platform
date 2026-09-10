# Client websites

BizFlow supports a branded public landing page for each client/tenant. The current implementation uses a reusable template plus a tenant-keyed content profile.

## First client: High Speed Internet Support

Client slug:

`high-speed-internet-support`

Public landing page:

`/client/high-speed-internet-support/`

The page includes:

- client brand presentation and responsive layout
- service overview
- Parañaque and Davao locations
- Facebook link
- HRIS sign-in CTA
- employee time-clock CTA
- BizFlow attribution

The current profile uses public business information for High Speed Internet Support, including its public website, the Parañaque location, and publicly described technical/customer-support work. The supplied Facebook profile URL is preserved as the client's social link.

## Adding another client

1. Create the client Organization and unique slug.
2. Add a profile in `apps/core/client_sites.py` using the organization slug.
3. Supply verified client copy, locations, social links and brand colors.
4. Keep the shared `templates/client_site.html` template reusable.
5. Add the client landing-page URL to the client's sales/onboarding materials.

Future enhancement: move client website content and theme fields into the Organization model/admin so HR administrators can manage branding without code changes.
