from datetime import date

from django.db.models import Q

from apps.workforce.models import CoverShift, ScheduleException, ScheduleRule, ShiftTemplate
from apps.employees.models import EmployeeAssignment


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

    has_effective_rules = rules.exists()
    weekday = work_date.weekday()
    for rule in rules:
        weekdays = {int(day) for day in rule.weekdays}
        if weekday not in weekdays or weekday in {int(day) for day in rule.rest_days}:
            continue
        shift = rule.shift_template
        if rule.pattern == ScheduleRule.Pattern.ROTATING and rule.rotation_shifts:
            week_index = ((work_date - rule.effective_from).days // 7) % len(rule.rotation_shifts)
            try:
                shift = ShiftTemplate.objects.filter(id=rule.rotation_shifts[week_index]).filter(Q(organization=employee.organization) | Q(organization__isnull=True)).first()
            except (TypeError, ValueError):
                shift = None
            if shift is None:
                continue
        return {
            'kind': 'SCHEDULED',
            'shift': shift,
            'client': None,
            'client_site': None,
            'cover_shift': None,
        }

    # An effective recurring rule also defines its off-days. Do not let a legacy
    # assignment silently turn an explicit rule rest-day back into a workday.
    if has_effective_rules:
        return {'kind': 'REST', 'shift': None, 'client': None, 'client_site': None, 'cover_shift': None}

    # Legacy/effective-dated assignments are the base schedule when no recurring
    # rule or approved date-specific override applies. Keep the same precedence
    # for every consumer, including ESS and the manager calendar.
    assignment = EmployeeAssignment.objects.filter(
        employee=employee,
        start_date__lte=work_date,
    ).filter(Q(end_date__isnull=True) | Q(end_date__gte=work_date)).select_related(
        'shift_template', 'client', 'client_site'
    ).order_by('-is_primary', '-start_date', '-created_at').first()
    if assignment:
        return {
            'kind': 'SCHEDULED',
            'shift': assignment.shift_template,
            'client': assignment.client,
            'client_site': assignment.client_site,
            'cover_shift': None,
        }

    return {'kind': 'REST', 'shift': None, 'client': None, 'client_site': None, 'cover_shift': None}


def is_workday(employee, work_date):
    return resolve_schedule(employee, work_date)['kind'] != 'REST'
