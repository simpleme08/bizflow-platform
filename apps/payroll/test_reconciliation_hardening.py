from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from apps.employees.models import Employee
from apps.organization.models import Organization
from apps.payroll.models import EmployeeSalary, PayrollPeriod, PayrollRecord
from apps.payroll.services import PayrollCalculator


class PayrollReconciliationHardeningTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(slug='payroll-rounding', name='Payroll Rounding')
        self.employee = Employee.objects.create(
            employee_number='PR-001',
            user=User.objects.create_user(username='pr-employee', password='TestPass123!'),
            organization=self.org,
            first_name='Payroll',
            last_name='Employee',
            status=Employee.Status.REGULAR,
            is_active=True,
        )
        EmployeeSalary.objects.create(employee=self.employee, basic_salary=Decimal('12345.67'), effective_date=date(2026, 1, 1))

    def test_second_semimonthly_period_receives_month_end_remainder(self):
        first = PayrollPeriod.objects.create(
            organization=self.org, name='Jan 1-15', start_date=date(2026, 1, 1), end_date=date(2026, 1, 15),
            frequency=PayrollPeriod.Frequency.SEMI_MONTHLY,
        )
        second = PayrollPeriod.objects.create(
            organization=self.org, name='Jan 16-31', start_date=date(2026, 1, 16), end_date=date(2026, 1, 31),
            frequency=PayrollPeriod.Frequency.SEMI_MONTHLY,
        )
        first_values = PayrollCalculator._statutory_for_period(self.employee, first, Decimal('12345.67'))
        PayrollRecord.objects.create(employee=self.employee, payroll_period=first, status=PayrollRecord.Status.APPROVED, **first_values)
        second_values = PayrollCalculator._statutory_for_period(self.employee, second, Decimal('12345.67'))
        monthly = PayrollCalculator._statutory_for_period(self.employee, PayrollPeriod(organization=self.org, start_date=date(2026,1,1), end_date=date(2026,1,31), frequency=PayrollPeriod.Frequency.MONTHLY), Decimal('12345.67'))
        self.assertEqual(first_values['sss_employee'] + second_values['sss_employee'], monthly['sss_employee'])
        self.assertEqual(first_values['philhealth_employee'] + second_values['philhealth_employee'], monthly['philhealth_employee'])
        self.assertEqual(first_values['pagibig_employee'] + second_values['pagibig_employee'], monthly['pagibig_employee'])

    def test_annual_tax_ignores_draft_records(self):
        period = PayrollPeriod.objects.create(
            organization=self.org, name='Annual', start_date=date(2026, 12, 1), end_date=date(2026, 12, 31),
            frequency=PayrollPeriod.Frequency.MONTHLY,
        )
        PayrollRecord.objects.create(employee=self.employee, payroll_period=period, basic_pay=Decimal('100000'), gross_pay=Decimal('100000'), net_pay=Decimal('100000'), status=PayrollRecord.Status.DRAFT)
        result = PayrollCalculator.annual_tax_reconciliation(self.employee, 2026)
        self.assertEqual(result['taxable_income'], Decimal('0.00'))
