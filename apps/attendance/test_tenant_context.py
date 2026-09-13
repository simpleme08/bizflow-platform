from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.employees.models import Employee
from apps.organization.models import Organization, OrganizationMembership


class AttendanceTenantContextTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username='multi-manager', password='test-password')
        self.org_a = Organization.objects.create(name='Alpha Corporation', slug='alpha')
        self.org_b = Organization.objects.create(name='Beta Corporation', slug='beta')
        OrganizationMembership.objects.create(
            organization=self.org_a,
            user=self.user,
            role=OrganizationMembership.Role.MANAGER,
            is_active=True,
        )
        OrganizationMembership.objects.create(
            organization=self.org_b,
            user=self.user,
            role=OrganizationMembership.Role.MANAGER,
            is_active=True,
        )
        self.employee = Employee.objects.create(
            employee_number='EMP-ALPHA-001',
            organization=self.org_a,
            first_name='Alpha',
            last_name='Employee',
            is_active=True,
        )
        self.client.login(username='multi-manager', password='test-password')

    def test_dashboard_fails_closed_without_selected_organization(self):
        response = self.client.get(reverse('dashboard-api'))
        self.assertEqual(response.status_code, 403)
        self.assertIn('Select an organization', response.json()['detail'])

    def test_attendance_write_fails_closed_without_selected_organization(self):
        response = self.client.post(
            reverse('record-attendance'),
            data={
                'employee_id': str(self.employee.id),
                'attendance_date': '2026-08-10',
            },
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 403)
