from django.test import TestCase, Client as TestClient
from django.contrib.auth.models import User
from datetime import date

from apps.organization.models import Organization, OrganizationMembership
from apps.employees.models import Employee, EmployeeAssignment
from apps.workforce.models import ShiftTemplate, Client, ClientSite


class ShiftSchedulingTests(TestCase):
    def setUp(self):
        self.client = TestClient()
        self.organization = Organization.objects.create(slug='test-org', name='Test Organization')
        self.user = User.objects.create_user(username='manager', password='TestPass123!')
        self.membership = OrganizationMembership.objects.create(user=self.user, organization=self.organization, role=OrganizationMembership.Role.MANAGER)
        self.client.login(username='manager', password='TestPass123!')
        self.shift_day = ShiftTemplate.objects.create(name='Day Shift', start_time='08:00', end_time='17:00')
        self.shift_night = ShiftTemplate.objects.create(name='Night Shift', start_time='22:00', end_time='07:00')
        self.client_obj = Client.objects.create(organization=self.organization, code='TEST', name='Test Client')
        self.site = ClientSite.objects.create(client=self.client_obj, name='Test Site')
        self.employee = Employee.objects.create(employee_number='EMP-001', user=User.objects.create_user(username='emp1', password='EmpPass123!'), organization=self.organization, first_name='John', last_name='Doe', is_active=True, status=Employee.Status.REGULAR)

    def test_scheduling_page_requires_login(self):
        self.client.logout()
        response = self.client.get('/scheduling/')
        self.assertEqual(response.status_code, 401)

    def test_get_shifts_returns_global_templates(self):
        response = self.client.get('/api/scheduling/shifts/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['shifts']), 2)
        self.assertEqual(data['shifts'][0]['name'], 'Day Shift')

    def test_get_shifts_does_not_expose_other_organization_templates(self):
        other_org = Organization.objects.create(slug='other-org', name='Other Organization')
        other_shift = ShiftTemplate.objects.create(organization=other_org, name='Other Tenant Shift', start_time='09:00', end_time='18:00')
        response = self.client.get('/api/scheduling/shifts/')
        self.assertEqual(response.status_code, 200)
        shift_ids = {item['id'] for item in response.json()['shifts']}
        self.assertNotIn(str(other_shift.id), shift_ids)


    def test_multi_organization_user_must_use_selected_tenant(self):
        other_org = Organization.objects.create(slug='other-org', name='Other Organization')
        OrganizationMembership.objects.create(user=self.user, organization=other_org, role=OrganizationMembership.Role.SUPER_USER)
        response = self.client.get('/api/scheduling/employees/', HTTP_X_ORGANIZATION_ID=str(other_org.id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['employees'], [])

    def test_get_employees_returns_active_only(self):
        Employee.objects.create(employee_number='EMP-002', user=User.objects.create_user(username='emp2', password='EmpPass123!'), organization=self.organization, first_name='Jane', last_name='Smith', is_active=False, status=Employee.Status.SEPARATED)
        response = self.client.get('/api/scheduling/employees/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['employees']), 1)
        self.assertEqual(data['employees'][0]['name'], 'John Doe')

    def test_assign_shift_creates_assignment(self):
        response = self.client.post('/api/scheduling/assign/', content_type='application/json', data={'employee_id': str(self.employee.id), 'shift_id': str(self.shift_day.id), 'client_id': str(self.client_obj.id), 'site_id': str(self.site.id), 'start_date': '2026-09-01', 'end_date': None, 'is_primary': True})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'created')
        assignment = EmployeeAssignment.objects.filter(employee=self.employee).first()
        self.assertIsNotNone(assignment)
        self.assertEqual(assignment.shift_template, self.shift_day)
        self.assertEqual(assignment.client, self.client_obj)
        self.assertTrue(assignment.is_primary)

    def test_cross_organization_shift_cannot_be_assigned(self):
        other_org = Organization.objects.create(slug='other-org', name='Other Organization')
        other_shift = ShiftTemplate.objects.create(organization=other_org, name='Other Tenant Shift', start_time='09:00', end_time='18:00')
        response = self.client.post('/api/scheduling/assign/', content_type='application/json', data={'employee_id': str(self.employee.id), 'shift_id': str(other_shift.id), 'start_date': '2026-09-01'})
        self.assertEqual(response.status_code, 404)
        self.assertFalse(EmployeeAssignment.objects.filter(employee=self.employee).exists())

    def test_delete_assignment_removes_shift(self):
        assignment = EmployeeAssignment.objects.create(employee=self.employee, shift_template=self.shift_day, client=self.client_obj, start_date=date(2026, 9, 1))
        response = self.client.delete('/api/scheduling/delete/', content_type='application/json', data={'assignment_id': str(assignment.id)})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(EmployeeAssignment.objects.filter(id=assignment.id).exists())

    def test_scheduling_mutations_require_csrf(self):
        csrf_client = TestClient(enforce_csrf_checks=True)
        self.assertTrue(csrf_client.login(username='manager', password='TestPass123!'))
        response = csrf_client.post('/api/scheduling/assign/', content_type='application/json', data={'employee_id': str(self.employee.id), 'shift_id': str(self.shift_day.id), 'start_date': '2026-09-01'})
        self.assertEqual(response.status_code, 403)

    def test_non_manager_cannot_assign_shifts(self):
        employee_user = User.objects.create_user(username='emp3', password='EmpPass123!')
        OrganizationMembership.objects.create(user=employee_user, organization=self.organization, role=OrganizationMembership.Role.EMPLOYEE)
        self.client.login(username='emp3', password='EmpPass123!')
        response = self.client.post('/api/scheduling/assign/', content_type='application/json', data={'employee_id': str(self.employee.id), 'shift_id': str(self.shift_day.id), 'start_date': '2026-09-01'})
        self.assertEqual(response.status_code, 403)

    def test_ineligible_employee_is_not_assignable(self):
        self.employee.status = Employee.Status.SUSPENDED
        self.employee.is_active = False
        self.employee.save(update_fields=('status', 'is_active', 'updated_at'))
        response = self.client.get('/api/scheduling/employees/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['employees'], [])
        response = self.client.post('/api/scheduling/assign/', content_type='application/json', data={'employee_id': str(self.employee.id), 'shift_id': str(self.shift_day.id), 'start_date': '2026-09-01'})
        self.assertEqual(response.status_code, 409)

    def test_cross_organization_assignment_is_rejected(self):
        other_org = Organization.objects.create(slug='other-org', name='Other Organization')
        other_employee = Employee.objects.create(employee_number='OTHER-001', user=User.objects.create_user(username='other', password='EmpPass123!'), organization=other_org, first_name='Other', last_name='Employee', is_active=True, status=Employee.Status.REGULAR)
        response = self.client.post('/api/scheduling/assign/', content_type='application/json', data={'employee_id': str(other_employee.id), 'shift_id': str(self.shift_day.id), 'start_date': '2026-09-01'})
        self.assertEqual(response.status_code, 400)
