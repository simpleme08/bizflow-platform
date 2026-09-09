from datetime import date, datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from apps.attendance.models import AttendanceRecord
from apps.attendance.services import AttendanceCalculator
from apps.employees.models import Employee, EmployeeAssignment
from apps.organization.models import Organization, OrganizationMembership
from apps.workforce.models import ShiftTemplate


class AttendanceCalculatorTests(TestCase):
	def setUp(self):
		user = get_user_model().objects.create_user(username='juan', password='clock-password')
		organization = Organization.objects.create(name='Acme Corporation', slug='acme')
		employee = Employee.objects.create(
			employee_number='EMP-000001',
			user=user,
			organization=organization,
			first_name='Juan',
			last_name='Cruz',
		)
		shift = ShiftTemplate.objects.create(
			name='Day Shift',
			start_time=time(8),
			end_time=time(17),
		)
		self.assignment = EmployeeAssignment.objects.create(
			employee=employee,
			shift_template=shift,
			start_date=date(2026, 1, 1),
			is_primary=True,
		)

	def record(self, time_in, time_out):
		return AttendanceRecord(
			employee=self.assignment.employee,
			assignment=self.assignment,
			attendance_date=date(2026, 8, 10),
			time_in=timezone.make_aware(datetime.combine(date(2026, 8, 10), time_in)),
			time_out=timezone.make_aware(datetime.combine(date(2026, 8, 10), time_out)),
		)

	def test_exact_start_has_no_late_or_adjustment(self):
		metrics = AttendanceCalculator.calculate(self.record(time(8), time(17)))
		self.assertEqual(metrics, {'late_minutes': 0, 'undertime_minutes': 0, 'overtime_minutes': 0})

	def test_late_and_undertime_are_independent(self):
		metrics = AttendanceCalculator.calculate(self.record(time(8, 20), time(16, 30)))
		self.assertEqual(metrics['late_minutes'], 20)
		self.assertEqual(metrics['undertime_minutes'], 30)
		self.assertEqual(metrics['overtime_minutes'], 0)

	def test_late_and_overtime_are_independent(self):
		metrics = AttendanceCalculator.calculate(self.record(time(8, 20), time(18)))
		self.assertEqual(metrics['late_minutes'], 20)
		self.assertEqual(metrics['undertime_minutes'], 0)
		self.assertEqual(metrics['overtime_minutes'], 60)

	def test_invalid_time_order_is_rejected(self):
		record = self.record(time(9), time(8, 59))

		with self.assertRaises(ValidationError):
			record.full_clean()

	def test_wrong_local_time_in_date_is_rejected(self):
		record = self.record(time(8), time(17))
		record.time_in = timezone.make_aware(datetime.combine(date(2026, 8, 11), time(8)))

		with self.assertRaises(ValidationError):
			record.full_clean()

	def test_overnight_shift_uses_next_day_end(self):
		shift = ShiftTemplate.objects.create(name='Night Shift', start_time=time(22), end_time=time(7))
		assignment = EmployeeAssignment.objects.create(
			employee=self.assignment.employee,
			shift_template=shift,
			start_date=date(2026, 1, 1),
		)
		record = AttendanceRecord(
			employee=assignment.employee,
			assignment=assignment,
			attendance_date=date(2026, 8, 10),
			time_in=timezone.make_aware(datetime(2026, 8, 10, 22)),
			time_out=timezone.make_aware(datetime(2026, 8, 11, 7, 30)),
		)
		self.assertEqual(AttendanceCalculator.calculate(record)['overtime_minutes'], 30)

	def test_clock_login_remembers_last_action_and_closes_record(self):
		login_response = self.client.post('/clock/login/', {'username': 'juan', 'password': 'clock-password'})

		self.assertEqual(login_response.status_code, 200)
		self.assertEqual(login_response.json()['last_action'], 'NOT_STARTED')

		clock_in_response = self.client.post('/clock/action/', {'action': 'CLOCK_IN'})
		self.assertEqual(clock_in_response.status_code, 200)
		self.assertEqual(clock_in_response.json()['last_action'], 'CLOCKED_IN')
		record = AttendanceRecord.objects.get(employee=self.assignment.employee, attendance_date=timezone.localdate())
		self.assertIsNotNone(record.time_in)

		clock_out_response = self.client.post('/clock/action/', {'action': 'CLOCK_OUT'})
		self.assertEqual(clock_out_response.status_code, 200)
		self.assertEqual(clock_out_response.json()['last_action'], 'CLOCKED_OUT')
		record.refresh_from_db()
		self.assertIsNotNone(record.time_out)
		self.assertGreaterEqual(record.hours_worked.total_seconds(), 0)
		self.assertEqual(AttendanceRecord.objects.filter(employee=self.assignment.employee).count(), 1)

	def test_clock_in_requires_employee_assignment(self):
		self.assignment.end_date = timezone.localdate() - timedelta(days=1)
		self.assignment.save(update_fields=['end_date', 'updated_at'])
		self.client.post('/clock/login/', {'username': 'juan', 'password': 'clock-password'})

		response = self.client.post('/clock/action/', {'action': 'CLOCK_IN'})

		self.assertEqual(response.status_code, 400)

	def test_employee_cannot_write_management_attendance_api(self):
		OrganizationMembership.objects.create(
			organization=self.assignment.employee.organization,
			user=self.assignment.employee.user,
			role=OrganizationMembership.Role.EMPLOYEE,
		)
		self.client.login(username='juan', password='clock-password')

		response = self.client.post('/api/attendance/', data={}, content_type='application/json')

		self.assertEqual(response.status_code, 403)


class DashboardViewTests(TestCase):
	def setUp(self):
		self.user = get_user_model().objects.create_user(username='manager', password='test-password')
		organization = Organization.objects.create(name='Acme Corporation', slug='acme')
		OrganizationMembership.objects.create(
			organization=organization,
			user=self.user,
			role=OrganizationMembership.Role.MANAGER,
		)
		employee_user = get_user_model().objects.create_user(username='juan')
		employee = Employee.objects.create(
			employee_number='EMP-000001',
			user=employee_user,
			organization=organization,
			first_name='Juan',
			last_name='Cruz',
		)
		shift = ShiftTemplate.objects.create(name='Day Shift', start_time=time(8), end_time=time(17))
		self.assignment = EmployeeAssignment.objects.create(
			employee=employee,
			shift_template=shift,
			start_date=date(2026, 1, 1),
			is_primary=True,
		)

	def test_dashboard_requires_login(self):
		response = self.client.get('/api/dashboard/')

		self.assertEqual(response.status_code, 401)
		self.assertEqual(response.json(), {'detail': 'Authentication credentials were not provided.'})

	def test_login_redirects_to_browser_dashboard(self):
		response = self.client.post('/login/', {
			'username': 'manager',
			'password': 'test-password',
		})

		self.assertRedirects(response, '/workspace/')

	def test_dashboard_returns_today_summary(self):
		today = timezone.localdate()
		AttendanceRecord.objects.create(
			employee=self.assignment.employee,
			assignment=self.assignment,
			attendance_date=today,
			status=AttendanceRecord.Status.PRESENT,
			late_minutes=12,
		)
		self.client.login(username='manager', password='test-password')

		response = self.client.get('/api/dashboard/')

		self.assertEqual(response.status_code, 200)
		data = response.json()
		self.assertEqual(data['role'], 'MANAGER')
		self.assertFalse(data['is_maintenance_user'])
		self.assertEqual([section['key'] for section in data['sections']], ['employee_directory', 'attendance', 'scheduling', 'leave'])
		self.assertEqual({key: value for key, value in data.items() if key not in ('role', 'role_label', 'is_maintenance_user', 'sections')}, {
			'date': today.isoformat(),
			'active_employee_count': 1,
			'today_attendance_count': 1,
			'today_present_count': 1,
			'today_absent_count': 0,
			'records': [{
				'employee_number': 'EMP-000001',
				'employee_name': 'Juan Cruz',
				'status': 'PRESENT',
				'late_minutes': 12,
				'undertime_minutes': 0,
				'overtime_minutes': 0,
			}],
		})

	def test_dashboard_excludes_other_organizations(self):
		other_user = get_user_model().objects.create_user(username='other')
		other_organization = Organization.objects.create(name='Other Corporation', slug='other')
		other_employee = Employee.objects.create(
			employee_number='EMP-000002',
			user=other_user,
			organization=other_organization,
			first_name='Other',
			last_name='Employee',
		)
		other_shift = ShiftTemplate.objects.create(name='Other Shift', start_time=time(8), end_time=time(17))
		other_assignment = EmployeeAssignment.objects.create(
			employee=other_employee,
			shift_template=other_shift,
			start_date=date(2026, 1, 1),
		)
		AttendanceRecord.objects.create(
			employee=other_employee,
			assignment=other_assignment,
			attendance_date=timezone.localdate(),
		)
		self.client.login(username='manager', password='test-password')

		response = self.client.get('/api/dashboard/')

		self.assertEqual(response.json()['active_employee_count'], 1)
		self.assertEqual(response.json()['today_attendance_count'], 0)

	def test_super_user_dashboard_has_maintenance_access(self):
		OrganizationMembership.objects.filter(
			organization=Organization.objects.get(slug='acme'),
			user=self.user,
		).update(role=OrganizationMembership.Role.SUPER_USER)
		self.user.is_superuser = True
		self.user.save(update_fields=['is_superuser'])
		self.client.login(username='manager', password='test-password')

		response = self.client.get('/api/dashboard/')

		self.assertTrue(response.json()['is_maintenance_user'])

	def test_employee_dashboard_exposes_self_service_only(self):
		self.user.organization_memberships.update(role=OrganizationMembership.Role.EMPLOYEE)
		self.client.login(username='manager', password='test-password')

		response = self.client.get('/api/dashboard/')

		self.assertEqual([section['key'] for section in response.json()['sections']], ['ess'])

	def test_record_attendance_calculates_metrics(self):
		self.client.login(username='manager', password='test-password')
		response = self.client.post('/api/attendance/', data={
			'employee_id': str(self.assignment.employee_id),
			'attendance_date': '2026-08-10',
			'time_in': '2026-08-10T08:20:00+08:00',
			'time_out': '2026-08-10T18:00:00+08:00',
		}, content_type='application/json')

		self.assertEqual(response.status_code, 201)
		self.assertEqual(response.json()['late_minutes'], 20)
		self.assertEqual(response.json()['overtime_minutes'], 60)
