from django.conf import settings
from django.db import models

from apps.core.models import BaseModel


class ApprovalRequest(BaseModel):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'
        CANCELLED = 'CANCELLED', 'Cancelled'

    organization = models.ForeignKey('organization.Organization', on_delete=models.PROTECT, related_name='approval_requests')
    requester = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='requested_approvals')
    approver = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='pending_approvals')
    category = models.CharField(max_length=50)
    title = models.CharField(max_length=180)
    payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    decision_note = models.TextField(blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)


class EmployeeDocument(BaseModel):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        PUBLISHED = 'PUBLISHED', 'Published'
        ARCHIVED = 'ARCHIVED', 'Archived'

    organization = models.ForeignKey('organization.Organization', on_delete=models.PROTECT, related_name='employee_documents')
    title = models.CharField(max_length=180)
    category = models.CharField(max_length=80, default='Policy')
    body = models.TextField(blank=True)
    file_url = models.URLField(blank=True)
    requires_acknowledgement = models.BooleanField(default=False)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    expires_on = models.DateField(null=True, blank=True)


class DocumentAcknowledgement(BaseModel):
    document = models.ForeignKey(EmployeeDocument, on_delete=models.CASCADE, related_name='acknowledgements')
    employee = models.ForeignKey('employees.Employee', on_delete=models.CASCADE, related_name='document_acknowledgements')
    acknowledged_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=('document', 'employee'), name='unique_document_acknowledgement')]


class Announcement(BaseModel):
    organization = models.ForeignKey('organization.Organization', on_delete=models.PROTECT, related_name='announcements')
    title = models.CharField(max_length=180)
    message = models.TextField()
    published_at = models.DateTimeField(null=True, blank=True)
    expires_on = models.DateField(null=True, blank=True)
    is_published = models.BooleanField(default=False)


class ProfileChangeRequest(BaseModel):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'

    employee = models.ForeignKey('employees.Employee', on_delete=models.CASCADE, related_name='profile_change_requests')
    requested_changes = models.JSONField(default=dict)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    remarks = models.TextField(blank=True)


class CompensationChange(BaseModel):
    employee = models.ForeignKey('employees.Employee', on_delete=models.CASCADE, related_name='compensation_changes')
    effective_date = models.DateField()
    previous_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    proposed_salary = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.CharField(max_length=180)
    approval = models.OneToOneField(ApprovalRequest, null=True, blank=True, on_delete=models.SET_NULL, related_name='compensation_change')


class Project(BaseModel):
    organization = models.ForeignKey('organization.Organization', on_delete=models.PROTECT, related_name='projects')
    code = models.CharField(max_length=30)
    name = models.CharField(max_length=140)
    is_billable = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=('organization', 'code'), name='unique_project_code_per_org')]


class TimesheetEntry(BaseModel):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        SUBMITTED = 'SUBMITTED', 'Submitted'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'

    employee = models.ForeignKey('employees.Employee', on_delete=models.CASCADE, related_name='timesheet_entries')
    project = models.ForeignKey(Project, on_delete=models.PROTECT, related_name='timesheet_entries')
    work_date = models.DateField()
    hours = models.DecimalField(max_digits=5, decimal_places=2)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    approver = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)


class OffboardingTask(BaseModel):
    offboarding = models.ForeignKey('talent.OffboardingRecord', on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=160)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    due_date = models.DateField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)


class ExternalConnector(BaseModel):
    class Kind(models.TextChoices):
        PAYROLL = 'PAYROLL', 'Payroll/tax provider'
        BENEFITS = 'BENEFITS', 'Benefits carrier'
        ESIGN = 'ESIGN', 'E-signature provider'
        BACKGROUND = 'BACKGROUND', 'Background checks'
        IDENTITY = 'IDENTITY', 'Identity provider'
        MESSAGING = 'MESSAGING', 'Email/SMS provider'

    organization = models.ForeignKey('organization.Organization', on_delete=models.PROTECT, related_name='external_connectors')
    name = models.CharField(max_length=120)
    kind = models.CharField(max_length=20, choices=Kind.choices)
    endpoint = models.URLField(blank=True)
    configuration = models.JSONField(default=dict, blank=True, help_text='Store non-secret connector settings only.')
    is_enabled = models.BooleanField(default=False)
    last_sync_at = models.DateTimeField(null=True, blank=True)
