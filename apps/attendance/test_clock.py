from datetime import date, time
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image

from apps.employees.models import Employee, EmployeeAssignment
from apps.organization.models import Organization, OrganizationMembership
from apps.workforce.models import ShiftTemplate


class ClockFlowTests(TestCase):
    def setUp(self):
        organization = Organization.objects.create(name="Clock Test Org", slug="clock-test")
        shift = ShiftTemplate.objects.create(name="Day Shift", start_time=time(8), end_time=time(17))
        user = get_user_model().objects.create_user(username="clock.user", password="ClockTest123!")
        OrganizationMembership.objects.create(
            organization=organization,
            user=user,
            role=OrganizationMembership.Role.EMPLOYEE,
            is_active=True,
        )
        self.employee = Employee.objects.create(
            employee_number="CLOCK-001",
            user=user,
            organization=organization,
            first_name="Clock",
            last_name="User",
            is_active=True,
        )
        EmployeeAssignment.objects.create(
            employee=self.employee,
            shift_template=shift,
            start_date=date(2026, 1, 1),
            is_primary=True,
        )

    def image_upload(self, name="clock-proof.jpg"):
        buffer = BytesIO()
        Image.new("RGB", (64, 64), "white").save(buffer, format="JPEG")
        return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/jpeg")

    def test_clock_in_and_out_save_photo_proof(self):
        login_response = self.client.post("/clock/login/", {
            "username": "clock.user",
            "password": "ClockTest123!",
        })
        self.assertEqual(login_response.status_code, 200)
        self.assertTrue(login_response.json()["can_clock_in"])

        clock_in = self.client.post(
            "/clock/action/",
            {"action": "CLOCK_IN", "photo": self.image_upload()},
        )
        self.assertEqual(clock_in.status_code, 200)
        self.assertTrue(clock_in.json()["can_clock_out"])

        self.employee.refresh_from_db()
        record = self.employee.attendance_records.get(attendance_date=date.today())
        self.assertTrue(record.clock_in_photo.name)
        self.assertIsNotNone(record.time_in)

        clock_out = self.client.post(
            "/clock/action/",
            {"action": "CLOCK_OUT", "photo": self.image_upload("clock-out-proof.jpg")},
        )
        self.assertEqual(clock_out.status_code, 200)

        record.refresh_from_db()
        self.assertTrue(record.clock_out_photo.name)
        self.assertIsNotNone(record.time_out)
