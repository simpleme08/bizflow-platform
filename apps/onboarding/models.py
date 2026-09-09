from django.conf import settings
from django.db import models

from apps.core.models import BaseModel


class OnboardingWorkflow(BaseModel):
    organization = models.ForeignKey('organization.Organization', on_delete=models.PROTECT, related_name='onboarding_workflows')
    name = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class OnboardingTaskTemplate(BaseModel):
    workflow = models.ForeignKey(OnboardingWorkflow, on_delete=models.CASCADE, related_name='task_templates')
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    is_required = models.BooleanField(default=True)

    class Meta:
        ordering = ('order', 'created_at')

    def __str__(self):
        return self.title


class EmployeeOnboarding(BaseModel):
    class Status(models.TextChoices):
        NOT_STARTED = 'NOT_STARTED', 'Not started'
        IN_PROGRESS = 'IN_PROGRESS', 'In progress'
        COMPLETED = 'COMPLETED', 'Completed'
        OVERDUE = 'OVERDUE', 'Overdue'

    employee = models.OneToOneField('employees.Employee', on_delete=models.CASCADE, related_name='onboarding_record')
    workflow = models.ForeignKey(OnboardingWorkflow, on_delete=models.PROTECT, related_name='employee_records')
    start_date = models.DateField(null=True, blank=True)
    expected_completion_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NOT_STARTED)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f'{self.employee} onboarding'


class OnboardingTask(BaseModel):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        IN_PROGRESS = 'IN_PROGRESS', 'In progress'
        COMPLETED = 'COMPLETED', 'Completed'
        SKIPPED = 'SKIPPED', 'Skipped'

    onboarding = models.ForeignKey(EmployeeOnboarding, on_delete=models.CASCADE, related_name='tasks')
    template = models.ForeignKey(OnboardingTaskTemplate, on_delete=models.PROTECT, related_name='task_instances')
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='assigned_onboarding_tasks')
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ('due_date', 'created_at')

    def __str__(self):
        return f'{self.onboarding.employee} - {self.title}'
