from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.employees.models import Employee
from apps.organization.models import Organization, OrganizationMembership

from .completion import final_pay_preview
from .models import EmployeeSalary


class FinalPayHardeningTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.manager = User.objects.create_user(username='final-pay-manager', password='test-password')
        self.employee_user = User.objects.create_user(username='final-pay-employee', password='test-password')
        self.organization = Organization.objects.create(name='Final Pay Org', slug='final-pay-org')
        OrganizationMembership.objects.create(
            user=self.manager,
            organization=self.organization,
            role=OrganizationMembership.Role.HR,
            is_active=True,
        )
        self.employee = Employee.objects.create(
            organization=self.organization,
            user=self.employee_user,
            employee_number='EMP-FINAL-001',
            first_name='Final',
            last_name='Pay',
            is_active=True,
        )
        EmployeeSalary.objects.create(
            employee=self.employee,
            basic_salary=Decimal('22000.00'),
            effective_date=date(2026, 1, 1),
        )
        self.client.login(username='final-pay-manager', password='test-password')
        session = self.client.session
        session['active_organization_id'] = str(self.organization.id)
        session.save()

    def test_preview_uses_explicit_worked_days_not_separation_day(self):
        result = final_pay_preview(
            self.employee,
            date(2026, 8, 31),
            Decimal('22000.00'),
            worked_days=10,
        )
        self.assertEqual(result['worked_days'], Decimal('10'))
        self.assertEqual(result['prorated_salary'], Decimal('10000.00'))
        self.assertEqual(result['gross_final_pay'], Decimal('10000.00'))
        self.assertEqual(result['net_final_pay'], Decimal('10000.00'))

    def test_preview_rejects_invalid_worked_days(self):
        with self.assertRaises(ValueError):
            final_pay_preview(self.employee, date(2026, 8, 31), Decimal('22000.00'), worked_days=32)
        with self.assertRaises(ValueError):
            final_pay_preview(self.employee, date(2026, 8, 31), Decimal('22000.00'), worked_days=-1)

    def test_api_requires_worked_days(self):
        response = self.client.post(
            reverse('payroll-final-pay'),
            {
                'employee_id': str(self.employee.id),
                'separation_date': '2026-08-31',
            },
        )
        self.assertEqual(response.status_code, 400)

    def test_api_uses_explicit_worked_days(self):
        response = self.client.post(
            reverse('payroll-final-pay'),
            {
                'employee_id': str(self.employee.id),
                'separation_date': '2026-08-31',
                'worked_days': '10',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['worked_days'], '10')
        self.assertEqual(response.json()['prorated_salary'], '10000.00')
