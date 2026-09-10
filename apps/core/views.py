from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render


def website(request):
    return render(request, 'website.html')


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
