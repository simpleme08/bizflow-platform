from django.http import JsonResponse

from apps.organization.billing import active_employee_count, get_plan
from apps.organization.context import current_membership


def subscription_api(request):
    if not request.user.is_authenticated:
        return JsonResponse({'detail': 'Authentication credentials were not provided.'}, status=401)
    membership = current_membership(request)
    if membership is None:
        return JsonResponse({'detail': 'No active organization membership found.'}, status=403)
    if not membership.has_permission('manage_organization') and not membership.has_permission('view_reports'):
        return JsonResponse({'detail': 'Permission denied.'}, status=403)
    organization = membership.organization
    plan = get_plan(organization.plan_code)
    used = active_employee_count(organization)
    return JsonResponse({
        'plan': {
            'code': plan.code,
            'name': plan.name,
            'monthly_price': str(plan.monthly_price),
            'employee_limit': plan.employee_limit,
            'overage_per_employee': str(organization.overage_rate),
        },
        'subscription': {
            'status': organization.subscription_status,
            'trial_ends_at': organization.trial_ends_at.isoformat() if organization.trial_ends_at else None,
            'billing_customer_id': bool(organization.billing_customer_id),
        },
        'usage': {
            'active_employees': used,
            'remaining_employee_slots': max(plan.employee_limit - used, 0),
            'over_limit': used > plan.employee_limit,
        },
    })
