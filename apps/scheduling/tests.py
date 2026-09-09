from django.test import TestCase, Client as TestClient
from django.contrib.auth.models import User
from datetime import date
from decimal import Decimal

from apps.organization.models import Organization, OrganizationMembership, Department, Position, EmploymentType
from apps.employees.models import Employee, EmployeeAssignment
from apps.workforce.models import ShiftTemplate, Client, ClientSite


class ShiftSchedulingTests(TestCase):
	def setUp(self):
		self.client = TestClient()
		self.organization = Organization.objects.create(slug='test-org', name='Test Organization')
		self.user = User.objects.create_user(username='manager', password='TestPass123!')
		self.membership = OrganizationMembership.objects.create(
			user=self.user,
			organization=self.organization,
			role=OrganizationMembership.Role.MANAGER
		)
		self.client.login(username='manager', password='TestPass123!')
		
		# Create test data
		self.shift_day = ShiftTemplate.objects.create(name='Day Shift', start_time='08:00', end_time='17:00')
		self.shift_night = ShiftTemplate.objects.create(name='Night Shift', start_time='22:00', end_time='07:00')
		self.client_obj = Client.objects.create(organization=self.organization, code='TEST', name='Test Client')
		self.site = ClientSite.objects.create(client=self.client_obj, name='Test Site')
		
		self.employee = Employee.objects.create(
			employee_number='EMP-001',
			user=User.objects.create_user(username='emp1', password='EmpPass123!'),
			organization=self.organization,
			first_name='John',
			last_name='Doe',
			is_active=True,
		)
	
	def test_scheduling_page_requires_login(self):
		"""Shift scheduling page requires authentication."""
		self.client.logout()
		response = self.client.get('/scheduling/')
		self.assertEqual(response.status_code, 401)
	
	def test_get_shifts_returns_all_templates(self):
		"""Get shifts endpoint returns all available shift templates."""
		response = self.client.get('/api/scheduling/shifts/')
		self.assertEqual(response.status_code, 200)
		data = response.json()
		self.assertEqual(len(data['shifts']), 2)
		self.assertEqual(data['shifts'][0]['name'], 'Day Shift')
	
	def test_get_employees_returns_active_only(self):
		"""Get assignable employees returns only active employees in organization."""
		inactive = Employee.objects.create(
			employee_number='EMP-002',
			user=User.objects.create_user(username='emp2', password='EmpPass123!'),
			organization=self.organization,
			first_name='Jane',
			last_name='Smith',
			is_active=False,
		)
		response = self.client.get('/api/scheduling/employees/')
		self.assertEqual(response.status_code, 200)
		data = response.json()
		self.assertEqual(len(data['employees']), 1)
		self.assertEqual(data['employees'][0]['name'], 'John Doe')
	
	def test_assign_shift_creates_assignment(self):
		"""Assigning a shift creates an EmployeeAssignment."""
		response = self.client.post(
			'/api/scheduling/assign/',
			content_type='application/json',
			data={
				'employee_id': str(self.employee.id),
				'shift_id': str(self.shift_day.id),
				'client_id': str(self.client_obj.id),
				'site_id': str(self.site.id),
				'start_date': '2026-09-01',
				'end_date': None,
				'is_primary': True,
			}
		)
		self.assertEqual(response.status_code, 200)
		data = response.json()
		self.assertEqual(data['status'], 'created')
		
		# Verify assignment was created
		assignment = EmployeeAssignment.objects.filter(employee=self.employee).first()
		self.assertIsNotNone(assignment)
		self.assertEqual(assignment.shift_template, self.shift_day)
		self.assertEqual(assignment.client, self.client_obj)
		self.assertEqual(assignment.is_primary, True)
	
	def test_delete_assignment_removes_shift(self):
		"""Deleting an assignment removes the shift assignment."""
		assignment = EmployeeAssignment.objects.create(
			employee=self.employee,
			shift_template=self.shift_day,
			client=self.client_obj,
			start_date=date(2026, 9, 1),
		)
		
		response = self.client.delete(
			'/api/scheduling/delete/',
			content_type='application/json',
			data={'assignment_id': str(assignment.id)}
		)
		self.assertEqual(response.status_code, 200)
		self.assertFalse(EmployeeAssignment.objects.filter(id=assignment.id).exists())
	
	def test_non_manager_cannot_assign_shifts(self):
		"""Only users with manage_attendance permission can assign shifts."""
		employee_user = User.objects.create_user(username='emp3', password='EmpPass123!')
		emp_membership = OrganizationMembership.objects.create(
			user=employee_user,
			organization=self.organization,
			role=OrganizationMembership.Role.EMPLOYEE
		)
		
		self.client.login(username='emp3', password='EmpPass123!')
		response = self.client.post(
			'/api/scheduling/assign/',
			content_type='application/json',
			data={
				'employee_id': str(self.employee.id),
				'shift_id': str(self.shift_day.id),
				'start_date': '2026-09-01',
			}
		)
		self.assertEqual(response.status_code, 403)
