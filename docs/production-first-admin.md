# Production first administrator

The production database is intentionally not seeded with a default administrator or demo account.

## Create the first administrator

From the Render service Shell, run:

```bash
python manage.py createsuperuser
```

Use a unique administrator username, email address, and strong password. Never commit the password to Git.

## Connect the administrator to the first organization

After creating the superuser, run:

```bash
python manage.py bootstrap_admin --username YOUR_ADMIN_USERNAME --organization-name "Your Company" --slug your-company
```

The command refuses ordinary users and refuses to reactivate an inactive organization automatically. It creates the organization as `FREE` / `TRIALING` and gives the existing superuser an `OWNER` membership.

Then sign in at `/login/`. The owner membership is required for the HRIS workspace because tenant context is fail-closed.

## Demo commands

Do **not** run `seed_demo`, `seed_role_accounts`, or `seed_hsis_demo` against a real production database. They are intended for disposable demonstration environments and contain intentionally predictable demo credentials/data.
