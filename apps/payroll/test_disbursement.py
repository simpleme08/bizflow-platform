from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model

from apps.organization.models import Organization, OrganizationMembership
from apps.employees.models import Employee
from .models import PayrollPeriod, PayrollProfile, PayrollRecord
from .disbursement import build_bank_disbursement_csv


class BankDisbursementTests(TestCase):
    def setUp(self):
        User=get_user_model()
        self.user=User.objects.create_user(username='payroll-test',password='safe-password')
        self.org=Organization.objects.create(name='Disbursement Test Org', code='DTO')
        OrganizationMembership.objects.create(user=self.user, organization=self.org, role='ADMIN', is_active=True)
        self.employee=Employee.objects.create(organization=self.org, employee_number='E-001', first_name='Ana', last_name='Test', status=Employee.Status.ACTIVE, is_active=True)
        self.period=PayrollPeriod.objects.create(organization=self.org,name='September 2026',start_date='2026-09-01',end_date='2026-09-15',status=PayrollPeriod.Status.APPROVED)
        self.record=PayrollRecord.objects.create(employee=self.employee,payroll_period=self.period,net_pay=Decimal('12500.00'),gross_pay=Decimal('13000.00'),status=PayrollRecord.Status.APPROVED)

    def test_export_requires_bank_details(self):
        with self.assertRaisesMessage(ValueError, 'Missing bank payout details'):
            build_bank_disbursement_csv(self.period)

    def test_export_contains_only_approved_or_paid_records(self):
        PayrollProfile.objects.create(employee=self.employee, bank_name='Test Bank', bank_account_name='Ana Test', bank_account_number='123456789')
        draft_employee=Employee.objects.create(organization=self.org,employee_number='E-002',first_name='Draft',last_name='Employee',status=Employee.Status.ACTIVE,is_active=True)
        PayrollRecord.objects.create(employee=draft_employee,payroll_period=self.period,net_pay=Decimal('9000.00'),gross_pay=Decimal('9000.00'),status=PayrollRecord.Status.DRAFT)
        payload, digest, count, total = build_bank_disbursement_csv(self.period)
        self.assertIn('123456789', payload)
        self.assertNotIn('9000.00', payload)
        self.assertEqual(count, 1)
        self.assertEqual(total, Decimal('12500.00'))
        self.assertEqual(len(digest), 64)

    def test_unapproved_period_is_blocked(self):
        self.period.status=PayrollPeriod.Status.OPEN
        self.period.save(update_fields=['status'])
        PayrollProfile.objects.create(employee=self.employee, bank_name='Test Bank', bank_account_name='Ana Test', bank_account_number='123456789')
        with self.assertRaisesMessage(ValueError, 'Payroll must be approved'):
            from .disbursement import prepare_bank_disbursement
            prepare_bank_disbursement(self.period, self.user)
