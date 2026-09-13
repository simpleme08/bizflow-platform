"""
Django settings for config project.
"""

from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

ENVIRONMENT = os.getenv('DJANGO_ENV', 'development').lower()
DEBUG = os.getenv('DJANGO_DEBUG', 'False').lower() in ('1', 'true', 'yes')
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', '')
if not SECRET_KEY:
    if ENVIRONMENT == 'production':
        raise RuntimeError('DJANGO_SECRET_KEY must be set in production')
    SECRET_KEY = 'dev-only-key-change-this-before-production'

ALLOWED_HOSTS = [host.strip() for host in os.getenv('DJANGO_ALLOWED_HOSTS', '127.0.0.1,localhost').split(',') if host.strip()]

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

if os.getenv('DB_ENGINE', 'sqlite').lower() == 'postgresql':
    DATABASES = {'default': {'ENGINE': 'django.db.backends.postgresql', 'NAME': os.getenv('POSTGRES_DB', 'bizflow'), 'USER': os.getenv('POSTGRES_USER', 'postgres'), 'PASSWORD': os.getenv('POSTGRES_PASSWORD', ''), 'HOST': os.getenv('POSTGRES_HOST', 'localhost'), 'PORT': os.getenv('POSTGRES_PORT', '5432'), 'OPTIONS': {'sslmode': os.getenv('POSTGRES_SSLMODE', 'require')}}}
else:
    DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'db.sqlite3'}}

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
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'},
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

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

PAYMONGO_SECRET_KEY = os.getenv('PAYMONGO_SECRET_KEY', '')
PAYMONGO_PUBLIC_KEY = os.getenv('PAYMONGO_PUBLIC_KEY', '')
PAYMONGO_WEBHOOK_SECRET = os.getenv('PAYMONGO_WEBHOOK_SECRET', '')
PAYMONGO_LIVEMODE = os.getenv('PAYMONGO_LIVEMODE', 'False').lower() in ('1', 'true', 'yes')
PAYMONGO_PLAN_STARTER = os.getenv('PAYMONGO_PLAN_STARTER', '')
PAYMONGO_PLAN_GROWTH = os.getenv('PAYMONGO_PLAN_GROWTH', '')
PAYMONGO_PLAN_BUSINESS = os.getenv('PAYMONGO_PLAN_BUSINESS', '')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
