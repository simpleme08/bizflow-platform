from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.employees.models import Employee
from apps.organization.models import Organization

from .models import EmployeeSalary, PayrollPeriod, PayrollProfile, PayrollWageRate
from .services import PayrollCalculator


class MWEPayrollIntegrationTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(username='mwe-user', password='password')
        self.organization = Organization.objects.create(name='MWE Co', slug='mwe-co')
        self.employee = Employee.objects.create(
            employee_number='MWE-001', user=user, organization=self.organization,
            first_name='Mia', last_name='Worker',
        )
        EmployeeSalary.objects.create(employee=self.employee, basic_salary=Decimal('11110.00'), effective_date=date(2026, 1, 1))
        PayrollProfile.objects.create(
            employee=self.employee, minimum_wage_earner=True,
            wage_region='CAR', wage_category='NON_AGRICULTURE',
        )
        PayrollWageRate.objects.create(
            organization=self.organization, region_code='CAR', category='NON_AGRICULTURE',
            daily_rate=Decimal('505.00'), effective_from=date(2026, 1, 1), wage_order='CAR-24',
        )
        self.period = PayrollPeriod.objects.create(
            organization=self.organization, name='MWE Test',
            start_date=date(2026, 8, 1), end_date=date(2026, 8, 15),
        )

    def test_exact_configured_rate_exempts_qualifying_mwe_income(self):
        result = PayrollCalculator.calculate(
            self.employee, self.period,
            allowances=Decimal('2000.00'), commissions=Decimal('1000.00'),
        )
        self.assertEqual(result['withholding_tax'], Decimal('0.00'))

    def test_mwe_flag_without_configured_rate_does_not_blanket_exempt_tax(self):
        PayrollWageRate.objects.all().delete()
        result = PayrollCalculator.calculate(
            self.employee, self.period,
            allowances=Decimal('10000.00'), commissions=Decimal('10000.00'),
        )
        self.assertGreater(result['withholding_tax'], Decimal('0.00'))
