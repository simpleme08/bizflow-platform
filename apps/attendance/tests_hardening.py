from datetime import date, time
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.utils import timezone
from PIL import Image

from apps.employees.models import Employee, EmployeeAssignment
from apps.organization.models import Organization, OrganizationMembership
from apps.workforce.models import ShiftTemplate

from .models import AttendanceRecord


def image_upload(name='clock.jpg'):
    buffer = BytesIO()
    Image.new('RGB', (16, 16), 'white').save(buffer, format='JPEG')
    return SimpleUploadedFile(name, buffer.getvalue(), content_type='image/jpeg')


class FlexibleClockingTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='cover-user', password='password')
        self.organization = Organization.objects.create(name='Cover Corp', slug='cover-corp')
        OrganizationMembership.objects.create(organization=self.organization, user=self.user, role=OrganizationMembership.Role.EMPLOYEE)
        self.employee = Employee.objects.create(
            employee_number='COVER-001', user=self.user, organization=self.organization,
            first_name='Cover', last_name='Agent'
        )
        self.normal_shift = ShiftTemplate.objects.create(name='Normal Shift', start_time=time(8), end_time=time(17))
        self.cover_shift = ShiftTemplate.objects.create(name='Cover Night', start_time=time(22), end_time=time(6))
        self.assignment = EmployeeAssignment.objects.create(
            employee=self.employee, shift_template=self.normal_shift, start_date=date(2026, 1, 1), is_primary=True
        )
        self.client.login(username='cover-user', password='password')

    def test_assigned_employee_can_clock_in_as_cover_without_changing_assignment(self):
        response = self.client.post('/clock/action/', {
            'action': 'CLOCK_IN',
            'clock_in_mode': 'COVER',
            'shift_id': str(self.cover_shift.id),
            'photo': image_upload(),
        })
        self.assertEqual(response.status_code, 200)
        record = AttendanceRecord.objects.get(employee=self.employee, attendance_date=timezone.localdate())
        self.assertEqual(record.clock_in_mode, AttendanceRecord.ClockInMode.COVER)
        self.assertEqual(record.clock_shift_id, self.cover_shift.id)
        self.assertEqual(record.assignment_id, self.assignment.id)
        self.assertEqual(record.effective_shift.id, self.cover_shift.id)
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.shift_template_id, self.normal_shift.id)

    def test_cover_clock_in_requires_a_selected_shift(self):
        response = self.client.post('/clock/action/', {
            'action': 'CLOCK_IN',
            'clock_in_mode': 'COVER',
            'photo': image_upload(),
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn('valid shift', response.json()['detail'])


class SchedulingSecurityTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='scheduler', password='password')
        self.organization = Organization.objects.create(name='Schedule Corp', slug='schedule-corp')
        OrganizationMembership.objects.create(organization=self.organization, user=self.user, role=OrganizationMembership.Role.HR)
        self.client = Client(enforce_csrf_checks=True)
        self.client.login(username='scheduler', password='password')

    def test_shift_assignment_mutation_requires_csrf(self):
        response = self.client.post('/api/scheduling/assign/', data='{}', content_type='application/json')
        self.assertEqual(response.status_code, 403)
