from django.conf import settings
from django.db import models

from apps.core.models import BaseModel


class Employee(BaseModel):
	employee_number = models.CharField(max_length=30, unique=True)
	user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='employee_profile')
	organization = models.ForeignKey('organization.Organization', on_delete=models.PROTECT, related_name='employees')
	department = models.ForeignKey('organization.Department', on_delete=models.PROTECT, null=True, blank=True, related_name='employees')
	position = models.ForeignKey('organization.Position', on_delete=models.PROTECT, null=True, blank=True, related_name='employees')
	employment_type = models.ForeignKey('organization.EmploymentType', on_delete=models.PROTECT, null=True, blank=True, related_name='employees')
	first_name = models.CharField(max_length=100)
	last_name = models.CharField(max_length=100)
	is_active = models.BooleanField(default=True)

	class Meta:
		ordering = ('last_name', 'first_name')

	def __str__(self):
		return f'{self.employee_number} - {self.first_name} {self.last_name}'


class EmployeeAssignment(BaseModel):
	employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name='assignments')
	shift_template = models.ForeignKey('workforce.ShiftTemplate', on_delete=models.PROTECT, related_name='employee_assignments')
	client = models.ForeignKey('workforce.Client', on_delete=models.PROTECT, null=True, blank=True, related_name='employee_assignments')
	client_site = models.ForeignKey('workforce.ClientSite', on_delete=models.PROTECT, null=True, blank=True, related_name='employee_assignments')
	cost_center = models.ForeignKey('organization.CostCenter', on_delete=models.PROTECT, null=True, blank=True, related_name='employee_assignments')
	start_date = models.DateField()
	end_date = models.DateField(null=True, blank=True)
	is_primary = models.BooleanField(default=False)

	class Meta:
		ordering = ('-is_primary', '-start_date')
