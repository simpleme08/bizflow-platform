from django.contrib.auth.models import User
from django.test import TestCase, Client

from apps.employees.models import Employee
from apps.leave.models import EmployeeLeaveBalance, LeaveType, LeaveApplication
from apps.organization.models import Organization, OrganizationMembership


class LeaveLifecycleIntegrationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.organization = Organization.objects.create(slug='leave-org', name='Leave Org')
        self.user = User.objects.create_user(username='employee', password='Pass12345!')
        OrganizationMembership.objects.create(user=self.user, organization=self.organization, role=OrganizationMembership.Role.EMPLOYEE)
        self.employee = Employee.objects.create(employee_number='EMP-LEAVE', user=self.user, organization=self.organization, first_name='Leave', last_name='Employee', status=Employee.Status.REGULAR, is_active=True)
        self.leave_type = LeaveType.objects.create(code='VL', name='Vacation Leave', annual_credits=10)
        EmployeeLeaveBalance.objects.create(employee=self.employee, leave_type=self.leave_type, year=2026, credits=10)
        self.client.login(username='employee', password='Pass12345!')

    def test_suspended_employee_cannot_submit_leave(self):
        self.employee.status = Employee.Status.SUSPENDED
        self.employee.is_active = False
        self.employee.save(update_fields=('status', 'is_active', 'updated_at'))
        response = self.client.post('/api/leave/me/', data={'leave_type_id': str(self.leave_type.id), 'start_date': '2026-09-15', 'end_date': '2026-09-16', 'reason': 'Rest'}, content_type='application/json')
        self.assertEqual(response.status_code, 409)
        self.assertFalse(LeaveApplication.objects.filter(employee=self.employee).exists())

    def test_leave_cannot_start_on_separation_date(self):
        self.employee.separation_date = __import__('datetime').date(2026, 9, 15)
        self.employee.save(update_fields=('separation_date', 'updated_at'))
        response = self.client.post('/api/leave/me/', data={'leave_type_id': str(self.leave_type.id), 'start_date': '2026-09-15', 'end_date': '2026-09-16', 'reason': 'Rest'}, content_type='application/json')
        self.assertEqual(response.status_code, 409)
        self.assertFalse(LeaveApplication.objects.filter(employee=self.employee).exists())

    def test_active_employee_can_submit_leave(self):
        response = self.client.post('/api/leave/me/', data={'leave_type_id': str(self.leave_type.id), 'start_date': '2026-09-15', 'end_date': '2026-09-16', 'reason': 'Rest'}, content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['status'], LeaveApplication.Status.PENDING)
