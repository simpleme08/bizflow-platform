from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import BaseModel


class JobOpening(BaseModel):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        OPEN = 'OPEN', 'Open'
        CLOSED = 'CLOSED', 'Closed'

    organization = models.ForeignKey('organization.Organization', on_delete=models.PROTECT, related_name='job_openings')
    title = models.CharField(max_length=150)
    department = models.ForeignKey('organization.Department', null=True, blank=True, on_delete=models.SET_NULL, related_name='job_openings')
    description = models.TextField(blank=True)
    location = models.CharField(max_length=120, blank=True)
    employment_type = models.ForeignKey('organization.EmploymentType', null=True, blank=True, on_delete=models.SET_NULL, related_name='job_openings')
    hiring_manager = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='managed_job_openings')
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    target_start_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ('-created_at',)


class Candidate(BaseModel):
    organization = models.ForeignKey('organization.Organization', on_delete=models.PROTECT, related_name='candidates')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=40, blank=True)
    source = models.CharField(max_length=80, blank=True)
    resume_url = models.URLField(blank=True)
    notes = models.TextField(blank=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=('organization', 'email'), name='unique_candidate_email_per_org')]
        ordering = ('last_name', 'first_name')

    def __str__(self):
        return f'{self.first_name} {self.last_name}'


class JobApplication(BaseModel):
    class Stage(models.TextChoices):
        APPLIED = 'APPLIED', 'Applied'
        SCREENING = 'SCREENING', 'Screening'
        INTERVIEW = 'INTERVIEW', 'Interview'
        OFFER = 'OFFER', 'Offer'
        HIRED = 'HIRED', 'Hired'
        REJECTED = 'REJECTED', 'Rejected'

    job = models.ForeignKey(JobOpening, on_delete=models.CASCADE, related_name='applications')
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='applications')
    stage = models.CharField(max_length=16, choices=Stage.choices, default=Stage.APPLIED)
    applied_at = models.DateTimeField(auto_now_add=True)
    rating = models.PositiveSmallIntegerField(null=True, blank=True)
    feedback = models.TextField(blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=('job', 'candidate'), name='unique_job_candidate_application')]

    def clean(self):
        super().clean()
        if self.job_id and self.candidate_id and self.job.organization_id != self.candidate.organization_id:
            raise ValidationError('The job and candidate must belong to the same organization.')


class PerformanceCycle(BaseModel):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        ACTIVE = 'ACTIVE', 'Active'
        CLOSED = 'CLOSED', 'Closed'

    organization = models.ForeignKey('organization.Organization', on_delete=models.PROTECT, related_name='performance_cycles')
    name = models.CharField(max_length=120)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)

    class Meta:
        ordering = ('-start_date',)


class EmployeeGoal(BaseModel):
    class Status(models.TextChoices):
        NOT_STARTED = 'NOT_STARTED', 'Not started'
        ON_TRACK = 'ON_TRACK', 'On track'
        AT_RISK = 'AT_RISK', 'At risk'
        COMPLETED = 'COMPLETED', 'Completed'

    employee = models.ForeignKey('employees.Employee', on_delete=models.CASCADE, related_name='goals')
    cycle = models.ForeignKey(PerformanceCycle, null=True, blank=True, on_delete=models.SET_NULL, related_name='goals')
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    due_date = models.DateField(null=True, blank=True)
    progress = models.PositiveSmallIntegerField(default=0)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.NOT_STARTED)

    def clean(self):
        super().clean()
        if self.cycle_id and self.employee_id and self.cycle.organization_id != self.employee.organization_id:
            raise ValidationError('The performance cycle and employee must belong to the same organization.')
        if self.progress > 100:
            raise ValidationError({'progress': 'Goal progress cannot exceed 100 percent.'})


class PerformanceReview(BaseModel):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        SUBMITTED = 'SUBMITTED', 'Submitted'
        ACKNOWLEDGED = 'ACKNOWLEDGED', 'Acknowledged'

    cycle = models.ForeignKey(PerformanceCycle, on_delete=models.CASCADE, related_name='reviews')
    employee = models.ForeignKey('employees.Employee', on_delete=models.CASCADE, related_name='performance_reviews')
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='submitted_reviews')
    rating = models.PositiveSmallIntegerField(null=True, blank=True)
    strengths = models.TextField(blank=True)
    development_areas = models.TextField(blank=True)
    comments = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)

    class Meta:
        constraints = [models.UniqueConstraint(fields=('cycle', 'employee'), name='unique_cycle_employee_review')]

    def clean(self):
        super().clean()
        if self.cycle_id and self.employee_id and self.cycle.organization_id != self.employee.organization_id:
            raise ValidationError('The performance cycle and employee must belong to the same organization.')
        if self.reviewer_id and self.employee_id:
            from apps.organization.models import OrganizationMembership
            if not OrganizationMembership.objects.filter(organization_id=self.employee.organization_id, user_id=self.reviewer_id, is_active=True).exists():
                raise ValidationError({'reviewer': 'The reviewer must have active membership in the employee organization.'})


class BenefitPlan(BaseModel):
    organization = models.ForeignKey('organization.Organization', on_delete=models.PROTECT, related_name='benefit_plans')
    name = models.CharField(max_length=140)
    provider = models.CharField(max_length=120, blank=True)
    description = models.TextField(blank=True)
    employee_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    employer_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)


class BenefitEnrollment(BaseModel):
    class Status(models.TextChoices):
        ENROLLED = 'ENROLLED', 'Enrolled'
        WAIVED = 'WAIVED', 'Waived'
        ENDED = 'ENDED', 'Ended'

    employee = models.ForeignKey('employees.Employee', on_delete=models.CASCADE, related_name='benefit_enrollments')
    plan = models.ForeignKey(BenefitPlan, on_delete=models.PROTECT, related_name='enrollments')
    effective_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ENROLLED)

    class Meta:
        constraints = [models.UniqueConstraint(fields=('employee', 'plan', 'effective_date'), name='unique_benefit_enrollment')]

    def clean(self):
        super().clean()
        if self.plan_id and self.employee_id and self.plan.organization_id != self.employee.organization_id:
            raise ValidationError('The benefit plan and employee must belong to the same organization.')
        if self.end_date and self.end_date < self.effective_date:
            raise ValidationError('Benefit enrollment end date cannot be before its effective date.')


class OffboardingRecord(BaseModel):
    class Status(models.TextChoices):
        PLANNED = 'PLANNED', 'Planned'
        IN_PROGRESS = 'IN_PROGRESS', 'In progress'
        COMPLETED = 'COMPLETED', 'Completed'

    employee = models.OneToOneField('employees.Employee', on_delete=models.CASCADE, related_name='offboarding_record')
    last_working_day = models.DateField()
    reason = models.CharField(max_length=160, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PLANNED)
    notes = models.TextField(blank=True)
    required_document_types = models.JSONField(default=list, blank=True)
    required_clearances = models.JSONField(default=list, blank=True)



class OffboardingClearanceEvidence(BaseModel):
    """Auditable, tenant-bound verification for one required offboarding clearance."""

    offboarding = models.ForeignKey(OffboardingRecord, on_delete=models.CASCADE, related_name='clearance_evidence')
    clearance_key = models.CharField(max_length=100)
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='verified_offboarding_clearances')
    verified_at = models.DateTimeField()
    notes = models.TextField()
    evidence_reference = models.CharField(max_length=255, blank=True, help_text='Private evidence identifier only; never store a public URL or secret.')
    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('offboarding', 'clearance_key'), name='unique_offboarding_clearance_evidence'),
        ]
        ordering = ('clearance_key',)

    def clean(self):
        super().clean()
        if self.offboarding_id and self.clearance_key not in (self.offboarding.required_clearances or []):
            raise ValidationError({'clearance_key': 'This clearance is not required for the offboarding record.'})
        if self.offboarding_id and self.verified_by_id:
            from apps.organization.models import OrganizationMembership
            if not OrganizationMembership.objects.filter(
                organization_id=self.offboarding.employee.organization_id,
                user_id=self.verified_by_id,
                is_active=True,
            ).exists():
                raise ValidationError({'verified_by': 'The verifier must have active membership in the employee organization.'})
        if not isinstance(self.notes, str) or not self.notes.strip():
            raise ValidationError({'notes': 'Verification notes are required.'})
        if self.evidence_reference and self.evidence_reference.strip().lower().startswith(('http://', 'https://')):
            raise ValidationError({'evidence_reference': 'Store a private evidence identifier, not a public URL.'})
