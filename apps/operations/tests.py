from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from apps.employees.models import Employee
from apps.talent.models import OffboardingRecord
from apps.organization.models import Organization, OrganizationMembership

from .models import ApprovalRequest, CompensationChange, DocumentAcknowledgement, EmployeeDocument, OffboardingTask, Project, TimesheetEntry


class PrivatePolicyDocumentTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.hr_user = User.objects.create_user(username='policy-hr', password='password')
        self.employee_user = User.objects.create_user(username='policy-employee', password='password')
        self.other_user = User.objects.create_user(username='policy-other', password='password')
        self.organization = Organization.objects.create(name='Policy Org', slug='policy-org')
        self.other_organization = Organization.objects.create(name='Other Policy Org', slug='other-policy-org')
        OrganizationMembership.objects.create(organization=self.organization, user=self.hr_user, role='HR')
        OrganizationMembership.objects.create(organization=self.organization, user=self.employee_user, role='EMPLOYEE')
        OrganizationMembership.objects.create(organization=self.other_organization, user=self.other_user, role='EMPLOYEE')
        self.employee = Employee.objects.create(
            employee_number='POL-001',
            user=self.employee_user,
            organization=self.organization,
            first_name='Policy',
            last_name='Employee',
        )
        self.other_employee = Employee.objects.create(
            employee_number='POL-002',
            user=self.other_user,
            organization=self.other_organization,
            first_name='Other',
            last_name='Employee',
        )
        self.document = EmployeeDocument.objects.create(
            organization=self.organization,
            title='Employee Handbook',
            category='Policy',
            body='Company policies',
            status=EmployeeDocument.Status.PUBLISHED,
        )
        self.document.file.save(
            'handbook.pdf',
            SimpleUploadedFile('handbook.pdf', b'%PDF-1.7 private policy content'),
            save=True,
        )
        self.addCleanup(self.document.file.delete)

    def file_url(self, document=None):
        document = document or self.document
        return f'/api/employee-documents/{document.id}/file/'

    def test_active_employee_can_download_published_policy_file(self):
        self.client.login(username='policy-employee', password='password')
        response = self.client.get(self.file_url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Cache-Control'], 'private, no-store')
        self.assertEqual(response['X-Content-Type-Options'], 'nosniff')
        self.assertIn('attachment', response['Content-Disposition'])
        self.assertEqual(b''.join(response.streaming_content), b'%PDF-1.7 private policy content')

    def test_employee_from_another_organization_cannot_download_policy_file(self):
        self.client.login(username='policy-other', password='password')
        response = self.client.get(self.file_url())
        self.assertEqual(response.status_code, 404)

    def test_unpublished_policy_file_is_not_available(self):
        self.document.status = EmployeeDocument.Status.DRAFT
        self.document.save(update_fields=('status', 'updated_at'))
        self.client.login(username='policy-employee', password='password')
        response = self.client.get(self.file_url())
        self.assertEqual(response.status_code, 404)

    def test_user_without_employee_profile_cannot_download_policy_file(self):
        self.client.login(username='policy-hr', password='password')
        response = self.client.get(self.file_url())
        self.assertEqual(response.status_code, 403)

    def test_legacy_external_url_is_not_returned_by_employee_hub(self):
        self.document.file.delete(save=False)
        self.document.file_url = 'https://public.example.invalid/legacy-policy.pdf'
        self.document.save(update_fields=('file', 'file_url', 'updated_at'))
        self.client.login(username='policy-employee', password='password')
        response = self.client.get('/api/operations/employee/')
        self.assertEqual(response.status_code, 200)
        document = response.json()['documents'][0]
        self.assertNotIn('file_url', document)
        self.assertIsNone(document['download_url'])
        self.assertTrue(document['legacy_attachment_needs_reupload'])

    def test_hr_can_upload_validated_private_policy_file(self):
        self.client.login(username='policy-hr', password='password')
        response = self.client.post('/api/operations/', {
            'kind': 'document',
            'title': 'Security Policy',
            'category': 'Policy',
            'body': 'Internal security requirements',
            'status': 'PUBLISHED',
            'requires_acknowledgement': 'true',
            'file': SimpleUploadedFile('security.pdf', b'%PDF-1.7 test document'),
        })
        self.assertEqual(response.status_code, 201)
        document = EmployeeDocument.objects.get(id=response.json()['id'])
        self.assertTrue(document.file)
        self.assertTrue(document.requires_acknowledgement)
        self.assertTrue(document.file.name.startswith('organization-documents/'))
        self.addCleanup(document.file.delete)

    def test_hr_cannot_upload_file_with_mismatched_extension(self):
        self.client.login(username='policy-hr', password='password')
        response = self.client.post('/api/operations/', {
            'kind': 'document',
            'title': 'Unsafe Upload',
            'status': 'DRAFT',
            'file': SimpleUploadedFile('payload.pdf', b'<html>not a pdf</html>'),
        })
        self.assertEqual(response.status_code, 400)
        self.assertFalse(EmployeeDocument.objects.filter(title='Unsafe Upload').exists())

    def test_unauthenticated_user_cannot_download_policy_file(self):
        response = self.client.get(self.file_url())
        self.assertEqual(response.status_code, 401)


class OperationsTenantRelationshipValidationTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username='tenant-owner')
        self.other_user = User.objects.create_user(username='tenant-outsider')
        self.organization = Organization.objects.create(name='Tenant One', slug='tenant-one')
        self.other_organization = Organization.objects.create(name='Tenant Two', slug='tenant-two')
        OrganizationMembership.objects.create(organization=self.organization, user=self.user, role='HR')
        OrganizationMembership.objects.create(organization=self.other_organization, user=self.other_user, role='HR')
        self.employee = Employee.objects.create(
            employee_number='TEN-001', user=self.user, organization=self.organization,
            first_name='Tenant', last_name='One',
        )
        self.other_employee = Employee.objects.create(
            employee_number='TEN-002', user=self.other_user, organization=self.other_organization,
            first_name='Tenant', last_name='Two',
        )
        self.document = EmployeeDocument.objects.create(
            organization=self.organization, title='Policy', status=EmployeeDocument.Status.PUBLISHED,
        )
        self.other_project = Project.objects.create(
            organization=self.other_organization, code='OTHER', name='Other tenant project',
        )

    def test_document_acknowledgement_cannot_cross_organizations(self):
        acknowledgement = DocumentAcknowledgement(document=self.document, employee=self.other_employee)
        with self.assertRaisesMessage(ValidationError, 'same organization'):
            acknowledgement.full_clean()

    def test_timesheet_cannot_reference_another_organizations_project(self):
        entry = TimesheetEntry(
            employee=self.employee, project=self.other_project,
            work_date='2026-11-24', hours='8.00',
        )
        with self.assertRaisesMessage(ValidationError, 'same organization'):
            entry.full_clean()

    def test_compensation_change_cannot_use_another_organizations_approval(self):
        approval = ApprovalRequest.objects.create(
            organization=self.other_organization,
            requester=self.other_user,
            category='Compensation',
            title='Other tenant approval',
        )
        change = CompensationChange(
            employee=self.employee,
            effective_date='2026-11-24',
            proposed_salary='50000.00',
            reason='Annual adjustment',
            approval=approval,
        )
        with self.assertRaisesMessage(ValidationError, 'employee organization'):
            change.full_clean()

    def test_offboarding_task_assignee_must_belong_to_employee_organization(self):
        offboarding = OffboardingRecord.objects.create(
            employee=self.employee,
            last_working_day='2026-11-30',
        )
        task = OffboardingTask(
            offboarding=offboarding,
            title='Recover company equipment',
            assigned_to=self.other_user,
        )
        with self.assertRaisesMessage(ValidationError, 'active membership'):
            task.full_clean()

class TimesheetApprovalScopeTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.org = Organization.objects.create(name='Timesheet Scope', slug='timesheet-scope')
        self.other_org = Organization.objects.create(name='Other Scope', slug='other-scope')
        self.manager_user = User.objects.create_user(username='scope-manager', password='password')
        self.hr_user = User.objects.create_user(username='scope-hr', password='password')
        self.employee_user = User.objects.create_user(username='scope-employee', password='password')
        self.peer_user = User.objects.create_user(username='scope-peer', password='password')
        self.outsider_user = User.objects.create_user(username='scope-outsider', password='password')
        OrganizationMembership.objects.create(organization=self.org, user=self.manager_user, role='MANAGER')
        OrganizationMembership.objects.create(organization=self.org, user=self.hr_user, role='HR')
        OrganizationMembership.objects.create(organization=self.org, user=self.employee_user, role='EMPLOYEE')
        OrganizationMembership.objects.create(organization=self.org, user=self.peer_user, role='EMPLOYEE')
        OrganizationMembership.objects.create(organization=self.other_org, user=self.outsider_user, role='HR')
        self.manager = Employee.objects.create(employee_number='TS-MGR', user=self.manager_user, organization=self.org, first_name='Team', last_name='Manager')
        self.employee = Employee.objects.create(employee_number='TS-EMP', user=self.employee_user, organization=self.org, manager=self.manager, first_name='Direct', last_name='Report')
        self.peer = Employee.objects.create(employee_number='TS-PEER', user=self.peer_user, organization=self.org, first_name='Peer', last_name='Worker')
        self.project = Project.objects.create(organization=self.org, code='TS', name='Timesheet project')

    def make_entry(self, employee):
        return TimesheetEntry.objects.create(employee=employee, project=self.project, work_date='2026-11-24', hours='8.00', status=TimesheetEntry.Status.SUBMITTED)

    def decide(self, user, entry):
        self.client.login(username=user, password='password')
        return self.client.post(f'/api/operations/timesheets/{entry.id}/decision/', data='{"decision":"approve"}', content_type='application/json')

    def test_manager_can_approve_direct_report(self):
        entry = self.make_entry(self.employee)
        response = self.decide('scope-manager', entry)
        self.assertEqual(response.status_code, 200)

    def test_manager_cannot_approve_peer(self):
        entry = self.make_entry(self.peer)
        response = self.decide('scope-manager', entry)
        self.assertEqual(response.status_code, 403)
        entry.refresh_from_db()
        self.assertEqual(entry.status, TimesheetEntry.Status.SUBMITTED)

    def test_hr_can_approve_organization_wide(self):
        entry = self.make_entry(self.peer)
        response = self.decide('scope-hr', entry)
        self.assertEqual(response.status_code, 200)

    def test_employee_cannot_approve_timesheets(self):
        entry = self.make_entry(self.peer)
        response = self.decide('scope-employee', entry)
        self.assertEqual(response.status_code, 403)

    def test_manager_cannot_approve_own_timesheet(self):
        entry = self.make_entry(self.manager)
        response = self.decide('scope-manager', entry)
        self.assertEqual(response.status_code, 403)
