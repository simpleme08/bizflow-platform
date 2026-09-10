from decimal import Decimal

from django.test import TestCase
from django.contrib.auth import get_user_model

from apps.organization.billing import PLANS, active_employee_count, can_activate_employee, get_plan
from apps.organization.models import Organization
from apps.employees.models import Employee


class SubscriptionPlanTests(TestCase):
    def test_plan_catalog(self):
        self.assertEqual(get_plan('STARTER').employee_limit, 10)
        self.assertEqual(get_plan('GROWTH').monthly_price, Decimal('1499.00'))
        self.assertEqual(get_plan('BUSINESS').employee_limit, 75)
        self.assertEqual(len(PLANS), 4)

    def test_employee_limit_uses_active_employees_only(self):
        org = Organization.objects.create(name='Acme', slug='acme')
        org.plan_code = Organization.Plan.FREE
        org.save(update_fields=['plan_code'])
        User = get_user_model()
        for i in range(5):
            user = User.objects.create_user(username=f'e{i}')
            Employee.objects.create(employee_number=f'E{i}', user=user, organization=org, first_name='A', last_name=str(i), status=Employee.Status.REGULAR, is_active=True)
        self.assertEqual(active_employee_count(org), 5)
        self.assertFalse(can_activate_employee(org))
        inactive_user = User.objects.create_user(username='inactive')
        Employee.objects.create(employee_number='EI', user=inactive_user, organization=org, first_name='I', last_name='N', status=Employee.Status.SEPARATED, is_active=False)
        self.assertEqual(active_employee_count(org), 5)
        self.assertFalse(can_activate_employee(org))
