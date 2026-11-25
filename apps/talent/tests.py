import json
from datetime import date

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.employees.models import Employee
from apps.organization.models import Organization, OrganizationMembership
from .models import BenefitEnrollment, BenefitPlan, Candidate, EmployeeGoal, JobApplication, JobOpening, OffboardingRecord, OffboardingClearanceEvidence, PerformanceCycle, PerformanceReview


class TalentModelsTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name='Acme', slug='acme')
        self.user = get_user_model().objects.create_user(username='hr', password='test-pass')
        OrganizationMembership.objects.create(organization=self.org, user=self.user, role=OrganizationMembership.Role.HR)
        self.employee = Employee.objects.create(organization=self.org, user=self.user, employee_number='E-1', first_name='Jane', last_name='Doe')

    def test_candidate_cannot_apply_twice_to_same_job(self):
        job = JobOpening.objects.create(organization=self.org, title='Designer')
        candidate = Candidate.objects.create(organization=self.org, first_name='Sam', last_name='Smith', email='sam@example.com')
        JobApplication.objects.create(job=job, candidate=candidate)
        with self.assertRaises(Exception):
            JobApplication.objects.create(job=job, candidate=candidate)

    def test_review_is_unique_per_cycle_and_employee(self):
        cycle = PerformanceCycle.objects.create(organization=self.org, name='2026 Review', start_date=date(2026, 1, 1), end_date=date(2026, 12, 31))
        PerformanceReview.objects.create(cycle=cycle, employee=self.employee, reviewer=self.user)
        with self.assertRaises(Exception):
            PerformanceReview.objects.create(cycle=cycle, employee=self.employee, reviewer=self.user)

    def test_benefit_plan_is_scoped_to_organization(self):
        plan = BenefitPlan.objects.create(organization=self.org, name='Medical')
        self.assertEqual(plan.organization, self.org)


class TalentTenantRelationshipValidationTests(TestCase):
    def setUp(self):
        self.org_one = Organization.objects.create(name='Talent One', slug='talent-one')
        self.org_two = Organization.objects.create(name='Talent Two', slug='talent-two')
        self.user_one = get_user_model().objects.create_user(username='talent-one-hr')
        self.user_two = get_user_model().objects.create_user(username='talent-two-hr')
        OrganizationMembership.objects.create(organization=self.org_one, user=self.user_one, role=OrganizationMembership.Role.HR)
        OrganizationMembership.objects.create(organization=self.org_two, user=self.user_two, role=OrganizationMembership.Role.HR)
        self.employee_one = Employee.objects.create(
            organization=self.org_one, user=self.user_one, employee_number='TAL-001',
            first_name='One', last_name='Employee',
        )
        self.employee_two = Employee.objects.create(
            organization=self.org_two, user=self.user_two, employee_number='TAL-002',
            first_name='Two', last_name='Employee',
        )
        self.cycle_two = PerformanceCycle.objects.create(
            organization=self.org_two, name='Other cycle',
            start_date=date(2026, 1, 1), end_date=date(2026, 12, 31),
        )

    def test_job_application_cannot_pair_cross_tenant_job_and_candidate(self):
        job = JobOpening.objects.create(organization=self.org_one, title='Engineer')
        candidate = Candidate.objects.create(
            organization=self.org_two, first_name='Other', last_name='Candidate',
            email='candidate@other.example',
        )
        application = JobApplication(job=job, candidate=candidate)
        with self.assertRaisesMessage(ValidationError, 'same organization'):
            application.full_clean()

    def test_employee_goal_cannot_use_another_tenant_cycle(self):
        goal = EmployeeGoal(employee=self.employee_one, cycle=self.cycle_two, title='Cross tenant goal')
        with self.assertRaisesMessage(ValidationError, 'same organization'):
            goal.full_clean()

    def test_performance_review_cannot_use_another_tenant_cycle(self):
        review = PerformanceReview(cycle=self.cycle_two, employee=self.employee_one, reviewer=self.user_one)
        with self.assertRaisesMessage(ValidationError, 'same organization'):
            review.full_clean()

    def test_benefit_enrollment_cannot_use_another_tenant_plan(self):
        plan = BenefitPlan.objects.create(organization=self.org_two, name='Other tenant plan')
        enrollment = BenefitEnrollment(employee=self.employee_one, plan=plan, effective_date=date(2026, 1, 1))
        with self.assertRaisesMessage(ValidationError, 'same organization'):
            enrollment.full_clean()


class OffboardingClearanceWorkflowTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.org = Organization.objects.create(name='Offboarding Org', slug='offboarding-org')
        self.hr = User.objects.create_user(username='offboarding-hr', password='password')
        self.employee_user = User.objects.create_user(username='offboarding-employee', password='password')
        OrganizationMembership.objects.create(organization=self.org, user=self.hr, role='HR')
        OrganizationMembership.objects.create(organization=self.org, user=self.employee_user, role='EMPLOYEE')
        self.employee = Employee.objects.create(
            employee_number='OFF-001', user=self.employee_user, organization=self.org,
            first_name='Leaving', last_name='Employee',
        )
        self.record = OffboardingRecord.objects.create(
            employee=self.employee,
            last_working_day=date(2026, 11, 30),
            required_clearances=['IT', 'FINANCE'],
        )
        self.client.login(username='offboarding-hr', password='password')

    def test_client_clearance_booleans_cannot_complete_offboarding(self):
        self.record.status = OffboardingRecord.Status.IN_PROGRESS
        self.record.save(update_fields=('status', 'updated_at'))
        response = self.client.patch(
            f'/api/offboarding/{self.record.id}/status/',
            data='{"status":"COMPLETED","clearances":{"IT":true,"FINANCE":true}}',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 409)
        self.record.refresh_from_db()
        self.assertEqual(self.record.status, OffboardingRecord.Status.IN_PROGRESS)

    def test_required_clearance_evidence_is_persisted_and_completion_requires_it(self):
        self.record.status = OffboardingRecord.Status.IN_PROGRESS
        self.record.save(update_fields=('status', 'updated_at'))
        self.employee.separation_date = self.record.last_working_day
        self.employee.save(update_fields=('separation_date', 'updated_at'))
        for key in ('IT', 'FINANCE'):
            response = self.client.post(
                f'/api/offboarding/{self.record.id}/clearances/',
                data=json.dumps({
                    'clearance_key': key,
                    'notes': f'{key} clearance checked and verified',
                    'evidence_reference': f'CASE-{key}-001',
                }),
                content_type='application/json',
            )
            self.assertEqual(response.status_code, 201)
        self.assertEqual(self.record.clearance_evidence.count(), 2)
        response = self.client.patch(
            f'/api/offboarding/{self.record.id}/status/',
            data='{"status":"COMPLETED","clearances":{"IT":false}}',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.record.refresh_from_db()
        self.assertEqual(self.record.status, OffboardingRecord.Status.COMPLETED)

    def test_unconfigured_clearance_evidence_is_rejected(self):
        response = self.client.post(
            f'/api/offboarding/{self.record.id}/clearances/',
            data=json.dumps({'clearance_key': 'UNLISTED', 'notes': 'Not configured'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(OffboardingClearanceEvidence.objects.count(), 0)

    def test_completed_offboarding_cannot_be_reopened(self):
        self.record.status = OffboardingRecord.Status.COMPLETED
        self.record.save(update_fields=('status', 'updated_at'))
        response = self.client.patch(
            f'/api/offboarding/{self.record.id}/status/',
            data='{"status":"IN_PROGRESS"}',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 409)
