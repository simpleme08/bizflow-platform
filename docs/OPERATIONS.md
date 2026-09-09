# Operations, security, and release procedure

## Routine operations

### Daily

- Verify time-clock exceptions and imported attendance errors.
- Review leave and approval queues.
- Check the HR dashboard and audit events for unexpected activity.

### Per payroll cycle

1. Confirm employee salaries and active assignments.
2. Review attendance including late, undertime, overtime, leave, and manual corrections.
3. Process payroll, perform independent review, and approve records.
4. Confirm employees can access only their approved payslips.
5. Export/archive reports according to internal policy.

### Monthly

- Review active users and memberships; disable departed/temporary access.
- Check leave balances and benefit enrollments.
- Test backup restoration for PostgreSQL.
- Review external connector records and ensure disabled connectors do not contain credentials.

## Database backup and restore

For PostgreSQL, take a logical backup before upgrades:

```powershell
pg_dump -Fc -h HOST -U USER -d bizflow -f bizflow-backup.dump
```

Restore only into a verified target database:

```powershell
pg_restore -h HOST -U USER -d bizflow_restored --clean --if-exists bizflow-backup.dump
```

For Supabase, use its database backup/export facilities and test recovery according to your plan.

## Release procedure

1. Back up production PostgreSQL.
2. Create/test changes in a staging database.
3. Install pinned project dependencies: `python -m pip install -r requirements.txt`.
4. Run `python manage.py check` and `python manage.py test`.
5. Apply migrations: `python manage.py migrate`.
6. Run `python manage.py collectstatic --noinput` for production.
7. Deploy Gunicorn application.
8. Perform smoke tests: login, ESS, time clock, leave submission, attendance import template, payroll payslip, and Admin access.

## Security requirements

- Use HTTPS and `DJANGO_DEBUG=False` in production.
- Set exact `DJANGO_ALLOWED_HOSTS`; never use `*`.
- Use unique passwords, MFA/SSO through a real identity-provider connector when available, and least-privilege memberships.
- Keep DB/provider secrets only in environment-managed secret stores.
- Do not enable connectors merely by adding an endpoint: require vendor credentials, agreement, security review, and test environment.
- Store employee data only where permitted by the organization’s privacy and retention policy.
- Review Philippine employment, payroll, tax, statutory-benefit, privacy, and retention obligations with qualified advisers before production use.

## Known operational boundaries

- Payroll tax calculation/filing, benefits-carrier transmission, background checks, legally binding third-party signatures, email/SMS delivery, and SSO require real external providers.
- The connector registry is configuration metadata, not an active integration engine and never stores secrets.
- A free Render service is for demonstrations, not a production HRIS: it can sleep, restart, and has no persistent local disk.
