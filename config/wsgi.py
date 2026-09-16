"""
WSGI config for config project.

It exposes the WSGI callable as a module-level variable named ``application``.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_wsgi_application()

# Compatibility path for an existing Render service whose start command has not
# yet been switched to the repository's current render.yaml. It is deliberately
# opt-in and only runs when every required production credential is present.
# Missing bootstrap credentials must never prevent the web process from starting.
if (
    os.environ.get("DJANGO_ENV", "development").lower() == "production"
    and os.environ.get("BIZFLOW_PROVISION_ON_WSGI", "false").lower() == "true"
):
    required = (
        "BIZFLOW_PRODUCTION_ORG_SLUG",
        "BIZFLOW_PRODUCTION_ORG_NAME",
        "BIZFLOW_PRODUCTION_HR_USERNAME",
        "BIZFLOW_PRODUCTION_HR_PASSWORD",
        "BIZFLOW_PRODUCTION_SME_USERNAME",
        "BIZFLOW_PRODUCTION_SME_PASSWORD",
        "BIZFLOW_PRODUCTION_SUPER_USER_USERNAME",
        "BIZFLOW_PRODUCTION_SUPER_USER_PASSWORD",
    )
    if all(os.environ.get(name, "").strip() for name in required):
        from django.core.management import call_command

        call_command("provision_production_accounts")
