from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.employees.models import Employee
from apps.organization.models import Organization, OrganizationMembership
from apps.payroll.models import PayrollAdjustment, PayrollPeriod, PayrollRecord


class PayrollAdjustmentApprovalHardeningTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username='hr-adjustment', password='test-password')
        self.employee_user = User.objects.create_user(username='employee-adjustment', password='test-password')
        self.organization = Organization.objects.create(name='Adjustment Test Org', slug='adjustment-test-org')
        OrganizationMembership.objects.create(
            user=self.user,
            organization=self.organization,
            role=OrganizationMembership.Role.HR,
            is_active=True,
        )
        self.employee = Employee.objects.create(
            organization=self.organization,
            user=self.employee_user,
            employee_number='EMP-ADJ-001',
            first_name='Test',
            last_name='Employee',
            is_active=True,
        )
        self.period = PayrollPeriod.objects.create(
            organization=self.organization,
            name='Adjustment Test Period',
            start_date='2026-09-01',
            end_date='2026-09-15',
            status=PayrollPeriod.Status.CALCULATED,
        )
        self.record = PayrollRecord.objects.create(
            employee=self.employee,
            payroll_period=self.period,
            status=PayrollRecord.Status.DRAFT,
            basic_pay=Decimal('10000.00'),
            gross_pay=Decimal('10000.00'),
            net_pay=Decimal('10000.00'),
        )
        self.client.login(username='hr-adjustment', password='test-password')
        self.session = self.client.session
        self.session['active_organization_id'] = str(self.organization.id)
        self.session.save()

    def test_adjustment_cannot_be_created_as_approved(self):
        response = self.client.post(
            reverse('create-payroll-adjustment', kwargs={'record_id': self.record.id}),
            {
                'kind': PayrollAdjustment.Kind.EARNING,
                'description': 'Manual earning',
                'amount': '500.00',
                'taxable': 'true',
                'approved': 'true',
            },
        )
        self.assertEqual(response.status_code, 201)
        adjustment = PayrollAdjustment.objects.get(id=response.json()['id'])
        self.assertFalse(adjustment.approved)
        self.assertEqual(adjustment.amount, Decimal('500.00'))
