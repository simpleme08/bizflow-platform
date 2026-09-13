from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.employees.models import Employee
from apps.organization.models import Organization, OrganizationMembership

from .loan_models import EmployeeLoan


class PayrollLoanApiHardeningTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.organization = Organization.objects.create(name='Loan Test Co', slug='loan-test')
        self.other_organization = Organization.objects.create(name='Other Loan Co', slug='other-loan')
        self.manager = User.objects.create_user(username='loan-manager', password='password')
        OrganizationMembership.objects.create(
            organization=self.organization,
            user=self.manager,
            role=OrganizationMembership.Role.HR,
        )
        employee_user = User.objects.create_user(username='loan-employee', password='password')
        self.employee = Employee.objects.create(
            employee_number='LOAN-001',
            user=employee_user,
            organization=self.organization,
            first_name='Loan',
            last_name='Employee',
        )
        foreign_user = User.objects.create_user(username='foreign-loan-employee', password='password')
        self.foreign_employee = Employee.objects.create(
            employee_number='LOAN-002',
            user=foreign_user,
            organization=self.other_organization,
            first_name='Foreign',
            last_name='Employee',
        )
        self.url = '/api/payroll/loans/'

    def _valid_payload(self):
        return {
            'employee_id': str(self.employee.id),
            'lender': 'SSS',
            'loan_type': 'Salary Loan',
            'reference_number': 'REF-001',
            'principal': '10000.00',
            'interest': '500.00',
            'installment_amount': '1000.00',
            'start_date': '2026-08-01',
            'end_date': '2027-07-31',
        }

    def test_valid_loan_is_created(self):
        self.client.login(username='loan-manager', password='password')
        response = self.client.post(self.url, self._valid_payload())
        self.assertEqual(response.status_code, 201)
        loan = EmployeeLoan.objects.get(id=response.json()['id'])
        self.assertEqual(loan.balance, Decimal('10500.00'))
        self.assertEqual(loan.start_date, date(2026, 8, 1))

    def test_negative_principal_is_rejected(self):
        self.client.login(username='loan-manager', password='password')
        payload = self._valid_payload()
        payload['principal'] = '-1.00'
        response = self.client.post(self.url, payload)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(EmployeeLoan.objects.count(), 0)

    def test_invalid_date_range_is_rejected(self):
        self.client.login(username='loan-manager', password='password')
        payload = self._valid_payload()
        payload['end_date'] = '2026-07-31'
        response = self.client.post(self.url, payload)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(EmployeeLoan.objects.count(), 0)

    def test_malformed_decimal_is_rejected_without_internal_error(self):
        self.client.login(username='loan-manager', password='password')
        payload = self._valid_payload()
        payload['principal'] = 'not-a-number'
        response = self.client.post(self.url, payload)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['detail'], 'Invalid loan data.')
        self.assertEqual(EmployeeLoan.objects.count(), 0)

    def test_foreign_employee_cannot_create_loan(self):
        self.client.login(username='loan-manager', password='password')
        payload = self._valid_payload()
        payload['employee_id'] = str(self.foreign_employee.id)
        response = self.client.post(self.url, payload)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(EmployeeLoan.objects.count(), 0)

    def test_loan_list_is_tenant_scoped(self):
        EmployeeLoan.objects.create(
            employee=self.employee,
            lender='SSS',
            loan_type='Salary Loan',
            principal=Decimal('10000.00'),
            interest=Decimal('0.00'),
            installment_amount=Decimal('1000.00'),
            start_date=date(2026, 8, 1),
            end_date=date(2027, 5, 31),
            balance=Decimal('10000.00'),
        )
        EmployeeLoan.objects.create(
            employee=self.foreign_employee,
            lender='SSS',
            loan_type='Salary Loan',
            principal=Decimal('20000.00'),
            interest=Decimal('0.00'),
            installment_amount=Decimal('2000.00'),
            start_date=date(2026, 8, 1),
            end_date=date(2027, 5, 31),
            balance=Decimal('20000.00'),
        )
        self.client.login(username='loan-manager', password='password')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        loans = response.json()['loans']
        self.assertEqual(len(loans), 1)
        self.assertEqual(loans[0]['employee_id'], str(self.employee.id))
