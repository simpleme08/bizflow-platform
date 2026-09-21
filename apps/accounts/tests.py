from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.employees.models import Employee
from apps.organization.models import Organization
from apps.organization.models import OrganizationMembership


class EmployeeLoginTests(TestCase):
    def test_public_website_is_available(self):
        response = self.client.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'People.')
        self.assertContains(response, 'Sign in to BizFlow')
        self.assertContains(response, 'Open time clock')
        self.assertNotContains(response, 'Client workspaces')

    def setUp(self):
        self.user = get_user_model().objects.create_user(username='employee', password='password')
        organization = Organization.objects.create(name='Acme', slug='acme')
        OrganizationMembership.objects.create(organization=organization, user=self.user, role=OrganizationMembership.Role.EMPLOYEE)
        Employee.objects.create(employee_number='EMP-LOGIN', user=self.user, organization=organization, first_name='Ana', last_name='Reyes')

    def test_single_login_redirects_employee_to_ess(self):
        response = self.client.post('/login/', {'username': 'employee', 'password': 'password'})

        self.assertRedirects(response, '/ess/')

    def test_back_to_workspace_link_uses_logged_in_user_role(self):
        manager = get_user_model().objects.create_user(username='manager', password='password')
        organization = Organization.objects.create(name='Branch Ops', slug='branch-ops')
        OrganizationMembership.objects.create(organization=organization, user=manager, role=OrganizationMembership.Role.MANAGER)
        self.client.force_login(manager)
        manager_response = self.client.get('/employees/')
        self.assertContains(manager_response, 'href="/workspace/"')

        self.client.logout()
        self.client.force_login(self.user)
        employee_response = self.client.get('/ess/')
        self.assertNotContains(employee_response, 'Back to workspace')

    def test_dashboard_redirects_employees_to_ess(self):
        self.client.force_login(self.user)
        response = self.client.get('/workspace/')
        self.assertRedirects(response, '/ess/')

    def test_ess_page_hides_back_to_workspace_link(self):
        self.client.force_login(self.user)
        response = self.client.get('/ess/')
        self.assertNotContains(response, 'Back to workspace')

    def test_unified_login_rejects_account_without_organization_access(self):
        get_user_model().objects.create_user(username='admin-only', password='password')

        response = self.client.post('/login/', {'username': 'admin-only', 'password': 'password'})

        self.assertEqual(response.status_code, 401)
