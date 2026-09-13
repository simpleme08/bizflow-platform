from datetime import date, datetime, time
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


class FlexibleClockingTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='cover-agent', password='clock-password')
        self.organization = Organization.objects.create(name='Cover Operations', slug='cover-operations')
        OrganizationMembership.objects.create(organization=self.organization, user=self.user, role=OrganizationMembership.Role.EMPLOYEE, is_active=True)
        self.employee = Employee.objects.create(employee_number='COVER-0001', user=self.user, organization=self.organization, first_name='Cover', last_name='Agent', is_active=True)
        self.shift = ShiftTemplate.objects.create(name='Night Cover', start_time=time(22), end_time=time(7))
        self.client.login(username='cover-agent', password='clock-password')

    def photo(self, name='clock-proof.jpg'):
        image = Image.new('RGB', (20, 20), 'white')
        buffer = BytesIO(); image.save(buffer, format='JPEG')
        return SimpleUploadedFile(name, buffer.getvalue(), content_type='image/jpeg')

    def test_employee_can_clock_in_without_preassigned_shift(self):
        response = self.client.post('/clock/action/', {'action': 'CLOCK_IN', 'photo': self.photo()})
        self.assertEqual(response.status_code, 200)
        record = AttendanceRecord.objects.get(employee=self.employee, attendance_date=timezone.localdate())
        self.assertIsNone(record.assignment_id)
        self.assertEqual(record.clock_in_mode, AttendanceRecord.ClockInMode.COVER)
        self.assertIn('schedule reconciliation', record.remarks.lower())

    def test_unassigned_clock_in_can_clock_out(self):
        self.client.post('/clock/action/', {'action': 'CLOCK_IN', 'photo': self.photo()})
        response = self.client.post('/clock/action/', {'action': 'CLOCK_OUT', 'photo': self.photo('out.jpg')})
        self.assertEqual(response.status_code, 200)
        record = AttendanceRecord.objects.get(employee=self.employee, attendance_date=timezone.localdate())
        self.assertIsNotNone(record.time_out)
        self.assertTrue(record.clock_out_photo)

    def test_cover_punch_can_use_clock_shift_for_metrics(self):
        record = AttendanceRecord(
            employee=self.employee,
            clock_shift=self.shift,
            clock_in_mode=AttendanceRecord.ClockInMode.COVER,
            attendance_date=date(2026, 8, 10),
            time_in=timezone.make_aware(datetime(2026, 8, 10, 22, 10)),
            time_out=timezone.make_aware(datetime(2026, 8, 11, 7, 30)),
        )
        record.full_clean()
        metrics = AttendanceCalculator.calculate(record)
        self.assertEqual(metrics['late_minutes'], 10)
        self.assertEqual(metrics['overtime_minutes'], 30)

    def test_scheduled_mode_still_requires_assignment(self):
        record = AttendanceRecord(employee=self.employee, attendance_date=date(2026, 8, 10), clock_in_mode=AttendanceRecord.ClockInMode.SCHEDULED)
        with self.assertRaises(ValidationError):
            record.full_clean()

    def test_clock_state_allows_punch_without_assignment(self):
        response = self.client.get('/clock/action/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['can_clock_in'])
        self.assertFalse(data['assignment_available'])
        self.assertIn('cover', data['clocking_note'].lower())
