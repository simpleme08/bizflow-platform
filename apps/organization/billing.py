from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Plan:
    code: str
    name: str
    monthly_price: Decimal
    employee_limit: int
    overage_per_employee: Decimal


PLANS = {
    'FREE': Plan('FREE', 'Free', Decimal('0.00'), 5, Decimal('50.00')),
    'STARTER': Plan('STARTER', 'Starter', Decimal('499.00'), 10, Decimal('50.00')),
    'GROWTH': Plan('GROWTH', 'Growth', Decimal('1499.00'), 30, Decimal('40.00')),
    'BUSINESS': Plan('BUSINESS', 'Business', Decimal('2999.00'), 75, Decimal('30.00')),
}


def get_plan(code):
    return PLANS.get((code or 'FREE').upper(), PLANS['FREE'])


def active_employee_count(organization):
    return organization.employees.filter(is_active=True).count()


def can_activate_employee(organization, *, excluding_employee_id=None):
    plan = get_plan(getattr(organization, 'plan_code', 'FREE'))
    qs = organization.employees.filter(is_active=True)
    if excluding_employee_id:
        qs = qs.exclude(pk=excluding_employee_id)
    return qs.count() < plan.employee_limit
