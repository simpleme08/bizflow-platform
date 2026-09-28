from datetime import timedelta

from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.core.models import AuditEvent
from apps.employees.models import Employee, EmployeeDocument
from apps.organization.models import Organization, OrganizationMembership


class RetentionCommandTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username='retention-admin', password='safe-password')
        self.org = Organization.objects.create(
            name='Retention Org',
            slug='retention-org',
            audit_retention_days=1,
            document_retention_days=1,
        )
        OrganizationMembership.objects.create(user=self.user, organization=self.org, role='HR', is_active=True)
        self.employee = Employee.objects.create(
            organization=self.org,
            user=self.user,
            employee_number='RET-001',
            first_name='Retention',
            last_name='Test',
            status=Employee.Status.REGULAR,
            is_active=True,
        )

    def test_archived_documents_and_old_audits_are_purged(self):
        old = timezone.now() - timedelta(days=3)
        event = AuditEvent.objects.create(
            organization=self.org, actor=self.user, action='old.event',
            entity_type='Employee', entity_id='1', details={},
        )
        AuditEvent.objects.filter(pk=event.pk).update(created_at=old)
        document = EmployeeDocument.objects.create(
            employee=self.employee,
            document_type='ID',
            name='Old ID',
            status='ARCHIVED',
            expiry_date=timezone.localdate() - timedelta(days=3),
        )
        call_command('apply_retention_policy')
        self.assertFalse(AuditEvent.objects.filter(pk=event.pk).exists())
        self.assertFalse(EmployeeDocument.objects.filter(pk=document.pk).exists())
