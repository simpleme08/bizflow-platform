from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.employees.models import Employee
from apps.organization.models import Organization, OrganizationMembership

from .models import PayrollPeriod, PayrollRecord


class PayrollAuthoritySeparationTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.organization = Organization.objects.create(name='Authority Test Co', slug='authority-test')
        self.processor = User.objects.create_user(username='processor', password='password')
        self.approver = User.objects.create_user(username='approver', password='password')
        self.payer = User.objects.create_user(username='payer', password='password')
        OrganizationMembership.objects.create(organization=self.organization, user=self.processor, role=OrganizationMembership.Role.HR)
        OrganizationMembership.objects.create(organization=self.organization, user=self.approver, role=OrganizationMembership.Role.CEO)
        OrganizationMembership.objects.create(organization=self.organization, user=self.payer, role=OrganizationMembership.Role.OWNER)
        employee_user = User.objects.create_user(username='authority-employee', password='password')
        self.employee = Employee.objects.create(
            employee_number='AUTH-001', user=employee_user, organization=self.organization,
            first_name='Test', last_name='Employee',
        )
        self.period = PayrollPeriod.objects.create(
            organization=self.organization, name='Authority Test Period',
            start_date=date(2026, 8, 1), end_date=date(2026, 8, 15),
            status=PayrollPeriod.Status.CALCULATED, processed_by=self.processor,
        )
        self.record = PayrollRecord.objects.create(
            employee=self.employee, payroll_period=self.period,
            basic_pay=Decimal('10000.00'), gross_pay=Decimal('10000.00'), net_pay=Decimal('10000.00'),
        )

    def test_processor_cannot_approve_own_payroll(self):
        self.client.login(username='processor', password='password')
        response = self.client.post(f'/api/payroll/{self.record.id}/approve/')
        self.assertEqual(response.status_code, 409)
        self.record.refresh_from_db()
        self.assertEqual(self.record.status, PayrollRecord.Status.DRAFT)

    def test_non_approver_cannot_approve_payroll(self):
        self.client.login(username='processor', password='password')
        response = self.client.post(f'/api/payroll/{self.record.id}/approve/')
        self.assertEqual(response.status_code, 409)

    def test_approver_can_approve_but_cannot_pay(self):
        self.client.login(username='approver', password='password')
        response = self.client.post(f'/api/payroll/{self.record.id}/approve/')
        self.assertEqual(response.status_code, 200)
        self.record.refresh_from_db()
        self.assertEqual(self.record.status, PayrollRecord.Status.APPROVED)
        self.period.refresh_from_db()
        self.assertEqual(self.period.approved_by_id, self.approver.id)

        response = self.client.post(f'/api/payroll/{self.record.id}/pay/')
        self.assertEqual(response.status_code, 403)

    def test_payment_authority_must_be_distinct_from_processor_and_approver(self):
        self.client.login(username='approver', password='password')
        self.assertEqual(self.client.post(f'/api/payroll/{self.record.id}/approve/').status_code, 200)
        self.client.logout()

        self.client.login(username='payer', password='password')
        response = self.client.post(f'/api/payroll/{self.record.id}/pay/')
        self.assertEqual(response.status_code, 200)
        self.record.refresh_from_db()
        self.period.refresh_from_db()
        self.assertEqual(self.record.status, PayrollRecord.Status.PAID)
        self.assertEqual(self.period.paid_by_id, self.payer.id)
        self.assertEqual(self.period.status, PayrollPeriod.Status.PAID)
