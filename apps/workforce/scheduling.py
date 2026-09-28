from datetime import date

from django.db.models import Q

from apps.workforce.models import CoverShift, ScheduleException, ScheduleRule


def resolve_schedule(employee, work_date):
    """Return the approved shift/rest-day decision for a date."""
    cover = CoverShift.objects.filter(
        employee=employee,
        work_date=work_date,
        status=CoverShift.Status.APPROVED,
    ).select_related('shift_template', 'client', 'client_site').first()
    if cover:
        return {
            'kind': 'COVER',
            'shift': cover.shift_template,
            'client': cover.client,
            'client_site': cover.client_site,
            'cover_shift': cover,
        }

    exception = ScheduleException.objects.filter(
        employee=employee,
        work_date=work_date,
        approved=True,
    ).select_related('shift_template').first()
    if exception:
        return {
            'kind': 'REST' if exception.is_rest_day else 'EXCEPTION',
            'shift': exception.shift_template,
            'client': None,
            'client_site': None,
            'cover_shift': None,
        }

    rules = ScheduleRule.objects.filter(
        employee=employee,
        is_active=True,
        effective_from__lte=work_date,
    ).filter(Q(effective_to__isnull=True) | Q(effective_to__gte=work_date)).select_related('shift_template').order_by('-priority', '-effective_from', '-created_at')

    weekday = work_date.weekday()
    for rule in rules:
        weekdays = {int(day) for day in rule.weekdays}
        if weekday not in weekdays or weekday in {int(day) for day in rule.rest_days}:
            continue
        if rule.pattern == ScheduleRule.Pattern.ROTATING and rule.cycle_weeks > 1:
            week_index = ((work_date - rule.effective_from).days // 7) % rule.cycle_weeks
            if week_index >= rule.cycle_weeks:
                continue
        return {
            'kind': 'SCHEDULED',
            'shift': rule.shift_template,
            'client': None,
            'client_site': None,
            'cover_shift': None,
        }

    return {'kind': 'REST', 'shift': None, 'client': None, 'client_site': None, 'cover_shift': None}


def is_workday(employee, work_date):
    return resolve_schedule(employee, work_date)['kind'] != 'REST'
