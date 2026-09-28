from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.employees.models import Employee, EmployeeDocument
from apps.onboarding.models import EmployeeOnboarding, OnboardingTask, OnboardingTaskTemplate, OnboardingWorkflow
from apps.organization.models import Organization, OrganizationMembership


class OnboardingCompletionGateTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.hr = User.objects.create_user(username='onboarding-hr', password='safe-password')
        self.employee_user = User.objects.create_user(username='onboarding-employee', password='safe-password')
        self.org = Organization.objects.create(name='Onboarding Org', slug='onboarding-org')
        OrganizationMembership.objects.create(user=self.hr, organization=self.org, role='HR', is_active=True)
        OrganizationMembership.objects.create(user=self.employee_user, organization=self.org, role='EMPLOYEE', is_active=True)
        self.employee = Employee.objects.create(
            organization=self.org, user=self.employee_user, employee_number='ONB-001',
            first_name='Test', last_name='Employee', status=Employee.Status.ONBOARDING, is_active=True,
        )
        self.workflow = OnboardingWorkflow.objects.create(
            organization=self.org, name='Standard', required_document_types=['Valid ID'],
        )
        template = OnboardingTaskTemplate.objects.create(workflow=self.workflow, title='Complete orientation', is_required=True)
        self.onboarding = EmployeeOnboarding.objects.create(employee=self.employee, workflow=self.workflow)
        self.task = OnboardingTask.objects.create(onboarding=self.onboarding, template=template, title=template.title, status=OnboardingTask.Status.COMPLETED)
        self.client.force_login(self.hr)
        session = self.client.session
        session['active_organization_id'] = str(self.org.id)
        session.save()

    def test_completion_is_blocked_when_required_document_missing(self):
        response = self.client.patch(
            f'/api/onboarding/{self.onboarding.id}/status/',
            data='{"status":"COMPLETED"}',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['missing_document_types'], ['Valid ID'])

    def test_completion_succeeds_with_required_document(self):
        EmployeeDocument.objects.create(
            employee=self.employee, document_type='Valid ID', name='Passport',
            status='ACTIVE',
        )
        response = self.client.patch(
            f'/api/onboarding/{self.onboarding.id}/status/',
            data='{"status":"COMPLETED"}',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'COMPLETED')
