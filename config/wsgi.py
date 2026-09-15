"""
WSGI config for config project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_wsgi_application()

# Legacy Render services may retain an older start command after the repository
# blueprint changes. A separate, explicit switch keeps this compatibility path
# opt-in so a correctly configured service does not provision twice.
if (
    os.environ.get("DJANGO_ENV", "development").lower() == "production"
    and os.environ.get("BIZFLOW_PROVISION_ON_WSGI", "false").lower() == "true"
):
    from django.core.management import call_command

    call_command("provision_production_accounts")
