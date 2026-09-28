from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import BaseModel
from apps.organization.models import Organization


class Client(BaseModel):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='clients')
    code = models.CharField(max_length=30)
    name = models.CharField(max_length=150)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=('organization', 'code'), name='unique_client_code_per_organization')]
        ordering = ('name',)

    def __str__(self):
        return f'{self.code} - {self.name}'


class ClientSite(BaseModel):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='sites')
    name = models.CharField(max_length=150)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=('client', 'name'), name='unique_client_site_name')]
        ordering = ('client', 'name')

    def __str__(self):
        return f'{self.client.name} - {self.name}'


class ShiftTemplate(BaseModel):
    # Nullable preserves existing global templates while allowing new templates
    # to be explicitly owned by an organization. Cross-tenant templates are never
    # valid for a tenant-owned EmployeeAssignment.
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, null=True, blank=True, related_name='shift_templates')
    name = models.CharField(max_length=100, unique=True)
    start_time = models.TimeField()
    end_time = models.TimeField()

    def clean(self):
        super().clean()
        if self.end_time == self.start_time:
            raise ValidationError('Shift start and end time cannot be identical.')

    def __str__(self):
        return self.name


class ScheduleRule(BaseModel):
    """Recurring, effective-dated work pattern for an employee."""

    class Pattern(models.TextChoices):
        WEEKLY = 'WEEKLY', 'Weekly'
        ROTATING = 'ROTATING', 'Rotating'

    employee = models.ForeignKey('employees.Employee', on_delete=models.PROTECT, related_name='schedule_rules')
    shift_template = models.ForeignKey(ShiftTemplate, on_delete=models.PROTECT, related_name='schedule_rules')
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    pattern = models.CharField(max_length=20, choices=Pattern.choices, default=Pattern.WEEKLY)
    weekdays = models.JSONField(default=list)
    cycle_weeks = models.PositiveIntegerField(default=1)
    rest_days = models.JSONField(default=list)
    priority = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ('-priority', '-effective_from', '-created_at')
        indexes = [
            models.Index(fields=('employee', 'effective_from'), name='schedule_rule_emp_date_idx'),
        ]

    def clean(self):
        super().clean()
        if self.effective_to and self.effective_to < self.effective_from:
            raise ValidationError('Schedule rule end date cannot be before its effective date.')
        if not self.weekdays:
            raise ValidationError('At least one weekday must be configured.')
        invalid = [int(day) for day in self.weekdays if int(day) not in range(7)]
        if invalid:
            raise ValidationError('Weekdays must use Python weekday numbers 0 through 6.')
        if self.pattern == self.Pattern.ROTATING and self.cycle_weeks < 1:
            raise ValidationError('A rotating schedule must have at least one cycle week.')
        if self.employee_id and self.shift_template.organization_id not in (None, self.employee.organization_id):
            raise ValidationError('The schedule shift must belong to the employee organization.')


class ScheduleException(BaseModel):
    employee = models.ForeignKey('employees.Employee', on_delete=models.PROTECT, related_name='schedule_exceptions')
    work_date = models.DateField()
    shift_template = models.ForeignKey(ShiftTemplate, on_delete=models.PROTECT, null=True, blank=True, related_name='schedule_exceptions')
    is_rest_day = models.BooleanField(default=False)
    reason = models.CharField(max_length=255)
    approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey('auth.User', on_delete=models.PROTECT, null=True, blank=True, related_name='approved_schedule_exceptions')

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('employee', 'work_date'), name='unique_schedule_exception_employee_date'),
        ]

    def clean(self):
        super().clean()
        if not self.is_rest_day and not self.shift_template_id:
            raise ValidationError('A working schedule exception requires a shift.')
        if self.shift_template_id and self.shift_template.organization_id not in (None, self.employee.organization_id):
            raise ValidationError('The exception shift must belong to the employee organization.')


class CoverShift(BaseModel):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'
        CANCELLED = 'CANCELLED', 'Cancelled'

    employee = models.ForeignKey('employees.Employee', on_delete=models.PROTECT, related_name='cover_shifts')
    work_date = models.DateField()
    shift_template = models.ForeignKey(ShiftTemplate, on_delete=models.PROTECT, related_name='cover_shifts')
    client = models.ForeignKey(Client, on_delete=models.PROTECT, null=True, blank=True, related_name='cover_shifts')
    client_site = models.ForeignKey(ClientSite, on_delete=models.PROTECT, null=True, blank=True, related_name='cover_shifts')
    reason = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    requested_by = models.ForeignKey('auth.User', on_delete=models.PROTECT, related_name='requested_cover_shifts')
    approved_by = models.ForeignKey('auth.User', on_delete=models.PROTECT, null=True, blank=True, related_name='approved_cover_shifts')
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('employee', 'work_date'), name='unique_cover_shift_employee_date'),
        ]
        indexes = [
            models.Index(fields=('employee', 'work_date', 'status'), name='cover_shift_emp_date_status_idx'),
        ]

    def clean(self):
        super().clean()
        if self.shift_template.organization_id not in (None, self.employee.organization_id):
            raise ValidationError('The cover shift must use an organization-owned or global shift.')
        if self.client_id and self.client.organization_id != self.employee.organization_id:
            raise ValidationError('The cover client must belong to the employee organization.')
        if self.client_site_id:
            if not self.client_id or self.client_site.client_id != self.client_id:
                raise ValidationError('The cover site must belong to the selected client.')
            if self.client_site.client.organization_id != self.employee.organization_id:
                raise ValidationError('The cover site must belong to the employee organization.')
