from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.employees.models import Employee
from apps.organization.models import Organization, OrganizationMembership
from .models import BenefitPlan, Candidate, JobApplication, JobOpening, PerformanceCycle, PerformanceReview


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
