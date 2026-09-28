from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from apps.employees.models import Employee
from apps.organization.models import Organization
from apps.payroll.models import EmployeeSalary, PayrollPeriod, PayrollRecord, PayrollWageRate
from apps.payroll.services import PhilippinePayrollRules, PayrollCalculator


class StatutoryRuleRegressionTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(slug='stat-regression', name='Stat Regression')
        self.employee = Employee.objects.create(
            employee_number='STAT-001',
            user=User.objects.create_user(username='stat-employee', password='TestPass123!'),
            organization=self.org,
            first_name='Stat', last_name='Employee',
            status=Employee.Status.REGULAR, is_active=True,
        )
        EmployeeSalary.objects.create(employee=self.employee, basic_salary=Decimal('25000.00'), effective_date=date(2026, 1, 1))

    def test_2025_sss_rate_and_caps_are_registry_defaults(self):
        ee, er = PhilippinePayrollRules.sss(Decimal('50000'))
        self.assertEqual(ee, Decimal('1750.00'))
        self.assertEqual(er, Decimal('3530.00'))

    def test_2025_philhealth_floor_and_ceiling(self):
        ee, er = PhilippinePayrollRules.philhealth(Decimal('5000'))
        self.assertEqual(ee, Decimal('250.00'))
        ee, er = PhilippinePayrollRules.philhealth(Decimal('150000'))
        self.assertEqual(ee, Decimal('2500.00'))

    def test_mwe_without_effective_regional_rate_blocks_preflight(self):
        self.employee.payroll_profile = None
        from apps.payroll.models import PayrollProfile
        PayrollProfile.objects.create(employee=self.employee, minimum_wage_earner=True, wage_region='NCR')
        period = PayrollPeriod.objects.create(
            organization=self.org, name='MWE test', start_date=date(2026, 9, 1), end_date=date(2026, 9, 30),
            frequency=PayrollPeriod.Frequency.MONTHLY,
        )
        result = PayrollCalculator.preflight(period, self.org)
        self.assertTrue(any('effective regional wage rate' in error for error in result['errors']))

    def test_13th_month_audit_lists_calendar_year_basic_pay(self):
        period = PayrollPeriod.objects.create(
            organization=self.org, name='September', start_date=date(2026, 9, 1), end_date=date(2026, 9, 30),
            frequency=PayrollPeriod.Frequency.MONTHLY,
        )
        PayrollRecord.objects.create(employee=self.employee, payroll_period=period, basic_pay=Decimal('25000'), gross_pay=Decimal('25000'), net_pay=Decimal('23000'), status=PayrollRecord.Status.APPROVED)
        audit = PayrollCalculator.thirteenth_month_audit(self.employee, 2026)
        self.assertEqual(audit['earned_basic_salary'], '25000.00')
        self.assertEqual(audit['thirteenth_month'], '2083.33')
