from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.employees.models import Employee
from apps.organization.models import Organization, OrganizationMembership

from .models import PayrollPeriod, PayrollRecord


class PayrollSummaryApiTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username='summary-manager', password='password')
        self.organization = Organization.objects.create(name='Summary Co', slug='summary-co')
        OrganizationMembership.objects.create(organization=self.organization, user=self.user, role=OrganizationMembership.Role.HR)
        employee_user = user_model.objects.create_user(username='summary-employee', password='password')
        self.employee = Employee.objects.create(
            employee_number='SUM-001', user=employee_user, organization=self.organization,
            first_name='Summary', last_name='Employee',
        )
        self.period = PayrollPeriod.objects.create(
            organization=self.organization, name='September 2026',
            start_date='2026-09-01', end_date='2026-09-15',
        )
        PayrollRecord.objects.create(
            employee=self.employee, payroll_period=self.period,
            basic_pay=Decimal('10000.00'), gross_pay=Decimal('10500.00'),
            net_pay=Decimal('9000.00'), withholding_tax=Decimal('200.00'),
            sss_employee=Decimal('500.00'), philhealth_employee=Decimal('250.00'),
            pagibig_employee=Decimal('50.00'), sss_employer=Decimal('1015.00'),
            philhealth_employer=Decimal('250.00'), pagibig_employer=Decimal('50.00'),
        )

    def test_summary_is_organization_scoped_and_aggregates_payroll(self):
        self.client.force_login(self.user)
        response = self.client.get('/api/payroll/summary/', {'period_id': str(self.period.id)})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['headcount'], 1)
        self.assertEqual(response.json()['gross_pay'], '10500.00')
        self.assertEqual(response.json()['net_pay'], '9000.00')
        self.assertEqual(response.json()['employer_contributions'], '1315.00')
        self.assertEqual(response.json()['withholding_tax'], '200.00')

    def test_summary_requires_authentication(self):
        response = self.client.get('/api/payroll/summary/')
        self.assertEqual(response.status_code, 401)
