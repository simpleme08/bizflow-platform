from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.employees.models import Employee
from apps.organization.models import Organization, OrganizationMembership

from .completion import apply_record_adjustments, loan_deduction_for_record, settle_loans_for_record
from .loan_models import EmployeeLoan
from .models import PayrollAdjustment, PayrollPeriod, PayrollProfile, PayrollRecord


class PayrollCompletionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='completion-manager', password='password')
        self.organization = Organization.objects.create(name='Completion Co', slug='completion-co')
        OrganizationMembership.objects.create(organization=self.organization, user=self.user, role=OrganizationMembership.Role.HR)
        employee_user = get_user_model().objects.create_user(username='completion-employee', password='password')
        self.employee = Employee.objects.create(
            employee_number='C-001', user=employee_user, organization=self.organization,
            first_name='Complete', last_name='Employee',
        )
        PayrollProfile.objects.create(
            employee=self.employee, sss_number='01-1234567-8',
            philhealth_number='12-345678901-2', pagibig_number='123456789012',
        )
        self.period = PayrollPeriod.objects.create(
            organization=self.organization, name='September 2026',
            start_date=date(2026, 9, 1), end_date=date(2026, 9, 15),
        )
        self.record = PayrollRecord.objects.create(
            employee=self.employee, payroll_period=self.period,
            basic_pay=Decimal('10000.00'), gross_pay=Decimal('10000.00'),
            net_pay=Decimal('10000.00'),
        )

    def test_adjustments_apply_once(self):
        earning = PayrollAdjustment.objects.create(
            payroll_record=self.record, kind=PayrollAdjustment.Kind.EARNING,
            description='Approved correction', amount=Decimal('500.00'), approved=True,
        )
        deduction = PayrollAdjustment.objects.create(
            payroll_record=self.record, kind=PayrollAdjustment.Kind.DEDUCTION,
            description='Approved deduction', amount=Decimal('100.00'), approved=True,
        )
        apply_record_adjustments(self.record)
        self.record.refresh_from_db()
        self.assertEqual(self.record.gross_pay, Decimal('10500.00'))
        self.assertEqual(self.record.other_deductions, Decimal('100.00'))
        self.assertTrue(PayrollAdjustment.objects.get(pk=earning.pk).applied)
        self.assertTrue(PayrollAdjustment.objects.get(pk=deduction.pk).applied)
        first_net = self.record.net_pay
        apply_record_adjustments(self.record)
        self.record.refresh_from_db()
        self.assertEqual(self.record.gross_pay, Decimal('10500.00'))
        self.assertEqual(self.record.net_pay, first_net)

    def test_loan_preview_and_settlement_respect_balance(self):
        loan = EmployeeLoan.objects.create(
            employee=self.employee, lender='SSS', loan_type='Salary Loan',
            principal=Decimal('1000.00'), interest=Decimal('0.00'),
            installment_amount=Decimal('700.00'), balance=Decimal('500.00'),
            start_date=date(2026, 9, 1), end_date=date(2026, 12, 31),
        )
        self.assertEqual(loan_deduction_for_record(self.record), Decimal('500.00'))
        self.record.loan_deductions = Decimal('500.00')
        settled = settle_loans_for_record(self.record)
        self.assertEqual(settled, Decimal('500.00'))
        loan.refresh_from_db()
        self.assertEqual(loan.balance, Decimal('0.00'))
        self.assertEqual(loan.status, EmployeeLoan.Status.PAID)

    def test_remittance_exports_are_organization_scoped(self):
        self.client.login(username='completion-manager', password='password')
        response = self.client.get(f'/api/payroll/remittance/{self.period.id}/sss/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('SSS Number', response.content.decode())
        self.assertIn('01-1234567-8', response.content.decode())

    def test_unsupported_remittance_export_is_rejected(self):
        self.client.login(username='completion-manager', password='password')
        response = self.client.get(f'/api/payroll/remittance/{self.period.id}/not-real/')
        self.assertEqual(response.status_code, 404)
