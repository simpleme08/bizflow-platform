from datetime import date, time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.employees.models import Employee
from apps.organization.models import Organization, OrganizationMembership
from apps.workforce.models import ShiftTemplate
from apps.employees.models import EmployeeAssignment

from .confidence import PayrollConfidenceEngine
from .models import EmployeeSalary, PayrollPeriod, PayrollWageRate


class PayrollConfidenceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='confidence-user', password='password')
        self.organization = Organization.objects.create(name='Confidence Corp', slug='confidence-corp')
        OrganizationMembership.objects.create(organization=self.organization, user=self.user, role=OrganizationMembership.Role.HR)
        self.employee = Employee.objects.create(
            employee_number='CONF-001', user=self.user, organization=self.organization,
            first_name='Confidence', last_name='Agent'
        )
        shift = ShiftTemplate.objects.create(name='Confidence Shift', start_time=time(8), end_time=time(17))
        EmployeeAssignment.objects.create(employee=self.employee, shift_template=shift, start_date=date(2026, 1, 1), is_primary=True)
        EmployeeSalary.objects.create(employee=self.employee, basic_salary=Decimal('20000.00'), effective_date=date(2026, 1, 1))
        self.period = PayrollPeriod.objects.create(
            organization=self.organization, name='September 1-15, 2026',
            start_date=date(2026, 9, 1), end_date=date(2026, 9, 15)
        )

    def test_missing_payroll_profile_is_review_not_silent_ready(self):
        result = PayrollConfidenceEngine.preflight(self.period, self.organization)
        self.assertTrue(result['ok'])
        self.assertEqual(result['status'], PayrollConfidenceEngine.REVIEW)
        self.assertTrue(any('payroll profile' in warning for warning in result['warnings']))

    def test_mwe_without_effective_wage_rate_is_blocked(self):
        from .models import PayrollProfile
        PayrollProfile.objects.create(
            employee=self.employee, minimum_wage_earner=True,
            wage_region='NCR', wage_category='NON_AGRICULTURE'
        )
        result = PayrollConfidenceEngine.preflight(self.period, self.organization)
        self.assertEqual(result['status'], PayrollConfidenceEngine.BLOCKED)
        self.assertTrue(any('no effective wage rate' in error for error in result['errors']))

    def test_effective_wage_rate_allows_mwe_to_pass_wage_gate(self):
        from .models import PayrollProfile
        PayrollProfile.objects.create(
            employee=self.employee, minimum_wage_earner=True,
            wage_region='NCR', wage_category='NON_AGRICULTURE'
        )
        PayrollWageRate.objects.create(
            organization=self.organization, region_code='NCR', category='NON_AGRICULTURE',
            daily_rate=Decimal('700.00'), effective_from=date(2026, 1, 1)
        )
        result = PayrollConfidenceEngine.preflight(self.period, self.organization)
        self.assertNotEqual(result['status'], PayrollConfidenceEngine.BLOCKED)
        self.assertFalse(any('no effective wage rate' in error for error in result['errors']))
