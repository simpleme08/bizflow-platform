# Privacy and data-retention operating process

This process applies before any customer HR data is loaded into BizFlow HRIS.

## Data handling principles

- Collect only data required for an HR/payroll workflow.
- Keep tenant data isolated by organization and enforce authorization server-side.
- Treat employee identity, compensation, payroll, bank and attendance evidence as confidential HR data.
- Do not place production secrets, customer exports or database dumps in source control.
- Use private object storage for employee documents and attendance proof photos.
- Use expiring/signed object URLs rather than public buckets or permanent public links.
- Restrict production support access to authorized personnel and record material administrative actions in the audit trail.

## Retention controls

Organization settings provide configurable retention periods for audit events, employee documents and attendance proof photos. Before onboarding a customer, record the customer's approved retention values and any legal/business exceptions.

The scheduled maintenance process should:

1. Apply the configured audit/document retention policy.
2. Remove expired attendance proof photos according to the organization setting.
3. Queue document-expiry notifications.
4. Deliver pending notifications with bounded retries.

Retention deletion must be treated as a controlled destructive operation. Test the policy on non-production data first and preserve only records that have an approved legal hold or other documented exception.

## Customer onboarding record

For each customer, record:

- Organization name and tenant identifier
- Data controller/processor roles as agreed by contract
- Categories of employee data processed
- Approved retention periods
- Legal-hold procedure and authorized approvers
- Subprocessors/cloud providers used
- Incident/security contact
- Export/deletion request procedure
- Date of privacy review and reviewer

## Data-subject and customer requests

Establish a documented process for customer requests involving access, correction, export, deletion, retention exceptions or legal holds. Verify requester authority before disclosing or deleting employee data.

## Incident handling

Suspected unauthorized access, accidental disclosure, credential exposure or destructive data loss must be escalated immediately. Preserve relevant audit/log evidence, contain access where appropriate, and follow the applicable contractual and legal notification requirements.

## Production sign-off

A customer must not be loaded with real HR data until the customer-specific retention settings, privacy responsibilities, subprocessors and incident contacts have been documented and approved by the responsible organization.
