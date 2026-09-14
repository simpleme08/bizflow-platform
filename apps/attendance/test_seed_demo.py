from datetime import date

from django.core.management import call_command
from django.test import TestCase

from apps.attendance.models import AttendanceRecord
from apps.employees.models import Employee
from apps.organization.models import Organization
from apps.payroll.models import PayrollPeriod, PayrollRecord


class DemoAttendanceSeedCommandTests(TestCase):
    def test_seed_creates_safe_demo_dataset(self):
        call_command('seed_demo_attendance')

        organization = Organization.objects.get(slug='bizflow-demo')
        self.assertEqual(Employee.objects.filter(organization=organization).count(), 6)
        self.assertEqual(
            AttendanceRecord.objects.filter(
                employee__organization=organization,
                attendance_date__range=(date(2026, 8, 16), date(2026, 8, 31)),
            ).count(),
            37,
        )

        period = PayrollPeriod.objects.get(
            organization=organization,
            start_date=date(2026, 8, 16),
            end_date=date(2026, 8, 31),
        )
        self.assertEqual(PayrollRecord.objects.filter(payroll_period=period).count(), 6)
        self.assertEqual(PayrollRecord.objects.filter(payroll_period=period, status=PayrollRecord.Status.DRAFT).count(), 6)
        self.assertFalse(PayrollRecord.objects.filter(payroll_period=period, approved=True).exists())
        self.assertFalse(PayrollRecord.objects.filter(payroll_period=period, is_paid=True).exists())

    def test_seed_is_idempotent_and_reset_rebuilds(self):
        call_command('seed_demo_attendance')
        first_count = AttendanceRecord.objects.filter(
            employee__organization__slug='bizflow-demo',
            attendance_date__range=(date(2026, 8, 16), date(2026, 8, 31)),
        ).count()

        call_command('seed_demo_attendance')
        self.assertEqual(
            AttendanceRecord.objects.filter(
                employee__organization__slug='bizflow-demo',
                attendance_date__range=(date(2026, 8, 16), date(2026, 8, 31)),
            ).count(),
            first_count,
        )

        call_command('seed_demo_attendance', '--reset')
        self.assertEqual(
            AttendanceRecord.objects.filter(
                employee__organization__slug='bizflow-demo',
                attendance_date__range=(date(2026, 8, 16), date(2026, 8, 31)),
            ).count(),
            first_count,
        )
