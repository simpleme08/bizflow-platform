from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.core.models import BaseModel


class Employee(BaseModel):
    class Status(models.TextChoices):
        ONBOARDING = 'ONBOARDING', 'Onboarding'
        PROBATIONARY = 'PROBATIONARY', 'Probationary'
        REGULAR = 'REGULAR', 'Regular'
        SUSPENDED = 'SUSPENDED', 'Suspended'
        RESIGNED = 'RESIGNED', 'Resigned'
        TERMINATED = 'TERMINATED', 'Terminated'
        SEPARATED = 'SEPARATED', 'Separated'

    employee_number = models.CharField(max_length=30, unique=True)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='employee_profile')
    organization = models.ForeignKey('organization.Organization', on_delete=models.PROTECT, related_name='employees')
    department = models.ForeignKey('organization.Department', on_delete=models.PROTECT, null=True, blank=True, related_name='employees')
    position = models.ForeignKey('organization.Position', on_delete=models.PROTECT, null=True, blank=True, related_name='employees')
    employment_type = models.ForeignKey('organization.EmploymentType', on_delete=models.PROTECT, null=True, blank=True, related_name='employees')
    manager = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='direct_reports')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    birth_date = models.DateField(null=True, blank=True)
    sex = models.CharField(max_length=30, blank=True)
    personal_email = models.EmailField(blank=True)
    work_email = models.EmailField(blank=True)
    mobile_number = models.CharField(max_length=30, blank=True)
    address = models.TextField(blank=True)
    emergency_contact_name = models.CharField(max_length=150, blank=True)
    emergency_contact_phone = models.CharField(max_length=30, blank=True)
    hire_date = models.DateField(null=True, blank=True)
    regularization_date = models.DateField(null=True, blank=True)
    separation_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ONBOARDING)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ('last_name', 'first_name')
        indexes = [models.Index(fields=('organization', 'status'))]

    def clean(self):
        super().clean()
        if self.manager_id and self.manager_id == self.id:
            raise ValidationError({'manager': 'An employee cannot be their own manager.'})
        for field in ('department', 'position', 'employment_type'):
            value = getattr(self, field, None)
            if value is not None and value.organization_id != self.organization_id:
                raise ValidationError({field: 'The selected record must belong to the employee organization.'})
        if self.manager_id and self.manager and self.manager.organization_id != self.organization_id:
            raise ValidationError({'manager': 'The manager must belong to the employee organization.'})

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

    def clean(self):
        if self.end_date and self.end_date < self.start_date:
            raise ValidationError({'end_date': 'End date cannot be before start date.'})


class EmployeeEmploymentHistory(BaseModel):
    class Action(models.TextChoices):
        ONBOARD = 'ONBOARD', 'Onboard'
        REGULARIZE = 'REGULARIZE', 'Regularize'
        PROMOTE = 'PROMOTE', 'Promote'
        TRANSFER = 'TRANSFER', 'Transfer'
        SUSPEND = 'SUSPEND', 'Suspend'
        REINSTATE = 'REINSTATE', 'Reinstate'
        RESIGN = 'RESIGN', 'Resign'
        TERMINATE = 'TERMINATE', 'Terminate'
        SEPARATE = 'SEPARATE', 'Separate'
        PROFILE_UPDATE = 'PROFILE_UPDATE', 'Profile update'

    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name='employment_history')
    action = models.CharField(max_length=30, choices=Action.choices)
    effective_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Employee.Status.choices)
    department = models.ForeignKey('organization.Department', on_delete=models.SET_NULL, null=True, blank=True)
    position = models.ForeignKey('organization.Position', on_delete=models.SET_NULL, null=True, blank=True)
    employment_type = models.ForeignKey('organization.EmploymentType', on_delete=models.SET_NULL, null=True, blank=True)
    manager = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name='employment_history_as_manager')
    reason = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='employee_history_actions')

    class Meta:
        ordering = ('-effective_date', '-created_at')
        constraints = [models.UniqueConstraint(fields=('employee', 'action', 'effective_date'), name='uniq_employee_history_action_date')]

    def clean(self):
        if self.end_date and self.end_date < self.effective_date:
            raise ValidationError({'end_date': 'End date cannot be before effective date.'})
        for field in ('department', 'position', 'employment_type'):
            value = getattr(self, field, None)
            if value is not None and value.organization_id != self.employee.organization_id:
                raise ValidationError({field: 'The selected record must belong to the employee organization.'})
        if self.manager and self.manager.organization_id != self.employee.organization_id:
            raise ValidationError({'manager': 'The manager must belong to the employee organization.'})


class EmployeeDocument(BaseModel):
    class DocumentType(models.TextChoices):
        CONTRACT = 'CONTRACT', 'Contract'
        GOVERNMENT_ID = 'GOVERNMENT_ID', 'Government ID'
        TAX = 'TAX', 'Tax'
        COMPANY = 'COMPANY', 'Company'
        CERTIFICATION = 'CERTIFICATION', 'Certification'
        OTHER = 'OTHER', 'Other'

    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name='documents')
    document_type = models.CharField(max_length=30, choices=DocumentType.choices)
    name = models.CharField(max_length=150)
    reference_number = models.CharField(max_length=100, blank=True)
    issued_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    file_url = models.URLField(blank=True)
    notes = models.TextField(blank=True)
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_employee_documents')
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ('expiry_date', 'name')

    @property
    def is_expired(self):
        return bool(self.expiry_date and self.expiry_date < timezone.localdate())

    @property
    def expires_soon(self):
        if not self.expiry_date:
            return False
        return timezone.localdate() <= self.expiry_date <= timezone.localdate() + timedelta(days=30)
