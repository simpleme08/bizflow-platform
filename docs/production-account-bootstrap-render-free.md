# Production account bootstrap on Render Free

Render Free does not provide an interactive service shell. BizFlow therefore supports a secure, non-interactive production bootstrap through Render environment variables.

## How it works

`render.yaml` keeps `BIZFLOW_PROVISION_ACCOUNTS=false` and `BIZFLOW_PROVISION_RESET_PASSWORDS=false` by default. When you intentionally enable the provisioning switch, the web service runs migrations and then executes `provision_production_accounts` before starting Gunicorn.

The command:

- creates the configured production organization if it does not exist;
- creates HR, SME, and HRIS SUPER_USER accounts when they do not exist;
- creates or repairs their organization memberships;
- never reactivates an inactive user or organization;
- never prints passwords;
- never stores passwords in GitHub;
- does not grant Django `is_staff`/`is_superuser` to the HRIS `SUPER_USER` role;
- preserves an existing active user's password unless the explicit one-time reset switch is enabled.

## Required Render environment variables

Set these in the Render service environment. Do not commit their values to the repository:

```text
BIZFLOW_PROVISION_ACCOUNTS=true
BIZFLOW_PROVISION_RESET_PASSWORDS=false
BIZFLOW_PRODUCTION_ORG_SLUG=hsis
BIZFLOW_PRODUCTION_ORG_NAME=High Speed Internet Support
BIZFLOW_PRODUCTION_HR_USERNAME=<hr-username>
BIZFLOW_PRODUCTION_HR_PASSWORD=<strong-random-password>
BIZFLOW_PRODUCTION_HR_EMAIL=<hr-email>
BIZFLOW_PRODUCTION_SME_USERNAME=<sme-username>
BIZFLOW_PRODUCTION_SME_PASSWORD=<strong-random-password>
BIZFLOW_PRODUCTION_SME_EMAIL=<sme-email>
BIZFLOW_PRODUCTION_SUPER_USER_USERNAME=<super-user-username>
BIZFLOW_PRODUCTION_SUPER_USER_PASSWORD=<strong-random-password>
BIZFLOW_PRODUCTION_SUPER_USER_EMAIL=<admin-email>
```

Optional first/last name variables are also supported by the command implementation.

### Recovering an existing account with a known bootstrap password

If an active configured account already exists but its password is unknown or does not match the password currently stored in Render, enable both switches for **one controlled deployment**:

```text
BIZFLOW_PROVISION_ACCOUNTS=true
BIZFLOW_PROVISION_RESET_PASSWORDS=true
```

This resets only the three configured production accounts to the passwords supplied through the protected Render environment variables. It never prints those passwords. After the deployment is successful, immediately set both switches back to `false` and redeploy.

Do not leave `BIZFLOW_PROVISION_RESET_PASSWORDS=true` enabled for normal operation.

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
