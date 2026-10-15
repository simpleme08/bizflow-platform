from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from apps.core.models import Notification
from apps.employees.models import Employee, EmployeeDocument
from apps.organization.models import Organization, OrganizationMembership


class DocumentExpiryCommandTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="expiry-user",
            email="expiry@example.com",
            password="test-password",
        )
        self.organization = Organization.objects.create(
            name="Expiry Test Org",
            slug="expiry-test-org",
        )
        OrganizationMembership.objects.create(
            organization=self.organization,
            user=self.user,
            role=OrganizationMembership.Role.EMPLOYEE,
            is_active=True,
        )
        self.employee = Employee.objects.create(
            employee_number="EXP-001",
            user=self.user,
            organization=self.organization,
            first_name="Expiry",
            last_name="Tester",
            status=Employee.Status.REGULAR,
            is_active=True,
        )

    def test_queues_expiring_active_document_once(self):
        document = EmployeeDocument.objects.create(
            employee=self.employee,
            document_type="Passport",
            name="Passport",
            expiry_date=date.today() + timedelta(days=10),
            status="ACTIVE",
        )

        call_command("notify_document_expiry", "--days", "30")
        self.assertEqual(Notification.objects.count(), 1)
        notification = Notification.objects.get()
        self.assertEqual(notification.recipient, self.user)
        self.assertEqual(notification.organization, self.organization)
        self.assertEqual(notification.event, f"DOCUMENT_EXPIRY:{document.pk}")

        call_command("notify_document_expiry", "--days", "30")
        self.assertEqual(Notification.objects.count(), 1)

    def test_dry_run_does_not_create_notification(self):
        EmployeeDocument.objects.create(
            employee=self.employee,
            document_type="License",
            name="License",
            expiry_date=date.today() + timedelta(days=5),
            status="ACTIVE",
        )

        call_command("notify_document_expiry", "--days", "30", "--dry-run")
        self.assertEqual(Notification.objects.count(), 0)

    def test_ignores_expired_and_archived_documents(self):
        EmployeeDocument.objects.create(
            employee=self.employee,
            document_type="Expired",
            name="Expired",
            expiry_date=date.today() - timedelta(days=1),
            status="ACTIVE",
        )
        EmployeeDocument.objects.create(
            employee=self.employee,
            document_type="Archived",
            name="Archived",
            expiry_date=date.today() + timedelta(days=5),
            status="ARCHIVED",
        )

        call_command("notify_document_expiry", "--days", "30")
        self.assertEqual(Notification.objects.count(), 0)
