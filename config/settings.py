"""
Django settings for config project.
"""

from pathlib import Path
import os
from urllib.parse import unquote, urlparse

BASE_DIR = Path(__file__).resolve().parent.parent

ENVIRONMENT = os.getenv('DJANGO_ENV', 'development').lower()
DEBUG = os.getenv('DJANGO_DEBUG', 'False').lower() in ('1', 'true', 'yes')
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', '')
if not SECRET_KEY:
    if ENVIRONMENT == 'production':
        raise RuntimeError('DJANGO_SECRET_KEY must be set in production')
    SECRET_KEY = 'dev-only-key-change-this-before-production'

ALLOWED_HOSTS = [host.strip() for host in os.getenv('DJANGO_ALLOWED_HOSTS', '').split(',') if host.strip()]
if not ALLOWED_HOSTS:
    ALLOWED_HOSTS = ['127.0.0.1', 'localhost'] if ENVIRONMENT != 'production' else []

# Render exposes the service's canonical public URL. Add only that exact
# hostname when configured; never use a broad wildcard/suffix for production.
render_external_url = os.getenv('RENDER_EXTERNAL_URL', '').strip()
if render_external_url:
    render_host = urlparse(render_external_url).hostname
    if render_host and render_host not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(render_host)

if ENVIRONMENT == 'production':
    if DEBUG:
        raise RuntimeError('DJANGO_DEBUG must be False in production')
    if not ALLOWED_HOSTS or '*' in ALLOWED_HOSTS or any(host in {'localhost', '127.0.0.1'} for host in ALLOWED_HOSTS):
        raise RuntimeError('DJANGO_ALLOWED_HOSTS must contain real production hostnames')

INSTALLED_APPS = [
    'django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes', 'django.contrib.sessions',
    'django.contrib.messages', 'django.contrib.staticfiles', 'apps.core', 'apps.accounts', 'apps.organization',
    'apps.employees', 'apps.workforce', 'apps.attendance', 'apps.leave', 'apps.payroll', 'apps.reports',
    'apps.ess', 'apps.scheduling', 'apps.onboarding', 'apps.talent', 'apps.operations',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware', 'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware', 'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware', 'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware', 'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'
TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates', 'DIRS': [BASE_DIR / 'templates'], 'APP_DIRS': True,
    'OPTIONS': {'context_processors': ['django.template.context_processors.request', 'django.contrib.auth.context_processors.auth', 'django.contrib.messages.context_processors.messages']},
}]
WSGI_APPLICATION = 'config.wsgi.application'

DATABASE_URL = os.getenv('DATABASE_URL', '').strip()
DB_ENGINE = os.getenv('DB_ENGINE', 'sqlite').lower()
if DATABASE_URL:
    parsed_database_url = urlparse(DATABASE_URL)
    if parsed_database_url.scheme not in ('postgresql', 'postgres'):
        raise RuntimeError('DATABASE_URL must use the postgresql:// scheme')
    if not parsed_database_url.hostname or not parsed_database_url.username or not parsed_database_url.path.strip('/'):
        raise RuntimeError('DATABASE_URL must include database host, user, and database name')
    database_options = dict(item.split('=', 1) for item in parsed_database_url.query.split('&') if '=' in item)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': unquote(parsed_database_url.path.lstrip('/')),
            'USER': unquote(parsed_database_url.username),
            'PASSWORD': unquote(parsed_database_url.password or ''),
            'HOST': parsed_database_url.hostname,
            'PORT': str(parsed_database_url.port or 5432),
            'CONN_MAX_AGE': int(os.getenv('POSTGRES_CONN_MAX_AGE', '60')),
            'OPTIONS': {'sslmode': database_options.get('sslmode', os.getenv('POSTGRES_SSLMODE', 'require'))},
        }
    }
elif DB_ENGINE == 'postgresql':
    DATABASES = {'default': {'ENGINE': 'django.db.backends.postgresql', 'NAME': os.getenv('POSTGRES_DB', 'bizflow'), 'USER': os.getenv('POSTGRES_USER', 'postgres'), 'PASSWORD': os.getenv('POSTGRES_PASSWORD', ''), 'HOST': os.getenv('POSTGRES_HOST', 'localhost'), 'PORT': os.getenv('POSTGRES_PORT', '5432'), 'CONN_MAX_AGE': int(os.getenv('POSTGRES_CONN_MAX_AGE', '60')), 'OPTIONS': {'sslmode': os.getenv('POSTGRES_SSLMODE', 'require')}}}
else:
    if ENVIRONMENT == 'production':
        raise RuntimeError('PostgreSQL is required in production; set DATABASE_URL or DB_ENGINE=postgresql')
    DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'db.sqlite3'}}

REDIS_URL = os.getenv('REDIS_URL', '').strip()
if ENVIRONMENT == 'production' and not REDIS_URL:
    raise RuntimeError('REDIS_URL must be set in production for shared cache and login throttling')
if REDIS_URL:
    CACHES = {'default': {'BACKEND': 'django.core.cache.backends.redis.RedisCache', 'LOCATION': REDIS_URL}}
else:
    CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache', 'LOCATION': 'bizflow-development-cache'}}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Manila'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

STORAGE_BACKEND = os.getenv('DJANGO_STORAGE', 'filesystem').strip().lower()
if ENVIRONMENT == 'production' and STORAGE_BACKEND != 's3':
    raise RuntimeError('DJANGO_STORAGE=s3 is required in production so private HR files are not stored on ephemeral local disk')
if STORAGE_BACKEND == 's3':
    AWS_ACCESS_KEY_ID = os.getenv('BIZFLOW_STORAGE_KEY', '').strip()
    AWS_SECRET_ACCESS_KEY = os.getenv('BIZFLOW_STORAGE_SECRET', '').strip()
    AWS_STORAGE_BUCKET_NAME = os.getenv('BIZFLOW_STORAGE_BUCKET', '').strip()
    AWS_S3_ENDPOINT_URL = os.getenv('BIZFLOW_STORAGE_ENDPOINT', '').strip()
    AWS_S3_REGION_NAME = os.getenv('BIZFLOW_STORAGE_REGION', '').strip() or None
    AWS_S3_ADDRESSING_STYLE = os.getenv('BIZFLOW_STORAGE_ADDRESSING', 'path').strip()
    AWS_S3_SIGNATURE_VERSION = os.getenv('BIZFLOW_STORAGE_SIGNATURE', 's3v4').strip()
    AWS_QUERYSTRING_AUTH = True
    AWS_QUERYSTRING_EXPIRE = int(os.getenv('BIZFLOW_STORAGE_URL_TTL', '300'))
    AWS_DEFAULT_ACL = None
    AWS_S3_FILE_OVERWRITE = False
    if ENVIRONMENT == 'production' and not all((AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_STORAGE_BUCKET_NAME, AWS_S3_ENDPOINT_URL)):
        raise RuntimeError('Private storage credentials, bucket, and endpoint must be configured in production')
    STORAGES = {
        'default': {'BACKEND': 'storages.backends.s3.S3Storage'},
        'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage'},
    }
else:
    STORAGES = {
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage'},
    }

SECURE_SSL_REDIRECT = ENVIRONMENT == 'production'
SECURE_HSTS_SECONDS = 31536000 if ENVIRONMENT == 'production' else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = ENVIRONMENT == 'production'
SECURE_HSTS_PRELOAD = ENVIRONMENT == 'production'
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https') if ENVIRONMENT == 'production' else None
SESSION_COOKIE_SECURE = ENVIRONMENT == 'production'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SECURE = ENVIRONMENT == 'production'
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = 'Lax'
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'same-origin'
CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in os.getenv('DJANGO_CSRF_TRUSTED_ORIGINS', '').split(',') if origin.strip()]
if render_external_url:
    render_origin = render_external_url.rstrip('/')
    if render_origin.startswith('https://') and render_origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(render_origin)
if ENVIRONMENT == 'production' and not CSRF_TRUSTED_ORIGINS:
    raise RuntimeError('DJANGO_CSRF_TRUSTED_ORIGINS must be configured in production or supplied by Render external URL')

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {'default': {'format': '{levelname} {asctime} {name} {message}', 'style': '{'}},
    'handlers': {'console': {'class': 'logging.StreamHandler', 'formatter': 'default'}},
    'root': {'handlers': ['console'], 'level': 'INFO' if ENVIRONMENT == 'production' else 'WARNING'},
}

PAYMONGO_SECRET_KEY = os.getenv('PAYMONGO_SECRET_KEY', '')
PAYMONGO_PUBLIC_KEY = os.getenv('PAYMONGO_PUBLIC_KEY', '')
PAYMONGO_WEBHOOK_SECRET = os.getenv('PAYMONGO_WEBHOOK_SECRET', '')
PAYMONGO_LIVEMODE = os.getenv('PAYMONGO_LIVEMODE', 'False').lower() in ('1', 'true', 'yes')
PAYMONGO_PLAN_STARTER = os.getenv('PAYMONGO_PLAN_STARTER', '')
PAYMONGO_PLAN_GROWTH = os.getenv('PAYMONGO_PLAN_GROWTH', '')
PAYMONGO_PLAN_BUSINESS = os.getenv('PAYMONGO_PLAN_BUSINESS', '')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
