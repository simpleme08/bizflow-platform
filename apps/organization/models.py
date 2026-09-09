from django.conf import settings
from django.db import models

from apps.core.models import BaseModel


class Organization(BaseModel):
	name = models.CharField(max_length=200)
	slug = models.SlugField(max_length=80, unique=True)
	is_active = models.BooleanField(default=True)

	class Meta:
		ordering = ('name',)

	def __str__(self):
		return self.name


class Department(BaseModel):
	organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='departments')
	code = models.CharField(max_length=20)
	name = models.CharField(max_length=100)

	class Meta:
		constraints = [models.UniqueConstraint(fields=('organization', 'code'), name='unique_department_code_per_organization')]
		ordering = ('name',)

	def __str__(self):
		return f'{self.code} - {self.name}'


class Position(BaseModel):
	organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='positions')
	code = models.CharField(max_length=20)
	title = models.CharField(max_length=100)

	class Meta:
		constraints = [models.UniqueConstraint(fields=('organization', 'code'), name='unique_position_code_per_organization')]
		ordering = ('title',)

	def __str__(self):
		return f'{self.code} - {self.title}'


class EmploymentType(BaseModel):
	organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='employment_types')
	code = models.CharField(max_length=20)
	name = models.CharField(max_length=100)
	eligible_for_overtime = models.BooleanField(default=True)

	class Meta:
		constraints = [models.UniqueConstraint(fields=('organization', 'code'), name='unique_employment_type_code_per_organization')]
		ordering = ('name',)

	def __str__(self):
		return f'{self.code} - {self.name}'


class CostCenter(BaseModel):
	organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='cost_centers')
	code = models.CharField(max_length=20)
	name = models.CharField(max_length=100)

	class Meta:
		constraints = [models.UniqueConstraint(fields=('organization', 'code'), name='unique_cost_center_code_per_organization')]
		ordering = ('name',)

	def __str__(self):
		return f'{self.code} - {self.name}'


class OrganizationMembership(BaseModel):
	class Role(models.TextChoices):
		OWNER = 'OWNER', 'Owner'
		ADMIN = 'ADMIN', 'Administrator'
		CEO = 'CEO', 'Chief Executive Officer'
		HR = 'HR', 'Human Resources'
		SME = 'SME', 'Subject Matter Expert'
		TEAM_LEADER = 'TEAM_LEADER', 'Team Leader'
		MANAGER = 'MANAGER', 'Manager'
		EMPLOYEE = 'EMPLOYEE', 'Employee'
		SUPER_USER = 'SUPER_USER', 'Super User'

	ROLE_PERMISSIONS = {
		'OWNER': {'view_employees', 'view_attendance', 'manage_organization', 'manage_users', 'manage_employees', 'manage_attendance', 'approve_leave', 'view_payroll', 'manage_payroll', 'view_reports', 'manage_recruiting', 'manage_performance', 'manage_benefits', 'manage_offboarding'},
		'SUPER_USER': {'view_employees', 'view_attendance', 'manage_organization', 'manage_users', 'manage_employees', 'manage_attendance', 'approve_leave', 'view_payroll', 'manage_payroll', 'view_reports', 'manage_recruiting', 'manage_performance', 'manage_benefits', 'manage_offboarding'},
		'CEO': {'view_employees', 'view_attendance', 'approve_leave', 'view_payroll', 'view_reports'},
		'HR': {'manage_users', 'manage_employees', 'manage_attendance', 'approve_leave', 'view_payroll', 'manage_payroll', 'view_reports', 'manage_recruiting', 'manage_performance', 'manage_benefits', 'manage_offboarding'},
		'ADMIN': {'manage_users', 'manage_employees', 'manage_attendance', 'approve_leave', 'view_reports', 'manage_recruiting', 'manage_performance', 'manage_benefits', 'manage_offboarding'},
		'SME': {'view_employees', 'view_attendance', 'manage_attendance', 'view_reports'},
		'TEAM_LEADER': {'view_employees', 'view_attendance', 'manage_attendance', 'approve_leave'},
		'MANAGER': {'view_employees', 'view_attendance', 'manage_attendance', 'approve_leave'},
		'EMPLOYEE': {'view_self', 'submit_leave', 'view_self_payroll'},
	}

	organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='memberships')
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='organization_memberships')
	role = models.CharField(max_length=20, choices=Role.choices, default=Role.EMPLOYEE)
	is_active = models.BooleanField(default=True)

	class Meta:
		constraints = [
			models.UniqueConstraint(
				fields=('organization', 'user'),
				name='unique_organization_membership',
			),
		]
		ordering = ('organization', 'user')

	def has_permission(self, permission):
		return self.is_active and self.organization.is_active and permission in self.ROLE_PERMISSIONS.get(self.role, set())
