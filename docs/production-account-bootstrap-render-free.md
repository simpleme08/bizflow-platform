# Production account bootstrap on Render Free

Render Free does not provide an interactive service shell. BizFlow therefore supports a secure, non-interactive production bootstrap through Render environment variables.

## How it works

`render.yaml` keeps `BIZFLOW_PROVISION_ACCOUNTS=false` by default. When you intentionally enable it, the web service runs migrations and then executes `provision_production_accounts` before starting Gunicorn.

The command:

- creates the configured production organization if it does not exist;
- creates HR, SME, and HRIS SUPER_USER accounts when they do not exist;
- creates or repairs their organization memberships;
- never reactivates an inactive user or organization;
- never prints passwords;
- never stores passwords in GitHub;
- does not grant Django `is_staff`/`is_superuser` to the HRIS `SUPER_USER` role.

## Required Render environment variables

Set these in the Render service environment. Do not commit their values to the repository:

```text
BIZFLOW_PROVISION_ACCOUNTS=true
BIZFLOW_PRODUCTION_ORG_SLUG=high-speed-internet-support
BIZFLOW_PRODUCTION_ORG_NAME=High Speed Internet Support
BIZFLOW_PRODUCTION_HR_USERNAME=production_hr
BIZFLOW_PRODUCTION_HR_PASSWORD=<strong-random-password>
BIZFLOW_PRODUCTION_HR_EMAIL=<hr-email>
BIZFLOW_PRODUCTION_SME_USERNAME=production_sme
BIZFLOW_PRODUCTION_SME_PASSWORD=<strong-random-password>
BIZFLOW_PRODUCTION_SME_EMAIL=<sme-email>
BIZFLOW_PRODUCTION_SUPER_USER_USERNAME=production_super_user
BIZFLOW_PRODUCTION_SUPER_USER_PASSWORD=<strong-random-password>
BIZFLOW_PRODUCTION_SUPER_USER_EMAIL=<admin-email>
```

Optional first/last name variables are also supported by the command implementation.

After the first successful deployment, set `BIZFLOW_PROVISION_ACCOUNTS=false` again. The command is idempotent, but disabling the bootstrap switch reduces the amount of credential material used during normal deploys.

## Important distinction

`SUPER_USER` is the BizFlow organization role and has full HRIS permissions. A Django administrator is separate. If Django Admin access is required, use a separately managed Django superuser process; do not turn every HRIS SUPER_USER into a Django superuser automatically.

## Adding employees after bootstrap

Once HR has signed in:

1. Open **Employees**.
2. Choose **Add Employee**.
3. Select the **High Speed Internet Support** organization.
4. Enter the employee's identity/contact information.
5. Assign department, position, site, shift, employment type, and payroll details as applicable.
6. Create/activate the employee account using the application's normal user workflow.
7. Verify the employee can see only their own permitted HRIS data.

Do not run demo seed commands against the production database.
