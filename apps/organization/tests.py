from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.db import transaction
from django.test import TestCase

from .models import Department, Organization, OrganizationMembership, Position


class OrganizationMembershipTests(TestCase):
	def setUp(self):
		self.organization = Organization.objects.create(name='Acme Corporation', slug='acme')
		self.user = get_user_model().objects.create_user(username='owner', password='test-password')

	def test_membership_connects_user_to_organization(self):
		membership = OrganizationMembership.objects.create(
			organization=self.organization,
			user=self.user,
			role=OrganizationMembership.Role.OWNER,
		)

		self.assertEqual(self.user.organization_memberships.get(), membership)
		self.assertEqual(self.organization.memberships.get(), membership)

	def test_user_can_only_have_one_membership_per_organization(self):
		OrganizationMembership.objects.create(organization=self.organization, user=self.user)

		with self.assertRaises(IntegrityError):
			OrganizationMembership.objects.create(organization=self.organization, user=self.user)

	def test_roles_expose_expected_capabilities(self):
		membership = OrganizationMembership.objects.create(
			organization=self.organization,
			user=self.user,
			role=OrganizationMembership.Role.HR,
		)

		self.assertTrue(membership.has_permission('manage_employees'))
		self.assertTrue(membership.has_permission('manage_payroll'))
		self.assertFalse(membership.has_permission('manage_organization'))

	def test_employee_role_is_limited_to_self_service(self):
		membership = OrganizationMembership.objects.create(
			organization=self.organization,
			user=self.user,
			role=OrganizationMembership.Role.EMPLOYEE,
		)

		self.assertTrue(membership.has_permission('submit_leave'))
		self.assertFalse(membership.has_permission('manage_attendance'))

	def test_super_user_can_view_every_operational_module(self):
		membership = OrganizationMembership.objects.create(
			organization=self.organization,
			user=self.user,
			role=OrganizationMembership.Role.SUPER_USER,
		)

		self.assertTrue(membership.has_permission('view_employees'))
		self.assertTrue(membership.has_permission('view_attendance'))
		self.assertTrue(membership.has_permission('manage_organization'))

	def test_structure_codes_are_unique_per_organization(self):
		Department.objects.create(organization=self.organization, code='HR', name='Human Resources')
		with self.assertRaises(IntegrityError):
			with transaction.atomic():
				Department.objects.create(organization=self.organization, code='HR', name='Another HR')
		Position.objects.create(organization=self.organization, code='DEV', title='Developer')
		self.assertEqual(self.organization.positions.get(code='DEV').title, 'Developer')

	def test_current_user_endpoint_returns_role_and_permissions(self):
		OrganizationMembership.objects.create(
			organization=self.organization,
			user=self.user,
			role=OrganizationMembership.Role.TEAM_LEADER,
		)
		self.client.login(username='owner', password='test-password')

		response = self.client.get('/api/me/')

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json()['role'], 'TEAM_LEADER')
		self.assertFalse(response.json()['is_maintenance_user'])
		self.assertIn('manage_attendance', response.json()['permissions'])
