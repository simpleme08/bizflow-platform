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

# Render services created before the production-hardening blueprint may retain
# their original start command. In that case, provisioning must still be able
# to run when explicitly enabled through the production-only environment flag.
# The command itself performs all validation and never logs passwords.
if (
    os.environ.get("DJANGO_ENV", "development").lower() == "production"
    and os.environ.get("BIZFLOW_PROVISION_ACCOUNTS", "false").lower() == "true"
):
    from django.core.management import call_command

    call_command("provision_production_accounts")
