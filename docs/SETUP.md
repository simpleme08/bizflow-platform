# Setup and configuration

## 1. Prerequisites

Install:

- Python 3.11+
- Git
- PostgreSQL 15+ for shared/staging/production environments

SQLite is supported for local evaluation only.

## 2. Local installation

Windows PowerShell:

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

Open `http://127.0.0.1:8000/`.

If `python` is not recognized, install Python with PATH enabled and recreate `.venv` rather than reusing an environment tied to a removed interpreter.

## 3. Environment configuration

| Variable | Local | Hosted/production |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | Unique local secret | Long random secret in secret store |
| `DJANGO_DEBUG` | `True` | `False` |
| `DJANGO_ALLOWED_HOSTS` | `127.0.0.1,localhost` | Exact hostnames only |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Usually empty/local | Exact HTTPS origins |
| `DB_ENGINE` | `sqlite` or `postgresql` | `postgresql` |
| `POSTGRES_*` | Only for PostgreSQL | Required |
| `POSTGRES_SSLMODE` | `prefer` | `require` or stronger |
| PayMongo variables | Test mode when needed | Live values in secret store |

Never commit `.env`, credentials, database dumps or provider secrets.

## 4. PostgreSQL

Example local configuration:

```dotenv
DB_ENGINE=postgresql
POSTGRES_DB=bizflow
POSTGRES_USER=bizflow_app
POSTGRES_PASSWORD=CHANGE_ME
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_SSLMODE=prefer
```

Use a least-privilege application database user. Run migrations before starting the application.

## 5. Supabase PostgreSQL

Create a Supabase project and copy the exact connection details from its **Connect** panel. For persistent Django hosting, use a Direct connection where IPv6/networking permits it; otherwise use the Supavisor Session Pooler connection appropriate to the host.

```dotenv
DB_ENGINE=postgresql
POSTGRES_DB=postgres
POSTGRES_USER=YOUR_SUPABASE_USER
POSTGRES_PASSWORD=YOUR_DATABASE_PASSWORD
POSTGRES_HOST=YOUR_SUPABASE_HOST
POSTGRES_PORT=5432
POSTGRES_SSLMODE=require
```

Never use the sample values literally. Use the current connection details supplied by the project.

## 6. Demo data

For a disposable local database:

```powershell
python manage.py migrate
python manage.py seed_demo
```

The command is intended for demonstrations and is safe to rerun within that purpose. Do not run it against a production HR database.

## 7. Render deployment

The repository includes `render.yaml`. Its production-oriented command sequence runs migrations and static collection before Gunicorn starts, and the service uses `/ready/` as the health check.

Configure at minimum:

- `DJANGO_DEBUG=False`
- generated `DJANGO_SECRET_KEY`
- exact `DJANGO_ALLOWED_HOSTS`
- exact `DJANGO_CSRF_TRUSTED_ORIGINS`
- PostgreSQL connection values
- PayMongo production/test configuration as appropriate

A free Render service is suitable for demonstration but is not an appropriate production HRIS hosting tier because availability and filesystem characteristics are limited. Use persistent PostgreSQL and production infrastructure with backups and monitoring.

## 8. First deployment verification

After deployment:

1. Open `/health/` and confirm HTTP 200.
2. Open `/ready/` and confirm HTTP 200 with database readiness.
3. Sign in with a controlled account.
4. Verify organization/membership scope.
5. Run the relevant smoke tests.
6. Confirm backups and monitoring before accepting real customer data.

## 9. Common problems

- **DisallowedHost:** fix `DJANGO_ALLOWED_HOSTS`.
- **CSRF failure:** fix `DJANGO_CSRF_TRUSTED_ORIGINS`.
- **Database refused:** verify host/user/password/port/SSL mode.
- **Static files missing:** run `collectstatic` and inspect WhiteNoise deployment.
- **Migration failure:** restore the database, inspect migration history, and fix dependencies before deploying application code.
- **PayMongo failures:** verify environment mode, plan identifiers, API credentials and webhook signing secret.
