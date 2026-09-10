# Contributing and development workflow

## Branching

Use a short-lived branch for feature, fix, documentation, or maintenance work. Keep commits focused and avoid generated files or unrelated refactors.

Recommended naming:

- `feat/<area>`
- `fix/<area>`
- `docs/<area>`
- `chore/<area>`

Open a pull request against `main` for changes that need review or CI validation.

## Local development

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python manage.py migrate
python manage.py check
python manage.py test
python manage.py runserver
```

## Before opening a PR

Run:

```powershell
python manage.py check
python manage.py test
python manage.py migrate --check
```

For deployment-related changes also run `python manage.py collectstatic --noinput` in a production-like environment.

## Django changes

When models change:

```powershell
python manage.py makemigrations
python manage.py migrate
python manage.py test
```

Review generated migrations before committing them. Keep migration dependencies linear and intentional; do not create duplicate migration numbers in the same Django app.

## Tenant-aware development

Every new organization-facing query must be reviewed for tenant scope. Test at least two organizations when adding or changing access-controlled behavior.

Do not use client-supplied organization IDs as an authorization mechanism. Resolve the organization from authenticated membership/context.

## Security-sensitive changes

For authentication, authorization, payroll, employee data, billing, webhooks, file imports or secrets:

1. Add a regression test for the failure/abuse case.
2. Verify organization isolation.
3. Verify permission enforcement server-side.
4. Avoid logging secrets or sensitive payroll/employee data.
5. Document any new environment variables or operational prerequisites.

## Documentation standard

User-facing behavior belongs in `README.md` or `docs/`. API behavior belongs in `docs/API.md`. Operational procedures belong in `docs/OPERATIONS.md` or `docs/production-launch.md`. Compliance caveats belong in `docs/PAYROLL_AND_COMPLIANCE.md`.

Do not document planned behavior as if it were implemented. Clearly label external integrations and operational prerequisites.
