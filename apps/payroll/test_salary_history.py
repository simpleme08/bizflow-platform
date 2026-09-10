from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.employees.models import Employee
from apps.organization.models import Organization

from .models import EmployeeSalary, EmployeeSalaryHistory, PayrollPeriod
from .services import PayrollCalculator


class SalaryHistoryPayrollTests(TestCase):
    def setUp(self):
        organization = Organization.objects.create(name='Salary History Co', slug='salary-history-co')
        user = get_user_model().objects.create_user(username='salary-history-employee', password='password')
        self.employee = Employee.objects.create(
            employee_number='EMP-SAL-1',
            user=user,
            organization=organization,
            first_name='Salary',
            last_name='History',
        )
        EmployeeSalary.objects.create(
            employee=self.employee,
            basic_salary=Decimal('20000.00'),
            effective_date=date(2026, 1, 1),
        )
        self.organization = organization

    def test_payroll_uses_salary_effective_at_period_end(self):
        EmployeeSalaryHistory.objects.create(
            employee=self.employee,
            basic_salary=Decimal('25000.00'),
            effective_date=date(2026, 8, 1),
            reason='Annual salary increase',
        )
        period = PayrollPeriod.objects.create(
            organization=self.organization,
            name='August 1-15, 2026',
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 15),
        )
        result = PayrollCalculator.calculate(self.employee, period)
        self.assertEqual(result['basic_pay'], Decimal('12500.00'))

    def test_payroll_keeps_prior_salary_before_effective_date(self):
        EmployeeSalaryHistory.objects.create(
            employee=self.employee,
            basic_salary=Decimal('25000.00'),
            effective_date=date(2026, 8, 1),
        )
        period = PayrollPeriod.objects.create(
            organization=self.organization,
            name='July 1-15, 2026',
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 15),
        )
        result = PayrollCalculator.calculate(self.employee, period)
        self.assertEqual(result['basic_pay'], Decimal('10000.00'))
