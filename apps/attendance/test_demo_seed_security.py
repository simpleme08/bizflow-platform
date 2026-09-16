from django.core import management
from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings


class DemoAttendanceSeedSecurityTests(SimpleTestCase):
    @override_settings(ENVIRONMENT='production')
    def test_demo_attendance_seed_is_blocked_in_production(self):
        with self.assertRaises(CommandError):
            management.call_command('seed_demo_attendance')
