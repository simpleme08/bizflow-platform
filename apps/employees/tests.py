from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.organization.models import Organization, OrganizationMembership
from apps.workforce.models import ShiftTemplate

from .models import Employee, EmployeeAssignment, EmploymentHistory


class EmployeeDirectoryTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username='manager', password='password')
        self.organization = Organization.objects.create(name='Acme', slug='acme')
        OrganizationMembership.objects.create(organization=self.organization, user=self.user, role='MANAGER')
        employee_user = User.objects.create_user(username='juan', password='password')
        self.employee = Employee.objects.create(employee_number='EMP-1', user=employee_user, organization=self.organization, first_name='Juan', last_name='Cruz')
        shift = ShiftTemplate.objects.create(name='Day', start_time='08:00', end_time='17:00')
        EmployeeAssignment.objects.create(employee=self.employee, shift_template=shift, start_date='2026-01-01', is_primary=True)

    def test_directory_returns_organization_employees(self):
        self.client.login(username='manager', password='password')
        response = self.client.get('/api/employees/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['employees'][0]['name'], 'Juan Cruz')
        self.assertEqual(response.json()['employees'][0]['assignments'][0]['shift'], 'Day')

    def test_self_profile_is_available(self):
        self.client.login(username='juan', password='password')
        response = self.client.get(f'/api/employees/{self.employee.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('personal_email', response.json()['employee'])

    def test_manager_cannot_change_lifecycle(self):
        self.client.login(username='manager', password='password')
        response = self.client.post(f'/api/employees/{self.employee.id}/lifecycle/', data='{"status":"REGULAR","effective_date":"2026-09-01"}', content_type='application/json')
        self.assertEqual(response.status_code, 403)


class EmployeeLifecycleTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.hr = User.objects.create_user(username='hr', password='password')
        self.org = Organization.objects.create(name='Acme', slug='acme')
        OrganizationMembership.objects.create(organization=self.org, user=self.hr, role='HR')
        employee_user = User.objects.create_user(username='employee', password='password')
        self.employee = Employee.objects.create(employee_number='EMP-2', user=employee_user, organization=self.org, first_name='Ana', last_name='Santos')

    def test_regularization_updates_employee_and_history(self):
        self.client.login(username='hr', password='password')
        response = self.client.post(f'/api/employees/{self.employee.id}/lifecycle/', data='{"status":"REGULAR","effective_date":"2026-09-01","reason":"Passed probation"}', content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.status, Employee.Status.REGULAR)
        self.assertEqual(str(self.employee.regularization_date), '2026-09-01')
        self.assertEqual(EmploymentHistory.objects.filter(employee=self.employee, status='REGULAR').count(), 1)

    def test_termination_deactivates_employee(self):
        self.client.login(username='hr', password='password')
        response = self.client.post(f'/api/employees/{self.employee.id}/lifecycle/', data='{"status":"TERMINATED","effective_date":"2026-09-10","reason":"End of employment"}', content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.employee.refresh_from_db()
        self.assertFalse(self.employee.is_active)
        self.assertEqual(self.employee.status, Employee.Status.TERMINATED)
        self.assertEqual(str(self.employee.separation_date), '2026-09-10')

    def test_other_organization_is_not_visible(self):
        other = Organization.objects.create(name='Other', slug='other')
        other_user = get_user_model().objects.create_user(username='otheremployee', password='password')
        other_employee = Employee.objects.create(employee_number='EMP-3', user=other_user, organization=other, first_name='Other', last_name='Person')
        self.client.login(username='hr', password='password')
        response = self.client.get(f'/api/employees/{other_employee.id}/')
        self.assertEqual(response.status_code, 404)
