from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render

from .client_sites import CLIENT_SITES


def website(request):
    clients = [
        {
            "slug": slug,
            "name": profile.get("name", slug.replace("-", " ").title()),
            "short_name": profile.get("short_name", "Client"),
            "eyebrow": profile.get("eyebrow", "Client workspace"),
            "website": f"/client/{slug}/",
            "login": f"/login/?org={slug}",
        }
        for slug, profile in CLIENT_SITES.items()
    ]
    return render(request, 'website.html', {"clients": clients})


def health(request):
    return JsonResponse({'status': 'ok'})


def readiness(request):
    checks = {'database': 'ok', 'cache': 'ok'}
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
    except Exception:
        checks['database'] = 'unavailable'

    try:
        cache.get('bizflow:readiness')
    except Exception:
        checks['cache'] = 'unavailable'

    if any(value != 'ok' for value in checks.values()):
        return JsonResponse({'status': 'not_ready', **checks}, status=503)
    return JsonResponse({'status': 'ready', **checks})
