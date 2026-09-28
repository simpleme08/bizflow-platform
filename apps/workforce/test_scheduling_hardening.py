from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase, Client

from apps.attendance.models import AttendanceRecord
from apps.employees.models import Employee
from apps.organization.models import Organization, OrganizationMembership
from apps.workforce.models import CoverShift, ScheduleException, ScheduleRule, ShiftTemplate
from apps.workforce.scheduling import resolve_schedule


class WorkforceSchedulingHardeningTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(slug='sched-hardening', name='Scheduling Hardening')
        self.manager = User.objects.create_user(username='sched-manager', password='TestPass123!')
        OrganizationMembership.objects.create(user=self.manager, organization=self.org, role=OrganizationMembership.Role.MANAGER)
        self.client = Client()
        self.client.login(username='sched-manager', password='TestPass123!')
        self.employee = Employee.objects.create(
            employee_number='SCH-001',
            user=User.objects.create_user(username='sched-employee', password='TestPass123!'),
            organization=self.org,
            first_name='Schedule',
            last_name='Employee',
            status=Employee.Status.REGULAR,
            is_active=True,
        )
        self.day = ShiftTemplate.objects.create(organization=self.org, name='Hardening Day', start_time='08:00', end_time='17:00')
        self.night = ShiftTemplate.objects.create(organization=self.org, name='Hardening Night', start_time='22:00', end_time='07:00')

    def test_weekly_rule_resolves_by_date(self):
        ScheduleRule.objects.create(
            employee=self.employee, shift_template=self.day,
            effective_from=date(2026, 9, 1), weekdays=[0, 1, 2, 3, 4], rest_days=[5, 6],
        )
        self.assertEqual(resolve_schedule(self.employee, date(2026, 9, 21))['shift'], self.day)
        self.assertEqual(resolve_schedule(self.employee, date(2026, 9, 20))['kind'], 'REST')

    def test_approved_exception_overrides_recurring_rule(self):
        ScheduleRule.objects.create(employee=self.employee, shift_template=self.day, effective_from=date(2026, 9, 1), weekdays=[0,1,2,3,4])
        ScheduleException.objects.create(employee=self.employee, work_date=date(2026, 9, 21), shift_template=self.night, reason='Approved rotation', approved=True, approved_by=self.manager)
        self.assertEqual(resolve_schedule(self.employee, date(2026, 9, 21))['shift'], self.night)

    def test_cover_shift_requires_second_person_approval_and_overrides_schedule(self):
        ScheduleRule.objects.create(employee=self.employee, shift_template=self.day, effective_from=date(2026, 9, 1), weekdays=[0,1,2,3,4])
        response = self.client.post('/api/scheduling/cover-shifts/', content_type='application/json', data={'employee_id': str(self.employee.id), 'shift_id': str(self.night.id), 'work_date': '2026-09-21', 'reason': 'Coverage'})
        self.assertEqual(response.status_code, 200)
        cover = CoverShift.objects.get(id=response.json()['id'])
        self.assertEqual(resolve_schedule(self.employee, date(2026, 9, 21))['shift'], self.day)
        self.assertEqual(self.client.post(f'/api/scheduling/cover-shifts/{cover.id}/decision/', content_type='application/json', data={'approved': True}).status_code, 409)
        approver = User.objects.create_user(username='second-manager', password='TestPass123!')
        OrganizationMembership.objects.create(user=approver, organization=self.org, role=OrganizationMembership.Role.MANAGER)
        self.client.login(username='second-manager', password='TestPass123!')
        response = self.client.post(f'/api/scheduling/cover-shifts/{cover.id}/decision/', content_type='application/json', data={'approved': True})
        self.assertEqual(response.status_code, 200)
        resolved = resolve_schedule(self.employee, date(2026, 9, 21))
        self.assertEqual(resolved['kind'], 'COVER')
        self.assertEqual(resolved['shift'], self.night)

    def test_split_attendance_segments_are_unique_per_segment(self):
        first = AttendanceRecord.objects.create(employee=self.employee, attendance_date=date(2026, 9, 21), segment_number=1, time_in=None, time_out=None, status=AttendanceRecord.Status.PRESENT)
        second = AttendanceRecord.objects.create(employee=self.employee, attendance_date=date(2026, 9, 21), segment_number=2, time_in=None, time_out=None, status=AttendanceRecord.Status.PRESENT)
        self.assertNotEqual(first.id, second.id)
