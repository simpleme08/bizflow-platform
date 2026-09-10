from django.utils import timezone

from .billing import can_activate_employee, get_plan


def subscription_allows_operations(organization):
    if not organization.is_active:
        return False
    return organization.subscription_status in {'TRIALING', 'ACTIVE'} or organization.subscription_status == 'PAST_DUE'


def activation_allowed(organization, *, excluding_employee_id=None):
    if not subscription_allows_operations(organization):
        return False
    if organization.subscription_status == 'TRIALING' and organization.trial_ends_at and timezone.now() > organization.trial_ends_at:
        return False
    return can_activate_employee(organization, excluding_employee_id=excluding_employee_id)


def plan_summary(organization):
    plan = get_plan(organization.plan_code)
    return {'code': plan.code, 'name': plan.name, 'limit': plan.employee_limit, 'monthly_price': str(plan.monthly_price)}
