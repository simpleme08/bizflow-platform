from django.db import connection
from django.http import JsonResponse
from django.shortcuts import redirect, render

from .client_sites import CLIENT_SITES


def website(request):
    """Public BizFlow marketing site.

    The marketing surface is intentionally separate from the HRIS application.
    Customers can keep their own public website and link employees/admins to
    the canonical HRIS host configured by BIZFLOW_APP_URL.
    """
    app_url = request.build_absolute_uri('/').rstrip('/')
    configured_app_url = request.META.get('HTTP_X_BIZFLOW_APP_URL') or app_url
    clients = [
        {
            "slug": slug,
            "name": profile.get("name", slug.replace("-", " ").title()),
            "short_name": profile.get("short_name", "Client"),
            "eyebrow": profile.get("eyebrow", "Client website"),
            "website": f"/client/{slug}/",
            "login": f"{configured_app_url}/login/?org={slug}",
        }
        for slug, profile in CLIENT_SITES.items()
    ]
    return render(request, 'website.html', {"clients": clients, "app_url": configured_app_url})


def health(request):
    return JsonResponse({'status': 'ok'})


def readiness(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
    except Exception:
        return JsonResponse({'status': 'not_ready', 'database': 'unavailable'}, status=503)
    return JsonResponse({'status': 'ready', 'database': 'ok'})
