# BizFlow Product Boundary

## Purpose

BizFlow HRIS is the workforce operating system. The primary customer journey is:

**BizFlow website → sign in → organization workspace → People → Time → Payroll → Control → Pay → Proof**

The HRIS application is not a collection of client marketing websites.

## Single identity flow

The BizFlow website is the public entry point.

- **Sign in** goes to `/login/`.
- The user supplies normal BizFlow credentials.
- The authenticated account's active organization membership determines the workspace.
- A user with exactly one active organization is routed immediately.
- A user with multiple active organizations must explicitly choose one permitted organization.
- HR, managers, HR administrators, and other management roles enter the organization workspace.
- Employee users enter Employee Self-Service.

No client slug, customer website URL, or organization code is required to sign in.

## Time clock flow

The time clock is a separate operational entry point from the same BizFlow website:

**BizFlow website → Time clock → credentials → employee profile → employee organization → attendance**

The time clock does not ask the employee to choose an organization.

The employee profile is the authoritative organization boundary for clocking attendance. On successful clock authentication, the session is bound to that employee's organization. Subsequent clock actions must remain consistent with that organization.

Clock-in and clock-out continue to require the existing attendance controls, including camera proof and the normal attendance validation rules.

## Tenant boundary

Organization membership remains the security boundary for HRIS data.

The application must never infer a tenant from:

- a client website slug,
- a marketing URL,
- a hard-coded customer,
- the first membership returned by an unordered query.

Use the centralized organization context in `apps/organization/context.py`.

## HSIS separation

High Speed Internet Support (HSIS) is a separate customer/company website project. It is **not part of the BizFlow HRIS application**.

The HRIS repository no longer contains:

- HSIS client website profiles
- the client website view
- the client website template
- the `/client/<slug>/` route
- the legacy `/employee-login/` route

The removed HSIS implementation remains available in Git history if it is needed while the standalone HSIS project is established.

## What belongs in BizFlow

BizFlow owns:

- authentication and organization routing
- employee records
- organization and role management
- scheduling
- attendance and time clock
- leave
- payroll
- payroll controls and approvals
- reports
- employee self-service
- onboarding and lifecycle workflows
- billing/subscription infrastructure
- audit/security controls

## What does not belong in BizFlow

Customer-specific marketing content, hospitality service descriptions, customer social links, customer-specific locations, and customer website branding belong in the customer's own website project.

This boundary keeps BizFlow focused and prevents one customer from becoming the product identity for every organization.
