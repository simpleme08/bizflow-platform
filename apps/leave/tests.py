from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
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

    def test_leave_request_cannot_cross_calendar_years(self):
        response = self.client.post('/api/leave/me/', data={'leave_type_id': str(self.leave_type.id), 'start_date': '2026-12-31', 'end_date': '2027-01-02', 'reason': 'New year'}, content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('cannot cross calendar years', response.json()['detail'])
        self.assertFalse(LeaveApplication.objects.filter(employee=self.employee).exists())

    def test_overlapping_pending_leave_request_is_rejected(self):
        LeaveApplication.objects.create(
            employee=self.employee,
            leave_type=self.leave_type,
            start_date='2026-09-15',
            end_date='2026-09-16',
            total_days=2,
            reason='Existing request',
        )
        response = self.client.post(
            '/api/leave/me/',
            data={'leave_type_id': str(self.leave_type.id), 'start_date': '2026-09-16', 'end_date': '2026-09-17', 'reason': 'Overlap'},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(LeaveApplication.objects.filter(employee=self.employee).count(), 1)

    def test_pending_leave_requests_count_against_available_balance(self):
        LeaveApplication.objects.create(
            employee=self.employee,
            leave_type=self.leave_type,
            start_date='2026-10-01',
            end_date='2026-10-08',
            total_days=8,
            reason='Existing request',
        )
        response = self.client.post(
            '/api/leave/',
            data={'leave_type_id': str(self.leave_type.id), 'start_date': '2026-10-20', 'end_date': '2026-10-22', 'reason': 'Additional leave'},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(LeaveApplication.objects.filter(employee=self.employee).count(), 1)

    def test_overlapping_pending_leave_cannot_be_approved_after_another_is_approved(self):
        first = LeaveApplication.objects.create(
            employee=self.employee,
            leave_type=self.leave_type,
            start_date='2026-09-15',
            end_date='2026-09-17',
            total_days=3,
            reason='First request',
        )
        second = LeaveApplication.objects.create(
            employee=self.employee,
            leave_type=self.leave_type,
            start_date='2026-09-16',
            end_date='2026-09-18',
            total_days=3,
            reason='Overlapping request',
        )
        first.approve(self.user)
        with self.assertRaisesMessage(ValidationError, 'overlaps an already approved'):
            second.approve(self.user)
        second.refresh_from_db()
        self.assertEqual(second.status, LeaveApplication.Status.PENDING)
        balance = EmployeeLeaveBalance.objects.get(employee=self.employee, leave_type=self.leave_type, year=2026)
        self.assertEqual(balance.used, 3)

    def test_approved_leave_cannot_be_approved_twice(self):
        application = LeaveApplication.objects.create(
            employee=self.employee,
            leave_type=self.leave_type,
            start_date='2026-09-15',
            end_date='2026-09-16',
            total_days=2,
            reason='Rest',
        )
        application.approve(self.user)
        with self.assertRaises(ValidationError):
            application.approve(self.user)
        balance = EmployeeLeaveBalance.objects.get(employee=self.employee, leave_type=self.leave_type, year=2026)
        self.assertEqual(balance.used, 2)

class LeaveDecisionAuthorizationTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(slug='leave-scope-org', name='Leave Scope Org')
        self.manager_user = User.objects.create_user(username='manager-scope', password='Pass12345!')
        OrganizationMembership.objects.create(
            user=self.manager_user,
            organization=self.organization,
            role=OrganizationMembership.Role.MANAGER,
        )
        self.manager_employee = Employee.objects.create(
            employee_number='EMP-MANAGER-SCOPE',
            user=self.manager_user,
            organization=self.organization,
            first_name='Mara',
            last_name='Manager',
            status=Employee.Status.REGULAR,
            is_active=True,
        )
        self.leave_type = LeaveType.objects.create(code='VL-SCOPE', name='Vacation Leave Scope', annual_credits=10)

        self.report_user = User.objects.create_user(username='direct-report', password='Pass12345!')
        OrganizationMembership.objects.create(
            user=self.report_user,
            organization=self.organization,
            role=OrganizationMembership.Role.EMPLOYEE,
        )
        self.report = Employee.objects.create(
            employee_number='EMP-DIRECT-REPORT',
            user=self.report_user,
            organization=self.organization,
            manager=self.manager_employee,
            first_name='Dina',
            last_name='Report',
            status=Employee.Status.REGULAR,
            is_active=True,
        )

        self.other_user = User.objects.create_user(username='other-employee', password='Pass12345!')
        OrganizationMembership.objects.create(
            user=self.other_user,
            organization=self.organization,
            role=OrganizationMembership.Role.EMPLOYEE,
        )
        self.other_employee = Employee.objects.create(
            employee_number='EMP-OTHER-EMPLOYEE',
            user=self.other_user,
            organization=self.organization,
            first_name='Omar',
            last_name='Other',
            status=Employee.Status.REGULAR,
            is_active=True,
        )

    def _application(self, employee, suffix):
        EmployeeLeaveBalance.objects.get_or_create(
            employee=employee,
            leave_type=self.leave_type,
            year=2026,
            defaults={'credits': 10},
        )
        return LeaveApplication.objects.create(
            employee=employee,
            leave_type=self.leave_type,
            start_date='2026-12-10',
            end_date='2026-12-11',
            total_days=2,
            reason=f'Authorization test {suffix}',
        )

    def _decide(self, application, decision='approve'):
        self.client.force_login(self.manager_user)
        return self.client.post(
            f'/api/leave/{application.id}/decision/',
            data={'decision': decision},
            content_type='application/json',
        )

    def test_manager_can_approve_direct_report_leave(self):
        application = self._application(self.report, 'direct-report')
        response = self._decide(application, 'approve')

        self.assertEqual(response.status_code, 200)
        application.refresh_from_db()
        self.assertEqual(application.status, LeaveApplication.Status.APPROVED)
        balance = EmployeeLeaveBalance.objects.get(employee=self.report, leave_type=self.leave_type, year=2026)
        self.assertEqual(balance.used, 2)

    def test_manager_cannot_approve_unrelated_employee_leave(self):
        application = self._application(self.other_employee, 'unrelated')
        response = self._decide(application, 'approve')

        self.assertEqual(response.status_code, 403)
        application.refresh_from_db()
        self.assertEqual(application.status, LeaveApplication.Status.PENDING)
        balance = EmployeeLeaveBalance.objects.get(employee=self.other_employee, leave_type=self.leave_type, year=2026)
        self.assertEqual(balance.used, 0)

    def test_manager_cannot_reject_unrelated_employee_leave(self):
        application = self._application(self.other_employee, 'unrelated-rejection')
        response = self._decide(application, 'reject')

        self.assertEqual(response.status_code, 403)
        application.refresh_from_db()
        self.assertEqual(application.status, LeaveApplication.Status.PENDING)

    def test_manager_cannot_approve_own_leave(self):
        application = self._application(self.manager_employee, 'self-approval')
        response = self._decide(application, 'approve')

        self.assertEqual(response.status_code, 403)
        application.refresh_from_db()
        self.assertEqual(application.status, LeaveApplication.Status.PENDING)
