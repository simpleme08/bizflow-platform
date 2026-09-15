# Production User Provisioning

Use the Render Shell for production account creation. **Never put production passwords in GitHub, source files, `render.yaml`, or command-line arguments.** The provisioning command prompts for passwords without echoing them.

## 1. Create the Django SuperUser

If you need a Django admin superuser, run:

```bash
python manage.py createsuperuser
```

This command is intentionally separate from HRIS organization roles.

## 2. Create or repair the first HRIS workspace owner

After the Django superuser exists:

```bash
python manage.py bootstrap_admin --username YOUR_SUPERUSER --organization-name "High Speed Internet Support" --slug high-speed-internet-support
```

The command refuses to reactivate an inactive organization.

## 3. Provision HR and SME users

Use the production-safe command:

```bash
python manage.py provision_user --username production_hr --organization high-speed-internet-support --role HR --email hr@your-company.example
```

Enter the password at the secure prompt.

For an SME:

```bash
python manage.py provision_user --username production_sme --organization high-speed-internet-support --role SME --email sme@your-company.example
```

The command creates the user when missing and creates/repairs the organization membership. If the user already exists, its password is **not** changed unless `--set-password` is explicitly supplied.

To deliberately rotate an existing user's password:

```bash
python manage.py provision_user --username production_hr --organization high-speed-internet-support --role HR --set-password
```

An inactive existing user is rejected rather than silently reactivated.

## 4. HRIS Super User role

If you need the application-level `SUPER_USER` organization role:

```bash
python manage.py provision_user --username production_superuser --organization high-speed-internet-support --role SUPER_USER
```

`SUPER_USER` is an HRIS organization role. It does **not** grant Django `is_staff` or `is_superuser`. Use `createsuperuser` separately when Django administration access is required.

## 5. Adding employees under HSIS

Once the organization owner/HR account can access the HRIS:

1. Open **Employees**.
2. Choose **Add Employee**.
3. Select the HSIS organization/workspace.
4. Enter the employee's legal/profile information.
5. Assign the appropriate department, position, site, shift, employment type, and payroll details.
6. Save the employee record.
7. Create or invite the employee's login using the application's user-management workflow; do not share administrator credentials.

For the existing HSIS demo/reference data, the repository defines departments such as `Virtual Front Desk Assistance` and `Technical Support`, positions such as `Virtual Front Desk Agent` and `Technical Support Agent`, and sites for Parañaque and Davao operations. Use the actual production values rather than running demo seed commands.

## Production safety rules

- Do not run `seed_demo`, `seed_role_accounts`, `seed_hsis_demo`, or other demo seed commands against the production database.
- Do not commit real passwords or API keys.
- Prefer Render's environment variables/secret storage for production secrets.
- Use the least-privileged HRIS role appropriate for each employee.
- Treat the Django superuser as a break-glass/admin account, not as a shared daily HR account.
