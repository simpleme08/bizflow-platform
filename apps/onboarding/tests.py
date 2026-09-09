from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.employees.models import Employee
from apps.onboarding.models import EmployeeOnboarding, OnboardingTask, OnboardingTaskTemplate, OnboardingWorkflow
from apps.organization.models import Organization, OrganizationMembership


class OnboardingTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='hr_manager', password='password')
        self.organization = Organization.objects.create(name='Acme', slug='acme')
        OrganizationMembership.objects.create(organization=self.organization, user=self.user, role=OrganizationMembership.Role.HR)
        self.employee = Employee.objects.create(
            employee_number='EMP-ONB-001',
            user=get_user_model().objects.create_user(username='new_employee', password='password'),
            organization=self.organization,
            first_name='Ava',
            last_name='Stone',
        )
        self.workflow = OnboardingWorkflow.objects.create(organization=self.organization, name='Standard onboarding')
        self.template = OnboardingTaskTemplate.objects.create(
            workflow=self.workflow,
            title='Complete tax forms',
            description='Submit required tax documents.',
            order=1,
        )

    def test_hr_can_create_onboarding_record(self):
        self.client.login(username='hr_manager', password='password')
        response = self.client.post('/api/onboarding/', {
            'employee_id': str(self.employee.id),
            'workflow_id': str(self.workflow.id),
            'start_date': '2026-09-01',
            'expected_completion_date': '2026-09-10',
        }, content_type='application/json')

        self.assertEqual(response.status_code, 201)
        self.assertTrue(EmployeeOnboarding.objects.filter(employee=self.employee).exists())

    def test_onboarding_task_can_be_updated(self):
        onboarding = EmployeeOnboarding.objects.create(
            employee=self.employee,
            workflow=self.workflow,
            start_date=date(2026, 9, 1),
            expected_completion_date=date(2026, 9, 10),
            status=EmployeeOnboarding.Status.IN_PROGRESS,
        )
        task = OnboardingTask.objects.create(
            onboarding=onboarding,
            template=self.template,
            title=self.template.title,
            description=self.template.description,
            due_date=date(2026, 9, 3),
            status=OnboardingTask.Status.PENDING,
        )
        self.client.login(username='hr_manager', password='password')

        response = self.client.patch(f'/api/onboarding/{onboarding.id}/tasks/{task.id}/', {
            'status': 'COMPLETED'
        }, content_type='application/json')

        self.assertEqual(response.status_code, 200)
        task.refresh_from_db()
        self.assertEqual(task.status, OnboardingTask.Status.COMPLETED)

    def test_employee_cannot_manage_onboarding_without_permission(self):
        self.client.login(username='new_employee', password='password')
        response = self.client.get('/api/onboarding/')

        self.assertEqual(response.status_code, 403)
