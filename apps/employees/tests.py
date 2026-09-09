from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.organization.models import Organization, OrganizationMembership
from apps.workforce.models import ShiftTemplate

from .models import Employee, EmployeeAssignment


class EmployeeDirectoryTests(TestCase):
	def setUp(self):
		self.user = get_user_model().objects.create_user(username='manager', password='password')
		self.organization = Organization.objects.create(name='Acme', slug='acme')
		OrganizationMembership.objects.create(organization=self.organization, user=self.user, role='MANAGER')
		employee_user = get_user_model().objects.create_user(username='juan')
		employee = Employee.objects.create(
			employee_number='EMP-1',
			user=employee_user,
			organization=self.organization,
			first_name='Juan',
			last_name='Cruz',
		)
		shift = ShiftTemplate.objects.create(name='Day', start_time='08:00', end_time='17:00')
		EmployeeAssignment.objects.create(
			employee=employee,
			shift_template=shift,
			start_date='2026-01-01',
			is_primary=True,
		)

	def test_directory_returns_organization_employees(self):
		self.client.login(username='manager', password='password')

		response = self.client.get('/api/employees/')

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json()['employees'][0]['name'], 'Juan Cruz')
		self.assertEqual(response.json()['employees'][0]['assignments'][0]['shift'], 'Day')
