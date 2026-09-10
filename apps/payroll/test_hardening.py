from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.employees.models import Employee
from apps.organization.models import Organization

from .models import EmployeeSalary, PayrollAdjustment, PayrollPeriod, PayrollRecord


class PayrollImmutabilityTests(TestCase):
    def setUp(self):
        organization = Organization.objects.create(name='Hardening Co', slug='hardening-co')
        from django.contrib.auth import get_user_model
        user = get_user_model().objects.create_user(username='hardening-employee', password='password')
        self.employee = Employee.objects.create(
            employee_number='H-001', user=user, organization=organization,
            first_name='Test', last_name='Employee',
        )
        EmployeeSalary.objects.create(
            employee=self.employee, basic_salary=Decimal('20000.00'),
            effective_date=date(2026, 1, 1),
        )
        self.period = PayrollPeriod.objects.create(
            organization=organization, name='Hardening Period',
            start_date=date(2026, 8, 1), end_date=date(2026, 8, 15),
        )
        self.record = PayrollRecord.objects.create(
            employee=self.employee, payroll_period=self.period,
            basic_pay=Decimal('10000.00'), gross_pay=Decimal('10000.00'),
            net_pay=Decimal('10000.00'), status=PayrollRecord.Status.DRAFT,
        )

    def test_approved_record_cannot_have_amounts_changed(self):
        self.record.status = PayrollRecord.Status.APPROVED
        self.record.save(update_fields=('status', 'updated_at'))
        self.record.net_pay = Decimal('1.00')
        with self.assertRaises(ValidationError):
            self.record.save()

    def test_approved_record_can_transition_to_paid(self):
        self.record.status = PayrollRecord.Status.APPROVED
        self.record.save(update_fields=('status', 'updated_at'))
        self.record.status = PayrollRecord.Status.PAID
        self.record.save(update_fields=('status', 'updated_at'))
        self.record.refresh_from_db()
        self.assertEqual(self.record.status, PayrollRecord.Status.PAID)

    def test_paid_record_cannot_be_reopened(self):
        self.record.status = PayrollRecord.Status.PAID
        self.record.save(update_fields=('status', 'updated_at'))
        self.record.status = PayrollRecord.Status.APPROVED
        with self.assertRaises(ValidationError):
            self.record.save()

    def test_adjustments_cannot_be_changed_after_approval(self):
        self.record.status = PayrollRecord.Status.APPROVED
        self.record.save(update_fields=('status', 'updated_at'))
        with self.assertRaises(ValidationError):
            PayrollAdjustment.objects.create(
                payroll_record=self.record, kind=PayrollAdjustment.Kind.EARNING,
                description='Late bonus', amount=Decimal('100.00'), approved=True,
            )
