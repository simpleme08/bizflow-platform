# Security Policy

## Reporting a vulnerability

Please do not disclose security vulnerabilities in public GitHub issues.

Report suspected vulnerabilities privately to the repository owner through GitHub's private security reporting mechanism, or through the private contact channel maintained by the project owner.

Include:
- affected URL, endpoint, module, or workflow
- concise reproduction steps
- impact and affected tenant/data scope
- relevant logs or screenshots with secrets and personal data redacted

## Production security rules

- Never commit `.env` files, credentials, API keys, webhook secrets, database passwords, or private storage credentials.
- Production demo/seed commands must not be executed against production data.
- Production must use `DJANGO_DEBUG=False`, explicit allowed hosts, PostgreSQL, shared Redis, and private media storage.
- Rotate any credential that may have been exposed in source control or logs.
- Treat payroll, employee documents, attendance photos, and personally identifiable information as sensitive data.
