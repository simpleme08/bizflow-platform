from datetime import date, datetime, time, timedelta
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone

from PIL import Image

from apps.attendance.models import AttendanceRecord
from apps.attendance.services import AttendanceCalculator
from apps.employees.models import Employee, EmployeeAssignment
from apps.organization.models import Organization, OrganizationMembership
from apps.workforce.models import ShiftTemplate


class AttendanceCalculatorTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(username='juan', password='clock-password')
        organization = Organization.objects.create(name='Acme Corporation', slug='acme')
        OrganizationMembership.objects.create(organization=organization, user=user, role=OrganizationMembership.Role.EMPLOYEE, is_active=True)
        employee = Employee.objects.create(employee_number='EMP-000001', user=user, organization=organization, first_name='Juan', last_name='Cruz')
        shift = ShiftTemplate.objects.create(name='Day Shift', start_time=time(8), end_time=time(17))
        self.assignment = EmployeeAssignment.objects.create(employee=employee, shift_template=shift, start_date=date(2026, 1, 1), is_primary=True)
        self.client.login(username='juan', password='clock-password')

    def photo(self, name='clock-proof.jpg'):
        image = Image.new('RGB', (20, 20), 'white')
        buffer = BytesIO()
        image.save(buffer, format='JPEG')
        return SimpleUploadedFile(name, buffer.getvalue(), content_type='image/jpeg')

    def record(self, time_in, time_out):
        return AttendanceRecord(employee=self.assignment.employee, assignment=self.assignment, attendance_date=date(2026, 8, 10), time_in=timezone.make_aware(datetime.combine(date(2026, 8, 10), time_in)), time_out=timezone.make_aware(datetime.combine(date(2026, 8, 10), time_out)))

    def test_exact_start_has_no_late_or_adjustment(self):
        self.assertEqual(AttendanceCalculator.calculate(self.record(time(8), time(17))), {'late_minutes': 0, 'undertime_minutes': 0, 'overtime_minutes': 0})

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
        with self.assertRaises(ValidationError):
            self.record(time(9), time(8, 59)).full_clean()

    def test_wrong_local_time_in_date_is_rejected(self):
        record = self.record(time(8), time(17))
        record.time_in = timezone.make_aware(datetime.combine(date(2026, 8, 11), time(8)))
        with self.assertRaises(ValidationError):
            record.full_clean()

    def test_overnight_shift_uses_next_day_end(self):
        shift = ShiftTemplate.objects.create(name='Night Shift', start_time=time(22), end_time=time(7))
        assignment = EmployeeAssignment.objects.create(employee=self.assignment.employee, shift_template=shift, start_date=date(2026, 1, 1))
        record = AttendanceRecord(employee=assignment.employee, assignment=assignment, attendance_date=date(2026, 8, 10), time_in=timezone.make_aware(datetime(2026, 8, 10, 22)), time_out=timezone.make_aware(datetime(2026, 8, 11, 7, 30)))
        self.assertEqual(AttendanceCalculator.calculate(record)['overtime_minutes'], 30)

    def test_clock_login_remembers_last_action_and_closes_record(self):
        login_response = self.client.post('/clock/login/', {'username': 'juan', 'password': 'clock-password'})
        self.assertEqual(login_response.status_code, 200)
        self.assertEqual(login_response.json()['last_action'], 'NOT_STARTED')
        clock_in_response = self.client.post('/clock/action/', {'action': 'CLOCK_IN', 'photo': self.photo()})
        self.assertEqual(clock_in_response.status_code, 200)
        self.assertEqual(clock_in_response.json()['last_action'], 'CLOCKED_IN')
        record = AttendanceRecord.objects.get(employee=self.assignment.employee, attendance_date=timezone.localdate())
        self.assertIsNotNone(record.time_in)
        self.assertTrue(record.clock_in_photo)
        clock_out_response = self.client.post('/clock/action/', {'action': 'CLOCK_OUT', 'photo': self.photo('clock-out-proof.jpg')})
        self.assertEqual(clock_out_response.status_code, 200)
        record.refresh_from_db()
        self.assertIsNotNone(record.time_out)
        self.assertTrue(record.clock_out_photo)
        self.assertGreaterEqual(record.hours_worked.total_seconds(), 0)
        self.assertEqual(AttendanceRecord.objects.filter(employee=self.assignment.employee).count(), 1)

    def test_clocking_requires_photo(self):
        response = self.client.post('/clock/action/', {'action': 'CLOCK_IN'})
        self.assertEqual(response.status_code, 400)
        self.assertIn('camera photo is required', response.json()['detail'].lower())

    def test_stale_open_record_does_not_disable_todays_clock_in(self):
        yesterday = timezone.localdate() - timedelta(days=1)
        AttendanceRecord.objects.create(
            employee=self.assignment.employee,
            assignment=self.assignment,
            attendance_date=yesterday,
            time_in=timezone.make_aware(datetime.combine(yesterday, time(8))),
            status=AttendanceRecord.Status.PRESENT,
        )
        response = self.client.get('/clock/action/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['can_clock_in'])
        self.assertFalse(response.json()['can_clock_out'])
        clock_in_response = self.client.post('/clock/action/', {'action': 'CLOCK_IN', 'photo': self.photo()})
        self.assertEqual(clock_in_response.status_code, 200)
        self.assertEqual(clock_in_response.json()['last_action'], 'CLOCKED_IN')

    def test_clock_in_requires_employee_assignment(self):
        self.assignment.end_date = timezone.localdate() - timedelta(days=1)
        self.assignment.save(update_fields=['end_date', 'updated_at'])
        response = self.client.post('/clock/action/', {'action': 'CLOCK_IN', 'photo': self.photo()})
        self.assertEqual(response.status_code, 400)

    def test_employee_cannot_write_management_attendance_api(self):
        response = self.client.post('/api/attendance/', data={}, content_type='application/json')
        self.assertEqual(response.status_code, 403)

    def test_suspended_employee_cannot_clock_in(self):
        employee = self.assignment.employee
        employee.status = Employee.Status.SUSPENDED
        employee.is_active = False
        employee.save(update_fields=('status', 'is_active', 'updated_at'))
        response = self.client.post('/clock/login/', {'username': 'juan', 'password': 'clock-password'})
        self.assertEqual(response.status_code, 403)


class DashboardViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='manager', password='test-password')
        organization = Organization.objects.create(name='Acme Corporation', slug='acme')
        OrganizationMembership.objects.create(organization=organization, user=self.user, role=OrganizationMembership.Role.MANAGER)
        employee_user = get_user_model().objects.create_user(username='juan')
        employee = Employee.objects.create(employee_number='EMP-000001', user=employee_user, organization=organization, first_name='Juan', last_name='Cruz')
        shift = ShiftTemplate.objects.create(name='Day Shift', start_time=time(8), end_time=time(17))
        self.assignment = EmployeeAssignment.objects.create(employee=employee, shift_template=shift, start_date=date(2026, 1, 1), is_primary=True)

    def test_dashboard_requires_login(self):
        response = self.client.get('/api/dashboard/')
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {'detail': 'Authentication credentials were not provided.'})

    def test_login_redirects_to_browser_dashboard(self):
        response = self.client.post('/login/', {'username': 'manager', 'password': 'test-password'})
        self.assertRedirects(response, '/workspace/')

    def test_dashboard_returns_today_summary(self):
        today = timezone.localdate()
        AttendanceRecord.objects.create(employee=self.assignment.employee, assignment=self.assignment, attendance_date=today, status=AttendanceRecord.Status.PRESENT, late_minutes=12)
        self.client.force_login(self.user)
        response = self.client.get('/api/dashboard/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['role'], 'MANAGER')
        self.assertFalse(data['is_maintenance_user'])
        self.assertEqual([section['key'] for section in data['sections']], ['employee_directory', 'attendance', 'scheduling', 'leave'])
        self.assertEqual({key: value for key, value in data.items() if key not in ('role', 'role_label', 'is_maintenance_user', 'sections')}, {'date': today.isoformat(), 'active_employee_count': 1, 'today_attendance_count': 1, 'today_present_count': 1, 'today_absent_count': 0, 'records': [{'employee_number': 'EMP-000001', 'employee_name': 'Juan Cruz', 'status': 'PRESENT', 'late_minutes': 12, 'undertime_minutes': 0, 'overtime_minutes': 0}]})

    def test_dashboard_excludes_other_organizations(self):
        other_user = get_user_model().objects.create_user(username='other')
        other_org = Organization.objects.create(name='Other Corp', slug='other-corp')
        OrganizationMembership.objects.create(organization=other_org, user=other_user, role=OrganizationMembership.Role.MANAGER)
        other_employee = Employee.objects.create(employee_number='OTHER-0001', user=other_user, organization=other_org, first_name='Other', last_name='Employee')
        AttendanceRecord.objects.create(employee=other_employee, attendance_date=timezone.localdate(), status=AttendanceRecord.Status.PRESENT)
        self.client.force_login(self.user)
        response = self.client.get('/api/dashboard/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['active_employee_count'], 1)
        self.assertEqual(data['today_attendance_count'], 1)
