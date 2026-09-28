import csv
from datetime import datetime, timedelta

from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_GET
from django.utils.dateparse import parse_datetime

from .models import AuditEvent
from apps.organization.context import current_membership


def audit_api(request):
    if not request.user.is_authenticated:
        return JsonResponse({'detail': 'Authentication credentials were not provided.'}, status=401)
    membership = current_membership(request)
    if membership is None or not membership.has_permission('view_reports'):
        return JsonResponse({'detail': 'Audit access required.'}, status=403)

    events = AuditEvent.objects.filter(organization=membership.organization).select_related('actor')
    action = request.GET.get('action', '').strip()
    entity_type = request.GET.get('entity_type', '').strip()
    actor = request.GET.get('actor', '').strip()
    search = request.GET.get('q', '').strip()
    since = request.GET.get('since', '').strip()
    until = request.GET.get('until', '').strip()
    if action:
        events = events.filter(action__icontains=action)
    if entity_type:
        events = events.filter(entity_type__iexact=entity_type)
    if actor:
        events = events.filter(actor__username__icontains=actor)
    if search:
        events = events.filter(details__icontains=search)
    if since:
        parsed_since = parse_datetime(since)
        if parsed_since is None:
            return JsonResponse({'detail': 'Invalid since datetime. Use ISO-8601.'}, status=400)
        events = events.filter(created_at__gte=parsed_since)
    if until:
        parsed_until = parse_datetime(until)
        if parsed_until is None:
            return JsonResponse({'detail': 'Invalid until datetime. Use ISO-8601.'}, status=400)
        events = events.filter(created_at__lte=parsed_until)
    try:
        limit = min(max(int(request.GET.get('limit', '100')), 1), 500)
    except ValueError:
        return JsonResponse({'detail': 'limit must be an integer between 1 and 500.'}, status=400)
    if request.GET.get('format') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="audit-log.csv"'
        writer = csv.writer(response)
        writer.writerow(['Timestamp', 'Action', 'Entity Type', 'Entity ID', 'Actor', 'Details'])
        for event in events[:limit]:
            writer.writerow([
                event.created_at.isoformat(),
                event.action,
                event.entity_type,
                event.entity_id,
                event.actor.username if event.actor else '',
                event.details,
            ])
        return response

    return JsonResponse({
        'count': events.count(),
        'results': [{
            'id': str(event.id),
            'timestamp': event.created_at.isoformat(),
            'action': event.action,
            'entity_type': event.entity_type,
            'entity_id': event.entity_id,
            'actor': event.actor.username if event.actor else None,
            'details': event.details,
        } for event in events[:limit]],
    })


@require_GET
def retention_status(request):
    if not request.user.is_authenticated:
        return JsonResponse({'detail': 'Authentication credentials were not provided.'}, status=401)
    membership = current_membership(request)
    if membership is None or not membership.has_permission('view_reports'):
        return JsonResponse({'detail': 'Audit access required.'}, status=403)
    cutoff = datetime.now().astimezone() - timedelta(days=membership.organization.audit_retention_days)
    oldest = AuditEvent.objects.filter(organization=membership.organization).order_by('created_at').values_list('created_at', flat=True).first()
    return JsonResponse({
        'audit_retention_days': membership.organization.audit_retention_days,
        'audit_cutoff': cutoff.isoformat(),
        'oldest_event': oldest.isoformat() if oldest else None,
        'document_retention_days': membership.organization.document_retention_days,
    })
