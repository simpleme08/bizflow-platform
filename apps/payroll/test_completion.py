from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.employees.models import Employee
from apps.organization.models import Organization

from .completion import final_pay_preview, loan_deduction_for_record
from .loan_models import EmployeeLoan
from .models import EmployeeSalary, PayrollPeriod, PayrollRecord


class PayrollCompletionTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name='Completion Test')
        from django.contrib.auth import get_user_model
        user = get_user_model().objects.create_user(username='completion-user', password='password')
        self.employee = Employee.objects.create(
            employee_number='COMP-001', user=user, organization=self.organization,
            first_name='Test', last_name='Employee', is_active=True,
        )
        EmployeeSalary.objects.create(employee=self.employee, basic_salary=Decimal('22000'), effective_date=date(2026, 1, 1))
        self.period = PayrollPeriod.objects.create(
            organization=self.organization, name='Aug 1-15', start_date=date(2026, 8, 1), end_date=date(2026, 8, 15),
        )

    def test_loan_schedule_caps_at_balance(self):
        loan = EmployeeLoan.objects.create(
            employee=self.employee, lender='Company', loan_type='Salary Loan', principal=Decimal('10000'),
            interest=Decimal('0'), installment_amount=Decimal('3000'), start_date=date(2026, 8, 1), end_date=date(2027, 1, 1), balance=Decimal('2500'),
        )
        record = PayrollRecord.objects.create(employee=self.employee, payroll_period=self.period, net_pay=Decimal('10000'))
        self.assertEqual(loan_deduction_for_record(record), Decimal('2500.00'))

    def test_final_pay_preview_is_transparent(self):
        result = final_pay_preview(
            self.employee, date(2026, 8, 10), Decimal('22000'),
            thirteenth_month=Decimal('1000'), accrued_leave_pay=Decimal('500'), other_earnings=Decimal('250'), other_deductions=Decimal('100'), loan_balance=Decimal('1000'),
        )
        self.assertEqual(result['prorated_salary'], Decimal('10000.00'))
        self.assertEqual(result['gross_final_pay'], Decimal('11750.00'))
        self.assertEqual(result['net_final_pay'], Decimal('10650.00'))

    def test_negative_loan_values_rejected(self):
        loan = EmployeeLoan(
            employee=self.employee, lender='Company', loan_type='Invalid', principal=Decimal('-1'),
            installment_amount=Decimal('1'), start_date=date(2026, 8, 1), end_date=date(2027, 1, 1), balance=Decimal('0'),
        )
        with self.assertRaises(ValidationError):
            loan.full_clean()
